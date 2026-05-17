"""Deterministic fan-in AML rule."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pandas as pd

from graph_aml.alerts import (
    ALERT_SEVERITIES,
    AlertRecord,
    build_alert_id,
    create_alert_record,
    validate_alert_records,
)
from graph_aml.rules.common import (
    attach_customer_ids,
    build_count_window_reason_code,
    normalise_rule_transactions,
    require_columns,
)
from graph_aml.rules.exceptions import (
    RuleConfigurationError,
    RuleExecutionError,
    RuleInputError,
)

FAN_IN_DETECTION_COLUMNS = (
    "account_id",
    "detection_window_start",
    "detection_window_end",
    "unique_sender_count",
    "transaction_count",
    "total_amount",
    "min_amount",
    "max_amount",
    "sender_ids",
    "evidence_ids",
)


@dataclass(frozen=True)
class FanInRuleConfig:
    """Configuration for the deterministic fan-in rule."""

    rule_name: str = "Fan-in"
    typology: str = "fan_in"
    min_unique_senders: int = 15
    window_days: int = 7
    severity: str = "high"
    base_risk_score: float = 80.0
    high_sender_risk_score: float = 90.0
    high_sender_multiplier: float = 1.5
    min_total_amount: float = 0.0
    transaction_types: tuple[str, ...] = ("transfer", "wire")
    include_internal_account_receipts: bool = True

    def __post_init__(self) -> None:
        if not self.rule_name.strip():
            raise RuleConfigurationError("rule_name must be non-empty")
        if not self.typology.strip():
            raise RuleConfigurationError("typology must be non-empty")
        if self.min_unique_senders < 2:
            raise RuleConfigurationError("min_unique_senders must be at least 2")
        if self.window_days <= 0:
            raise RuleConfigurationError("window_days must be positive")
        if self.severity.lower() not in ALERT_SEVERITIES:
            raise RuleConfigurationError(f"severity must be one of {ALERT_SEVERITIES}")
        for field_name, score in (
            ("base_risk_score", self.base_risk_score),
            ("high_sender_risk_score", self.high_sender_risk_score),
        ):
            if score < 0 or score > 100:
                raise RuleConfigurationError(f"{field_name} must be between 0 and 100")
        if self.high_sender_multiplier < 1.0:
            raise RuleConfigurationError("high_sender_multiplier must be at least 1.0")
        if self.min_total_amount < 0:
            raise RuleConfigurationError("min_total_amount must be non-negative")
        if not isinstance(self.include_internal_account_receipts, bool):
            raise RuleConfigurationError("include_internal_account_receipts must be boolean")
        transaction_types = tuple(
            str(value).strip().lower() for value in self.transaction_types if str(value).strip()
        )
        if not transaction_types:
            raise RuleConfigurationError("at least one transaction type must be configured")
        object.__setattr__(self, "severity", self.severity.lower())
        object.__setattr__(self, "typology", self.typology.strip().lower())
        object.__setattr__(self, "transaction_types", transaction_types)


def filter_fan_in_candidate_transactions(
    transactions: pd.DataFrame,
    config: FanInRuleConfig | None = None,
) -> pd.DataFrame:
    """Filter inbound account receipts eligible for fan-in detection."""

    resolved_config = FanInRuleConfig() if config is None else config
    try:
        require_columns(transactions, ("receiver_account_id",), "transactions")
        frame = normalise_rule_transactions(transactions)
        if not resolved_config.include_internal_account_receipts:
            output = frame.iloc[0:0].copy()
            output["account_id"] = pd.Series(dtype="object")
            output["sender_id"] = pd.Series(dtype="object")
            return output
        mask = (
            frame["receiver_account_id"].notna()
            & frame["sender_account_id"].notna()
            & frame["sender_account_id"].ne(frame["receiver_account_id"])
            & frame["amount"].gt(0)
            & frame["transaction_type"].isin(resolved_config.transaction_types)
        )
        output = frame.loc[mask].copy()
        output["account_id"] = output["receiver_account_id"]
        output["sender_id"] = output["sender_account_id"]
        return output.sort_values(
            ["receiver_account_id", "transaction_timestamp", "sender_account_id", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to filter fan-in candidate transactions: {exc}") from exc


def detect_fan_in_windows(
    transactions: pd.DataFrame,
    config: FanInRuleConfig | None = None,
) -> pd.DataFrame:
    """Detect strongest fan-in window per receiving account."""

    resolved_config = FanInRuleConfig() if config is None else config
    try:
        candidates = filter_fan_in_candidate_transactions(transactions, resolved_config)
        if candidates.empty:
            return pd.DataFrame(columns=FAN_IN_DETECTION_COLUMNS)

        rows: list[dict[str, object]] = []
        for account_id, account_frame in candidates.groupby("account_id", sort=True):
            account_frame = account_frame.sort_values(
                ["transaction_timestamp", "sender_account_id", "transaction_id"],
                kind="mergesort",
            ).reset_index(drop=True)
            account_rows: list[dict[str, object]] = []
            for _, row in account_frame.iterrows():
                start = pd.Timestamp(row["transaction_timestamp"])
                end = start + pd.Timedelta(days=resolved_config.window_days)
                window = account_frame[
                    account_frame["transaction_timestamp"].ge(start)
                    & account_frame["transaction_timestamp"].le(end)
                ].copy()
                sender_ids = tuple(sorted(window["sender_id"].dropna().astype(str).unique()))
                unique_sender_count = len(sender_ids)
                total_amount = float(window["amount"].sum())
                if unique_sender_count < resolved_config.min_unique_senders:
                    continue
                if total_amount < resolved_config.min_total_amount:
                    continue
                account_rows.append(
                    {
                        "account_id": account_id,
                        "detection_window_start": start.isoformat(),
                        "detection_window_end": pd.Timestamp(
                            window["transaction_timestamp"].max()
                        ).isoformat(),
                        "unique_sender_count": unique_sender_count,
                        "transaction_count": int(len(window)),
                        "total_amount": total_amount,
                        "min_amount": float(window["amount"].min()),
                        "max_amount": float(window["amount"].max()),
                        "sender_ids": sender_ids,
                        "evidence_ids": tuple(window["transaction_id"].astype(str).tolist()),
                    }
                )
            if not account_rows:
                continue
            rows.append(sorted(account_rows, key=_fan_in_window_strength_key)[0])

        if not rows:
            return pd.DataFrame(columns=FAN_IN_DETECTION_COLUMNS)
        return (
            pd.DataFrame(rows, columns=FAN_IN_DETECTION_COLUMNS)
            .sort_values(
                ["account_id", "detection_window_start"],
                kind="mergesort",
            )
            .reset_index(drop=True)
        )
    except RuleExecutionError:
        raise
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to detect fan-in windows: {exc}") from exc


def build_fan_in_alerts(
    detections: pd.DataFrame,
    accounts: pd.DataFrame,
    config: FanInRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Convert fan-in detections into common AlertRecord objects."""

    resolved_config = FanInRuleConfig() if config is None else config
    try:
        if detections.empty:
            return ()
        require_columns(detections, FAN_IN_DETECTION_COLUMNS, "detections")
        with_customers = attach_customer_ids(detections, accounts)
        alerts: list[AlertRecord] = []
        high_sender_threshold = (
            resolved_config.min_unique_senders * resolved_config.high_sender_multiplier
        )
        for record in with_customers.sort_values(
            ["account_id", "detection_window_start"],
            kind="mergesort",
        ).to_dict(orient="records"):
            evidence_ids = tuple(str(value) for value in record["evidence_ids"])
            unique_sender_count = int(record["unique_sender_count"])
            risk_score = (
                resolved_config.high_sender_risk_score
                if unique_sender_count >= high_sender_threshold
                else resolved_config.base_risk_score
            )
            alert = create_alert_record(
                alert_id=build_alert_id(
                    resolved_config.rule_name,
                    str(record["account_id"]),
                    str(record["detection_window_start"]),
                    evidence_ids,
                ),
                account_id=str(record["account_id"]),
                customer_id=_optional_string(record.get("customer_id")),
                rule_name=resolved_config.rule_name,
                typology=resolved_config.typology,
                severity=resolved_config.severity,
                risk_score_rule=risk_score,
                reason_code=build_count_window_reason_code(
                    unique_sender_count,
                    "unique senders",
                    resolved_config.window_days,
                    "days",
                ),
                evidence_ids=evidence_ids,
                detection_window_start=str(record["detection_window_start"]),
                detection_window_end=str(record["detection_window_end"]),
                model_run_id=model_run_id,
            )
            alerts.append(alert)
        output = tuple(
            sorted(
                alerts,
                key=lambda alert: (
                    alert.account_id,
                    alert.detection_window_start or "",
                    alert.alert_id,
                ),
            )
        )
        validate_alert_records(output)
        return output
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to build fan-in alerts: {exc}") from exc


def run_fan_in_rule(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    config: FanInRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Run the deterministic fan-in rule without persistence."""

    resolved_config = FanInRuleConfig() if config is None else config
    try:
        require_columns(
            transactions,
            (
                "transaction_id",
                "sender_account_id",
                "receiver_account_id",
                "transaction_timestamp",
                "amount",
                "transaction_type",
            ),
            "transactions",
        )
        require_columns(accounts, ("account_id",), "accounts")
        detections = detect_fan_in_windows(transactions, resolved_config)
        return build_fan_in_alerts(
            detections,
            accounts,
            resolved_config,
            model_run_id=model_run_id,
        )
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to run fan-in rule: {exc}") from exc


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


def _fan_in_window_strength_key(item: dict[str, object]) -> tuple[int, int, float, str]:
    return (
        -int(cast(Any, item["unique_sender_count"])),
        -int(cast(Any, item["transaction_count"])),
        -float(cast(Any, item["total_amount"])),
        str(item["detection_window_start"]),
    )
