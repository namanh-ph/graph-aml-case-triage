"""Deterministic structuring AML rule."""

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
    build_rule_reason_code,
    normalise_rule_transactions,
    require_columns,
)
from graph_aml.rules.exceptions import (
    RuleConfigurationError,
    RuleExecutionError,
    RuleInputError,
)

DETECTION_COLUMNS = (
    "account_id",
    "detection_window_start",
    "detection_window_end",
    "transaction_count",
    "total_amount",
    "min_amount",
    "max_amount",
    "evidence_ids",
)


@dataclass(frozen=True)
class StructuringRuleConfig:
    """Configuration for the deterministic structuring rule."""

    rule_name: str = "Structuring"
    typology: str = "structuring"
    reporting_threshold: float = 10000.0
    below_threshold_margin: float = 0.90
    min_transaction_count: int = 8
    window_hours: int = 24
    severity: str = "high"
    base_risk_score: float = 80.0
    high_count_risk_score: float = 90.0
    high_count_multiplier: float = 1.5
    transaction_types: tuple[str, ...] = ("transfer", "wire")
    include_counterparty_payments: bool = True

    def __post_init__(self) -> None:
        if not self.rule_name.strip():
            raise RuleConfigurationError("rule_name must be non-empty")
        if not self.typology.strip():
            raise RuleConfigurationError("typology must be non-empty")
        if self.reporting_threshold <= 0:
            raise RuleConfigurationError("reporting_threshold must be positive")
        if self.below_threshold_margin <= 0 or self.below_threshold_margin >= 1:
            raise RuleConfigurationError(
                "below_threshold_margin must be greater than 0 and less than 1"
            )
        if self.min_transaction_count < 2:
            raise RuleConfigurationError("min_transaction_count must be at least 2")
        if self.window_hours <= 0:
            raise RuleConfigurationError("window_hours must be positive")
        if self.severity.lower() not in ALERT_SEVERITIES:
            raise RuleConfigurationError(f"severity must be one of {ALERT_SEVERITIES}")
        for field_name, score in (
            ("base_risk_score", self.base_risk_score),
            ("high_count_risk_score", self.high_count_risk_score),
        ):
            if score < 0 or score > 100:
                raise RuleConfigurationError(f"{field_name} must be between 0 and 100")
        if self.high_count_multiplier < 1.0:
            raise RuleConfigurationError("high_count_multiplier must be at least 1.0")
        transaction_types = tuple(
            str(value).strip().lower() for value in self.transaction_types if str(value).strip()
        )
        if not transaction_types:
            raise RuleConfigurationError("at least one transaction type must be configured")
        object.__setattr__(self, "severity", self.severity.lower())
        object.__setattr__(self, "typology", self.typology.strip().lower())
        object.__setattr__(self, "transaction_types", transaction_types)


def filter_structuring_candidate_transactions(
    transactions: pd.DataFrame,
    config: StructuringRuleConfig | None = None,
) -> pd.DataFrame:
    """Filter outbound below-threshold transactions eligible for structuring detection."""

    resolved_config = StructuringRuleConfig() if config is None else config
    try:
        frame = normalise_rule_transactions(transactions)
        lower_bound = resolved_config.reporting_threshold * resolved_config.below_threshold_margin
        mask = (
            frame["amount"].ge(lower_bound)
            & frame["amount"].lt(resolved_config.reporting_threshold)
            & frame["transaction_type"].isin(resolved_config.transaction_types)
        )
        if not resolved_config.include_counterparty_payments:
            if "receiver_account_id" not in frame.columns:
                mask &= False
            else:
                mask &= frame["receiver_account_id"].notna()
        output = frame.loc[mask].copy()
        output["account_id"] = output["sender_account_id"]
        return output.sort_values(
            ["sender_account_id", "transaction_timestamp", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to filter structuring candidate transactions: {exc}"
        ) from exc


def detect_structuring_windows(
    transactions: pd.DataFrame,
    config: StructuringRuleConfig | None = None,
) -> pd.DataFrame:
    """Detect strongest structuring window per account."""

    resolved_config = StructuringRuleConfig() if config is None else config
    try:
        candidates = filter_structuring_candidate_transactions(transactions, resolved_config)
        if candidates.empty:
            return pd.DataFrame(columns=DETECTION_COLUMNS)

        rows: list[dict[str, object]] = []
        for account_id, account_frame in candidates.groupby("account_id", sort=True):
            account_frame = account_frame.sort_values(
                ["transaction_timestamp", "transaction_id"],
                kind="mergesort",
            ).reset_index(drop=True)
            account_rows: list[dict[str, object]] = []
            for _, row in account_frame.iterrows():
                start = pd.Timestamp(row["transaction_timestamp"])
                end = start + pd.Timedelta(hours=resolved_config.window_hours)
                window = account_frame[
                    account_frame["transaction_timestamp"].ge(start)
                    & account_frame["transaction_timestamp"].le(end)
                ].copy()
                if len(window) < resolved_config.min_transaction_count:
                    continue
                account_rows.append(
                    {
                        "account_id": account_id,
                        "detection_window_start": start.isoformat(),
                        "detection_window_end": pd.Timestamp(
                            window["transaction_timestamp"].max()
                        ).isoformat(),
                        "transaction_count": int(len(window)),
                        "total_amount": float(window["amount"].sum()),
                        "min_amount": float(window["amount"].min()),
                        "max_amount": float(window["amount"].max()),
                        "evidence_ids": tuple(window["transaction_id"].astype(str).tolist()),
                    }
                )
            if not account_rows:
                continue
            strongest = sorted(
                account_rows,
                key=_window_strength_key,
            )[0]
            rows.append(strongest)

        if not rows:
            return pd.DataFrame(columns=DETECTION_COLUMNS)
        return (
            pd.DataFrame(rows, columns=DETECTION_COLUMNS)
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
        raise RuleExecutionError(f"Failed to detect structuring windows: {exc}") from exc


def build_structuring_alerts(
    detections: pd.DataFrame,
    accounts: pd.DataFrame,
    config: StructuringRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Convert structuring detections into common AlertRecord objects."""

    resolved_config = StructuringRuleConfig() if config is None else config
    try:
        if detections.empty:
            return ()
        require_columns(detections, DETECTION_COLUMNS, "detections")
        with_customers = attach_customer_ids(detections, accounts)
        alerts: list[AlertRecord] = []
        high_count_threshold = (
            resolved_config.min_transaction_count * resolved_config.high_count_multiplier
        )
        for record in with_customers.sort_values(
            ["account_id", "detection_window_start"],
            kind="mergesort",
        ).to_dict(orient="records"):
            evidence_ids = tuple(str(value) for value in record["evidence_ids"])
            transaction_count = int(record["transaction_count"])
            risk_score = (
                resolved_config.high_count_risk_score
                if transaction_count >= high_count_threshold
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
                reason_code=build_rule_reason_code(
                    transaction_count,
                    resolved_config.reporting_threshold,
                    resolved_config.window_hours,
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
        raise RuleExecutionError(f"Failed to build structuring alerts: {exc}") from exc


def run_structuring_rule(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    config: StructuringRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Run the deterministic structuring rule without persistence."""

    resolved_config = StructuringRuleConfig() if config is None else config
    try:
        require_columns(
            transactions,
            (
                "transaction_id",
                "sender_account_id",
                "transaction_timestamp",
                "amount",
                "transaction_type",
            ),
            "transactions",
        )
        require_columns(accounts, ("account_id",), "accounts")
        detections = detect_structuring_windows(transactions, resolved_config)
        return build_structuring_alerts(
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
        raise RuleExecutionError(f"Failed to run structuring rule: {exc}") from exc


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


def _window_strength_key(item: dict[str, object]) -> tuple[int, float, str]:
    return (
        -int(cast(Any, item["transaction_count"])),
        -float(cast(Any, item["total_amount"])),
        str(item["detection_window_start"]),
    )
