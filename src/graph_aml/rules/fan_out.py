"""Deterministic fan-out AML rule."""

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

FAN_OUT_DETECTION_COLUMNS = (
    "account_id",
    "detection_window_start",
    "detection_window_end",
    "unique_recipient_count",
    "transaction_count",
    "total_amount",
    "min_amount",
    "max_amount",
    "recipient_ids",
    "evidence_ids",
)


@dataclass(frozen=True)
class FanOutRuleConfig:
    """Configuration for the deterministic fan-out rule."""

    rule_name: str = "Fan-out"
    typology: str = "fan_out"
    min_unique_recipients: int = 20
    window_days: int = 7
    severity: str = "high"
    base_risk_score: float = 80.0
    high_recipient_risk_score: float = 90.0
    high_recipient_multiplier: float = 1.5
    min_total_amount: float = 0.0
    transaction_types: tuple[str, ...] = ("transfer", "wire")
    include_counterparties: bool = True
    include_internal_accounts: bool = True

    def __post_init__(self) -> None:
        if not self.rule_name.strip():
            raise RuleConfigurationError("rule_name must be non-empty")
        if not self.typology.strip():
            raise RuleConfigurationError("typology must be non-empty")
        if self.min_unique_recipients < 2:
            raise RuleConfigurationError("min_unique_recipients must be at least 2")
        if self.window_days <= 0:
            raise RuleConfigurationError("window_days must be positive")
        if self.severity.lower() not in ALERT_SEVERITIES:
            raise RuleConfigurationError(f"severity must be one of {ALERT_SEVERITIES}")
        for field_name, score in (
            ("base_risk_score", self.base_risk_score),
            ("high_recipient_risk_score", self.high_recipient_risk_score),
        ):
            if score < 0 or score > 100:
                raise RuleConfigurationError(f"{field_name} must be between 0 and 100")
        if self.high_recipient_multiplier < 1.0:
            raise RuleConfigurationError("high_recipient_multiplier must be at least 1.0")
        if self.min_total_amount < 0:
            raise RuleConfigurationError("min_total_amount must be non-negative")
        if not isinstance(self.include_counterparties, bool):
            raise RuleConfigurationError("include_counterparties must be boolean")
        if not isinstance(self.include_internal_accounts, bool):
            raise RuleConfigurationError("include_internal_accounts must be boolean")
        if not self.include_counterparties and not self.include_internal_accounts:
            raise RuleConfigurationError(
                "at least one recipient source must be enabled for fan-out"
            )
        transaction_types = tuple(
            str(value).strip().lower() for value in self.transaction_types if str(value).strip()
        )
        if not transaction_types:
            raise RuleConfigurationError("at least one transaction type must be configured")
        object.__setattr__(self, "severity", self.severity.lower())
        object.__setattr__(self, "typology", self.typology.strip().lower())
        object.__setattr__(self, "transaction_types", transaction_types)


def build_fan_out_recipient_key(row: pd.Series | dict[str, object]) -> str | None:
    """Return the canonical fan-out recipient key for one transaction row."""

    receiver_account_id = _normalise_recipient_value(row.get("receiver_account_id"))
    if receiver_account_id is not None:
        return receiver_account_id
    return _normalise_recipient_value(row.get("counterparty_id"))


def filter_fan_out_candidate_transactions(
    transactions: pd.DataFrame,
    config: FanOutRuleConfig | None = None,
) -> pd.DataFrame:
    """Filter outbound transactions eligible for fan-out detection."""

    resolved_config = FanOutRuleConfig() if config is None else config
    try:
        require_columns(transactions, ("receiver_account_id", "counterparty_id"), "transactions")
        frame = normalise_rule_transactions(transactions)
        frame["recipient_id"] = frame.apply(build_fan_out_recipient_key, axis=1)
        frame["recipient_type"] = frame.apply(_fan_out_recipient_type, axis=1)
        mask = (
            frame["sender_account_id"].notna()
            & frame["amount"].gt(0)
            & frame["transaction_type"].isin(resolved_config.transaction_types)
            & frame["recipient_id"].notna()
            & (
                frame["receiver_account_id"].isna()
                | frame["sender_account_id"].ne(frame["receiver_account_id"])
            )
        )
        if not resolved_config.include_internal_accounts:
            mask &= frame["recipient_type"].ne("account")
        if not resolved_config.include_counterparties:
            mask &= frame["recipient_type"].ne("counterparty")
        output = frame.loc[mask].copy()
        output["account_id"] = output["sender_account_id"]
        return output.sort_values(
            ["sender_account_id", "transaction_timestamp", "recipient_id", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to filter fan-out candidate transactions: {exc}") from exc


def detect_fan_out_windows(
    transactions: pd.DataFrame,
    config: FanOutRuleConfig | None = None,
) -> pd.DataFrame:
    """Detect strongest fan-out window per sending account."""

    resolved_config = FanOutRuleConfig() if config is None else config
    try:
        candidates = filter_fan_out_candidate_transactions(transactions, resolved_config)
        if candidates.empty:
            return pd.DataFrame(columns=FAN_OUT_DETECTION_COLUMNS)

        rows: list[dict[str, object]] = []
        for account_id, account_frame in candidates.groupby("account_id", sort=True):
            account_frame = account_frame.sort_values(
                ["transaction_timestamp", "recipient_id", "transaction_id"],
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
                recipient_ids = tuple(sorted(window["recipient_id"].dropna().astype(str).unique()))
                unique_recipient_count = len(recipient_ids)
                total_amount = float(window["amount"].sum())
                if unique_recipient_count < resolved_config.min_unique_recipients:
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
                        "unique_recipient_count": unique_recipient_count,
                        "transaction_count": int(len(window)),
                        "total_amount": total_amount,
                        "min_amount": float(window["amount"].min()),
                        "max_amount": float(window["amount"].max()),
                        "recipient_ids": recipient_ids,
                        "evidence_ids": tuple(window["transaction_id"].astype(str).tolist()),
                    }
                )
            if not account_rows:
                continue
            rows.append(sorted(account_rows, key=_fan_out_window_strength_key)[0])

        if not rows:
            return pd.DataFrame(columns=FAN_OUT_DETECTION_COLUMNS)
        return (
            pd.DataFrame(rows, columns=FAN_OUT_DETECTION_COLUMNS)
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
        raise RuleExecutionError(f"Failed to detect fan-out windows: {exc}") from exc


def build_fan_out_alerts(
    detections: pd.DataFrame,
    accounts: pd.DataFrame,
    config: FanOutRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Convert fan-out detections into common AlertRecord objects."""

    resolved_config = FanOutRuleConfig() if config is None else config
    try:
        if detections.empty:
            return ()
        require_columns(detections, FAN_OUT_DETECTION_COLUMNS, "detections")
        with_customers = attach_customer_ids(detections, accounts)
        alerts: list[AlertRecord] = []
        high_recipient_threshold = (
            resolved_config.min_unique_recipients * resolved_config.high_recipient_multiplier
        )
        for record in with_customers.sort_values(
            ["account_id", "detection_window_start"],
            kind="mergesort",
        ).to_dict(orient="records"):
            evidence_ids = tuple(str(value) for value in record["evidence_ids"])
            unique_recipient_count = int(record["unique_recipient_count"])
            risk_score = (
                resolved_config.high_recipient_risk_score
                if unique_recipient_count >= high_recipient_threshold
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
                    unique_recipient_count,
                    "unique recipients",
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
        raise RuleExecutionError(f"Failed to build fan-out alerts: {exc}") from exc


def run_fan_out_rule(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    config: FanOutRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Run the deterministic fan-out rule without persistence."""

    resolved_config = FanOutRuleConfig() if config is None else config
    try:
        require_columns(
            transactions,
            (
                "transaction_id",
                "sender_account_id",
                "receiver_account_id",
                "counterparty_id",
                "transaction_timestamp",
                "amount",
                "transaction_type",
            ),
            "transactions",
        )
        require_columns(accounts, ("account_id",), "accounts")
        detections = detect_fan_out_windows(transactions, resolved_config)
        return build_fan_out_alerts(
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
        raise RuleExecutionError(f"Failed to run fan-out rule: {exc}") from exc


def _normalise_recipient_value(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _fan_out_recipient_type(row: pd.Series | dict[str, object]) -> str | None:
    if _normalise_recipient_value(row.get("receiver_account_id")) is not None:
        return "account"
    if _normalise_recipient_value(row.get("counterparty_id")) is not None:
        return "counterparty"
    return None


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


def _fan_out_window_strength_key(item: dict[str, object]) -> tuple[int, int, float, str]:
    return (
        -int(cast(Any, item["unique_recipient_count"])),
        -int(cast(Any, item["transaction_count"])),
        -float(cast(Any, item["total_amount"])),
        str(item["detection_window_start"]),
    )
