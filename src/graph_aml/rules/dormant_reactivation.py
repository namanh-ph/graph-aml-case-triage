"""Deterministic dormant reactivation AML rule."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
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
    normalise_rule_transactions,
    require_columns,
)
from graph_aml.rules.exceptions import (
    RuleConfigurationError,
    RuleExecutionError,
    RuleInputError,
)

DORMANT_REACTIVATION_DETECTION_COLUMNS = (
    "account_id",
    "detection_window_start",
    "detection_window_end",
    "dormant_days_before_activity",
    "reactivation_transaction_count",
    "total_outbound_amount",
    "max_outbound_amount",
    "recipient_count",
    "previous_activity_timestamp",
    "reactivation_evidence_ids",
    "evidence_ids",
)

ACCOUNT_ACTIVITY_COLUMNS = (
    "account_id",
    "transaction_id",
    "transaction_timestamp",
    "activity_direction",
    "amount",
)


@dataclass(frozen=True)
class DormantReactivationRuleConfig:
    """Configuration for the deterministic dormant reactivation rule."""

    rule_name: str = "Dormant reactivation"
    typology: str = "dormant_reactivation"
    dormant_days_threshold: int = 120
    reactivation_window_days: int = 7
    min_outbound_amount: float = 10000.0
    min_total_outbound_amount: float = 10000.0
    min_outbound_transaction_count: int = 1
    severity: str = "high"
    base_risk_score: float = 80.0
    high_value_risk_score: float = 90.0
    high_value_multiplier: float = 2.0
    outbound_transaction_types: tuple[str, ...] = ("transfer", "wire", "cash_withdrawal")
    include_counterparty_outflows: bool = True
    include_internal_account_outflows: bool = True

    def __post_init__(self) -> None:
        try:
            dormant_days_threshold = int(self.dormant_days_threshold)
            reactivation_window_days = int(self.reactivation_window_days)
            min_outbound_amount = float(self.min_outbound_amount)
            min_total_outbound_amount = float(self.min_total_outbound_amount)
            min_outbound_transaction_count = int(self.min_outbound_transaction_count)
            base_risk_score = float(self.base_risk_score)
            high_value_risk_score = float(self.high_value_risk_score)
            high_value_multiplier = float(self.high_value_multiplier)
        except (TypeError, ValueError) as exc:
            raise RuleConfigurationError(
                "dormant reactivation numeric configuration values must be valid"
            ) from exc
        if not self.rule_name.strip():
            raise RuleConfigurationError("rule_name must be non-empty")
        if not self.typology.strip():
            raise RuleConfigurationError("typology must be non-empty")
        if dormant_days_threshold <= 0:
            raise RuleConfigurationError("dormant_days_threshold must be positive")
        if reactivation_window_days <= 0:
            raise RuleConfigurationError("reactivation_window_days must be positive")
        if not isfinite(min_outbound_amount) or min_outbound_amount < 0:
            raise RuleConfigurationError("min_outbound_amount must be non-negative")
        if not isfinite(min_total_outbound_amount) or min_total_outbound_amount < 0:
            raise RuleConfigurationError("min_total_outbound_amount must be non-negative")
        if min_outbound_transaction_count < 1:
            raise RuleConfigurationError("min_outbound_transaction_count must be at least 1")
        if self.severity.lower() not in ALERT_SEVERITIES:
            raise RuleConfigurationError(f"severity must be one of {ALERT_SEVERITIES}")
        for field_name, score in (
            ("base_risk_score", base_risk_score),
            ("high_value_risk_score", high_value_risk_score),
        ):
            if not isfinite(score) or score < 0 or score > 100:
                raise RuleConfigurationError(f"{field_name} must be between 0 and 100")
        if not isfinite(high_value_multiplier) or high_value_multiplier < 1.0:
            raise RuleConfigurationError("high_value_multiplier must be at least 1.0")
        if not isinstance(self.include_counterparty_outflows, bool):
            raise RuleConfigurationError("include_counterparty_outflows must be boolean")
        if not isinstance(self.include_internal_account_outflows, bool):
            raise RuleConfigurationError("include_internal_account_outflows must be boolean")
        if not self.include_counterparty_outflows and not self.include_internal_account_outflows:
            raise RuleConfigurationError(
                "at least one dormant reactivation outflow recipient source must be enabled"
            )
        outbound_transaction_types = tuple(
            str(value).strip().lower()
            for value in self.outbound_transaction_types
            if str(value).strip()
        )
        if not outbound_transaction_types:
            raise RuleConfigurationError("at least one outbound transaction type is required")
        object.__setattr__(self, "severity", self.severity.lower())
        object.__setattr__(self, "typology", self.typology.strip().lower())
        object.__setattr__(self, "dormant_days_threshold", dormant_days_threshold)
        object.__setattr__(self, "reactivation_window_days", reactivation_window_days)
        object.__setattr__(self, "min_outbound_amount", min_outbound_amount)
        object.__setattr__(
            self,
            "min_total_outbound_amount",
            min_total_outbound_amount,
        )
        object.__setattr__(
            self,
            "min_outbound_transaction_count",
            min_outbound_transaction_count,
        )
        object.__setattr__(self, "base_risk_score", base_risk_score)
        object.__setattr__(self, "high_value_risk_score", high_value_risk_score)
        object.__setattr__(self, "high_value_multiplier", high_value_multiplier)
        object.__setattr__(self, "outbound_transaction_types", outbound_transaction_types)


def build_dormant_reactivation_reason_code(
    dormant_days: int,
    total_outbound_amount: float,
    reactivation_window_days: int,
    template: str | None = None,
) -> str:
    """Build deterministic dormant reactivation reason text."""

    try:
        dormant_days_value = int(dormant_days)
        reactivation_window_days_value = int(reactivation_window_days)
    except (TypeError, ValueError) as exc:
        raise RuleInputError("dormant_days and reactivation_window_days must be integers") from exc
    try:
        amount = float(total_outbound_amount)
    except (TypeError, ValueError) as exc:
        raise RuleInputError("total_outbound_amount must be numeric") from exc
    if dormant_days_value <= 0:
        raise RuleInputError("dormant_days must be positive")
    if not isfinite(amount) or amount < 0:
        raise RuleInputError("total_outbound_amount must be non-negative")
    if reactivation_window_days_value <= 0:
        raise RuleInputError("reactivation_window_days must be positive")
    if template is not None:
        return template.format(
            dormant_days=dormant_days_value,
            total_outbound_amount=amount,
            total_outbound_amount_formatted=f"{amount:.2f}",
            reactivation_window_days=reactivation_window_days_value,
        )
    return (
        f"{dormant_days_value} inactive days followed by {amount:.2f} outbound value "
        f"within {reactivation_window_days_value} days"
    )


def build_dormant_reactivation_recipient_key(
    row: pd.Series | dict[str, object],
) -> str | None:
    """Return the canonical recipient key for a dormant reactivation outflow."""

    receiver_account_id = _normalise_identifier_value(row.get("receiver_account_id"))
    if receiver_account_id is not None:
        return receiver_account_id
    return _normalise_identifier_value(row.get("counterparty_id"))


def prepare_dormant_reactivation_transactions(
    transactions: pd.DataFrame,
    config: DormantReactivationRuleConfig | None = None,
) -> pd.DataFrame:
    """Prepare transactions for dormant reactivation activity analysis."""

    DormantReactivationRuleConfig() if config is None else config
    try:
        require_columns(transactions, ("receiver_account_id", "counterparty_id"), "transactions")
        frame = normalise_rule_transactions(transactions)
        frame["recipient_id"] = frame.apply(build_dormant_reactivation_recipient_key, axis=1)
        frame["sender_activity_account_id"] = frame["sender_account_id"]
        frame["receiver_activity_account_id"] = frame["receiver_account_id"]
        return frame.sort_values(
            ["transaction_timestamp", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to prepare dormant reactivation transactions: {exc}"
        ) from exc


def filter_dormant_reactivation_outbound_candidates(
    transactions: pd.DataFrame,
    config: DormantReactivationRuleConfig | None = None,
) -> pd.DataFrame:
    """Filter high-value outbound candidates eligible for reactivation detection."""

    resolved_config = DormantReactivationRuleConfig() if config is None else config
    try:
        frame = prepare_dormant_reactivation_transactions(transactions, resolved_config)
        recipient_type = frame.apply(_dormant_reactivation_recipient_type, axis=1)
        mask = (
            frame["sender_account_id"].notna()
            & frame["amount"].ge(resolved_config.min_outbound_amount)
            & frame["transaction_type"].isin(resolved_config.outbound_transaction_types)
            & frame["recipient_id"].notna()
            & (
                frame["receiver_account_id"].isna()
                | frame["sender_account_id"].ne(frame["receiver_account_id"])
            )
        )
        if not resolved_config.include_internal_account_outflows:
            mask &= recipient_type.ne("account")
        if not resolved_config.include_counterparty_outflows:
            mask &= recipient_type.ne("counterparty")
        output = frame.loc[mask].copy()
        output["account_id"] = output["sender_account_id"]
        return output.sort_values(
            ["account_id", "transaction_timestamp", "recipient_id", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to filter dormant reactivation outbound candidates: {exc}"
        ) from exc


def build_account_activity_history(transactions: pd.DataFrame) -> pd.DataFrame:
    """Build account-level inbound and outbound activity history."""

    try:
        frame = prepare_dormant_reactivation_transactions(transactions)
        outbound = frame.loc[
            frame["sender_account_id"].notna(),
            ["sender_account_id", "transaction_id", "transaction_timestamp", "amount"],
        ].copy()
        outbound = outbound.rename(columns={"sender_account_id": "account_id"})
        outbound["activity_direction"] = "outbound"

        inbound = frame.loc[
            frame["receiver_account_id"].notna(),
            ["receiver_account_id", "transaction_id", "transaction_timestamp", "amount"],
        ].copy()
        inbound = inbound.rename(columns={"receiver_account_id": "account_id"})
        inbound["activity_direction"] = "inbound"

        output = pd.concat([outbound, inbound], ignore_index=True)
        if output.empty:
            return pd.DataFrame(columns=ACCOUNT_ACTIVITY_COLUMNS)
        output = output.loc[
            output["account_id"].notna() & output["transaction_timestamp"].notna()
        ].copy()
        return (
            output.loc[:, ACCOUNT_ACTIVITY_COLUMNS]
            .sort_values(
                ["account_id", "transaction_timestamp", "transaction_id"],
                kind="mergesort",
            )
            .reset_index(drop=True)
        )
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to build account activity history: {exc}") from exc


def detect_dormant_reactivation_windows(
    transactions: pd.DataFrame,
    config: DormantReactivationRuleConfig | None = None,
) -> pd.DataFrame:
    """Detect strongest dormant reactivation window per account."""

    resolved_config = DormantReactivationRuleConfig() if config is None else config
    try:
        activity = build_account_activity_history(transactions)
        candidates = filter_dormant_reactivation_outbound_candidates(
            transactions,
            resolved_config,
        )
        if activity.empty or candidates.empty:
            return pd.DataFrame(columns=DORMANT_REACTIVATION_DETECTION_COLUMNS)

        rows: list[dict[str, object]] = []
        for account_id, account_candidates in candidates.groupby("account_id", sort=True):
            account_activity = activity.loc[activity["account_id"].eq(account_id)].copy()
            if account_activity.empty:
                continue
            account_candidates = account_candidates.sort_values(
                ["transaction_timestamp", "recipient_id", "transaction_id"],
                kind="mergesort",
            ).reset_index(drop=True)
            account_rows: list[dict[str, object]] = []
            for _, candidate in account_candidates.iterrows():
                start = pd.Timestamp(candidate["transaction_timestamp"])
                prior_activity = account_activity.loc[
                    account_activity["transaction_timestamp"].lt(start)
                ].sort_values(
                    ["transaction_timestamp", "transaction_id"],
                    kind="mergesort",
                )
                if prior_activity.empty:
                    continue
                prior = prior_activity.iloc[-1]
                prior_timestamp = pd.Timestamp(prior["transaction_timestamp"])
                dormant_days = int((start.date() - prior_timestamp.date()).days)
                if dormant_days < resolved_config.dormant_days_threshold:
                    continue
                end = start + pd.Timedelta(days=resolved_config.reactivation_window_days)
                window = account_candidates.loc[
                    account_candidates["transaction_timestamp"].ge(start)
                    & account_candidates["transaction_timestamp"].le(end)
                ].copy()
                if window.empty:
                    continue
                transaction_count = int(len(window))
                total_outbound = float(window["amount"].sum())
                if transaction_count < resolved_config.min_outbound_transaction_count:
                    continue
                if total_outbound < resolved_config.min_total_outbound_amount:
                    continue
                reactivation_ids = tuple(window["transaction_id"].astype(str).tolist())
                previous_activity_id = str(prior["transaction_id"])
                account_rows.append(
                    {
                        "account_id": account_id,
                        "detection_window_start": start.isoformat(),
                        "detection_window_end": end.isoformat(),
                        "dormant_days_before_activity": dormant_days,
                        "reactivation_transaction_count": transaction_count,
                        "total_outbound_amount": total_outbound,
                        "max_outbound_amount": float(window["amount"].max()),
                        "recipient_count": int(window["recipient_id"].dropna().nunique()),
                        "previous_activity_timestamp": prior_timestamp.isoformat(),
                        "reactivation_evidence_ids": reactivation_ids,
                        "evidence_ids": (previous_activity_id, *reactivation_ids),
                    }
                )
            if not account_rows:
                continue
            rows.append(sorted(account_rows, key=_dormant_reactivation_window_strength_key)[0])

        if not rows:
            return pd.DataFrame(columns=DORMANT_REACTIVATION_DETECTION_COLUMNS)
        return (
            pd.DataFrame(rows, columns=DORMANT_REACTIVATION_DETECTION_COLUMNS)
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
        raise RuleExecutionError(f"Failed to detect dormant reactivation windows: {exc}") from exc


def build_dormant_reactivation_alerts(
    detections: pd.DataFrame,
    accounts: pd.DataFrame,
    config: DormantReactivationRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Convert dormant reactivation detections into common AlertRecord objects."""

    resolved_config = DormantReactivationRuleConfig() if config is None else config
    try:
        if detections.empty:
            return ()
        require_columns(detections, DORMANT_REACTIVATION_DETECTION_COLUMNS, "detections")
        with_customers = attach_customer_ids(detections, accounts)
        alerts: list[AlertRecord] = []
        high_value_threshold = (
            resolved_config.min_total_outbound_amount * resolved_config.high_value_multiplier
        )
        for record in with_customers.sort_values(
            ["account_id", "detection_window_start"],
            kind="mergesort",
        ).to_dict(orient="records"):
            evidence_ids = tuple(str(value) for value in record["evidence_ids"])
            total_outbound = float(record["total_outbound_amount"])
            risk_score = (
                resolved_config.high_value_risk_score
                if total_outbound >= high_value_threshold
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
                reason_code=build_dormant_reactivation_reason_code(
                    int(record["dormant_days_before_activity"]),
                    total_outbound,
                    resolved_config.reactivation_window_days,
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
        raise RuleExecutionError(f"Failed to build dormant reactivation alerts: {exc}") from exc


def run_dormant_reactivation_rule(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    config: DormantReactivationRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Run the deterministic dormant reactivation rule without persistence."""

    resolved_config = DormantReactivationRuleConfig() if config is None else config
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
        detections = detect_dormant_reactivation_windows(transactions, resolved_config)
        return build_dormant_reactivation_alerts(
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
        raise RuleExecutionError(f"Failed to run dormant reactivation rule: {exc}") from exc


def _normalise_identifier_value(value: object) -> str | None:
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


def _dormant_reactivation_recipient_type(row: pd.Series | dict[str, object]) -> str | None:
    if _normalise_identifier_value(row.get("receiver_account_id")) is not None:
        return "account"
    if _normalise_identifier_value(row.get("counterparty_id")) is not None:
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


def _dormant_reactivation_window_strength_key(
    item: dict[str, object],
) -> tuple[int, float, int, str]:
    return (
        -int(cast(Any, item["dormant_days_before_activity"])),
        -float(cast(Any, item["total_outbound_amount"])),
        -int(cast(Any, item["reactivation_transaction_count"])),
        str(item["detection_window_start"]),
    )
