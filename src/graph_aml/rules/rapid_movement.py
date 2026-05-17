"""Deterministic rapid movement AML rule."""

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

RAPID_MOVEMENT_DETECTION_COLUMNS = (
    "account_id",
    "detection_window_start",
    "detection_window_end",
    "inbound_transaction_count",
    "outbound_transaction_count",
    "total_received",
    "total_sent_out",
    "outflow_ratio",
    "retained_amount",
    "retained_ratio",
    "inbound_evidence_ids",
    "outbound_evidence_ids",
    "evidence_ids",
)


@dataclass(frozen=True)
class RapidMovementRuleConfig:
    """Configuration for the deterministic rapid movement rule."""

    rule_name: str = "Rapid movement"
    typology: str = "rapid_movement"
    outflow_window_hours: int = 48
    min_total_received: float = 1000.0
    min_outflow_ratio: float = 0.90
    max_retained_ratio: float = 0.10
    min_outgoing_transaction_count: int = 1
    severity: str = "high"
    base_risk_score: float = 80.0
    high_ratio_risk_score: float = 90.0
    high_ratio_threshold: float = 0.98
    inbound_transaction_types: tuple[str, ...] = ("transfer", "wire", "cash_deposit")
    outbound_transaction_types: tuple[str, ...] = ("transfer", "wire", "cash_withdrawal")
    include_counterparty_outflows: bool = True
    include_internal_account_outflows: bool = True

    def __post_init__(self) -> None:
        if not self.rule_name.strip():
            raise RuleConfigurationError("rule_name must be non-empty")
        if not self.typology.strip():
            raise RuleConfigurationError("typology must be non-empty")
        if self.outflow_window_hours <= 0:
            raise RuleConfigurationError("outflow_window_hours must be positive")
        if self.min_total_received < 0:
            raise RuleConfigurationError("min_total_received must be non-negative")
        if self.min_outflow_ratio <= 0 or self.min_outflow_ratio > 1:
            raise RuleConfigurationError("min_outflow_ratio must be greater than 0 and at most 1")
        if self.max_retained_ratio < 0 or self.max_retained_ratio >= 1:
            raise RuleConfigurationError("max_retained_ratio must be at least 0 and less than 1")
        if self.min_outgoing_transaction_count < 1:
            raise RuleConfigurationError("min_outgoing_transaction_count must be at least 1")
        if self.severity.lower() not in ALERT_SEVERITIES:
            raise RuleConfigurationError(f"severity must be one of {ALERT_SEVERITIES}")
        for field_name, score in (
            ("base_risk_score", self.base_risk_score),
            ("high_ratio_risk_score", self.high_ratio_risk_score),
        ):
            if score < 0 or score > 100:
                raise RuleConfigurationError(f"{field_name} must be between 0 and 100")
        if self.high_ratio_threshold < self.min_outflow_ratio or self.high_ratio_threshold > 1:
            raise RuleConfigurationError(
                "high_ratio_threshold must be at least min_outflow_ratio and at most 1"
            )
        if not isinstance(self.include_counterparty_outflows, bool):
            raise RuleConfigurationError("include_counterparty_outflows must be boolean")
        if not isinstance(self.include_internal_account_outflows, bool):
            raise RuleConfigurationError("include_internal_account_outflows must be boolean")
        if not self.include_counterparty_outflows and not self.include_internal_account_outflows:
            raise RuleConfigurationError(
                "at least one rapid movement outflow recipient source must be enabled"
            )
        inbound_transaction_types = _normalise_transaction_types(
            self.inbound_transaction_types,
            "inbound_transaction_types",
        )
        outbound_transaction_types = _normalise_transaction_types(
            self.outbound_transaction_types,
            "outbound_transaction_types",
        )
        object.__setattr__(self, "severity", self.severity.lower())
        object.__setattr__(self, "typology", self.typology.strip().lower())
        object.__setattr__(self, "inbound_transaction_types", inbound_transaction_types)
        object.__setattr__(self, "outbound_transaction_types", outbound_transaction_types)


def build_rapid_movement_reason_code(
    outflow_ratio: float,
    window_hours: int,
    template: str | None = None,
) -> str:
    """Build deterministic rapid movement reason text."""

    try:
        ratio = float(outflow_ratio)
    except (TypeError, ValueError) as exc:
        raise RuleInputError("outflow_ratio must be numeric") from exc
    if not isfinite(ratio) or ratio <= 0:
        raise RuleInputError("outflow_ratio must be positive")
    if window_hours <= 0:
        raise RuleInputError("window_hours must be positive")
    outflow_percentage = int(round(ratio * 100))
    if template is not None:
        return template.format(
            outflow_ratio=ratio,
            outflow_percentage=outflow_percentage,
            outflow_ratio_pct=outflow_percentage,
            outgoing_ratio_pct=outflow_percentage,
            window_hours=window_hours,
        )
    return f"{outflow_percentage} percent of received value sent out within {window_hours} hours"


def build_rapid_movement_outflow_recipient_key(
    row: pd.Series | dict[str, object],
) -> str | None:
    """Return the canonical recipient key for a rapid movement outflow."""

    receiver_account_id = _normalise_identifier_value(row.get("receiver_account_id"))
    if receiver_account_id is not None:
        return receiver_account_id
    return _normalise_identifier_value(row.get("counterparty_id"))


def prepare_rapid_movement_transactions(
    transactions: pd.DataFrame,
    config: RapidMovementRuleConfig | None = None,
) -> pd.DataFrame:
    """Prepare transactions for rapid movement inbound and outbound filtering."""

    RapidMovementRuleConfig() if config is None else config
    try:
        require_columns(transactions, ("receiver_account_id", "counterparty_id"), "transactions")
        frame = normalise_rule_transactions(transactions)
        frame["inbound_account_id"] = frame["receiver_account_id"]
        frame["outbound_account_id"] = frame["sender_account_id"]
        frame["outflow_recipient_id"] = frame.apply(
            build_rapid_movement_outflow_recipient_key,
            axis=1,
        )
        return frame.sort_values(
            ["transaction_timestamp", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to prepare rapid movement transactions: {exc}") from exc


def filter_rapid_movement_inbound_transactions(
    transactions: pd.DataFrame,
    config: RapidMovementRuleConfig | None = None,
) -> pd.DataFrame:
    """Filter transactions that represent value entering an account."""

    resolved_config = RapidMovementRuleConfig() if config is None else config
    try:
        frame = prepare_rapid_movement_transactions(transactions, resolved_config)
        mask = (
            frame["receiver_account_id"].notna()
            & frame["amount"].gt(0)
            & frame["transaction_type"].isin(resolved_config.inbound_transaction_types)
        )
        output = frame.loc[mask].copy()
        output["account_id"] = output["receiver_account_id"]
        return output.sort_values(
            ["account_id", "transaction_timestamp", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to filter rapid movement inbound transactions: {exc}"
        ) from exc


def filter_rapid_movement_outbound_transactions(
    transactions: pd.DataFrame,
    config: RapidMovementRuleConfig | None = None,
) -> pd.DataFrame:
    """Filter transactions that represent value quickly leaving an account."""

    resolved_config = RapidMovementRuleConfig() if config is None else config
    try:
        frame = prepare_rapid_movement_transactions(transactions, resolved_config)
        recipient_type = frame.apply(_rapid_movement_outflow_recipient_type, axis=1)
        mask = (
            frame["sender_account_id"].notna()
            & frame["amount"].gt(0)
            & frame["transaction_type"].isin(resolved_config.outbound_transaction_types)
            & frame["outflow_recipient_id"].notna()
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
            ["account_id", "transaction_timestamp", "outflow_recipient_id", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to filter rapid movement outbound transactions: {exc}"
        ) from exc


def detect_rapid_movement_windows(
    transactions: pd.DataFrame,
    config: RapidMovementRuleConfig | None = None,
) -> pd.DataFrame:
    """Detect strongest rapid movement window per pass-through account."""

    resolved_config = RapidMovementRuleConfig() if config is None else config
    try:
        inbound = filter_rapid_movement_inbound_transactions(transactions, resolved_config)
        outbound = filter_rapid_movement_outbound_transactions(transactions, resolved_config)
        if inbound.empty or outbound.empty:
            return pd.DataFrame(columns=RAPID_MOVEMENT_DETECTION_COLUMNS)

        rows: list[dict[str, object]] = []
        for account_id, inbound_frame in inbound.groupby("account_id", sort=True):
            outbound_frame = outbound.loc[outbound["account_id"].eq(account_id)].copy()
            if outbound_frame.empty:
                continue
            inbound_frame = inbound_frame.sort_values(
                ["transaction_timestamp", "transaction_id"],
                kind="mergesort",
            ).reset_index(drop=True)
            outbound_frame = outbound_frame.sort_values(
                ["transaction_timestamp", "outflow_recipient_id", "transaction_id"],
                kind="mergesort",
            ).reset_index(drop=True)
            account_rows: list[dict[str, object]] = []
            for _, row in inbound_frame.iterrows():
                start = pd.Timestamp(row["transaction_timestamp"])
                end = start + pd.Timedelta(hours=resolved_config.outflow_window_hours)
                inbound_window = inbound_frame[
                    inbound_frame["transaction_timestamp"].ge(start)
                    & inbound_frame["transaction_timestamp"].le(end)
                ].copy()
                outbound_window = outbound_frame[
                    outbound_frame["transaction_timestamp"].ge(start)
                    & outbound_frame["transaction_timestamp"].le(end)
                ].copy()
                if inbound_window.empty or outbound_window.empty:
                    continue
                total_received = float(inbound_window["amount"].sum())
                total_sent_out = float(outbound_window["amount"].sum())
                if total_received <= 0:
                    continue
                outflow_ratio = total_sent_out / total_received
                retained_amount = total_received - total_sent_out
                retained_ratio = max(retained_amount, 0.0) / total_received
                outbound_count = int(len(outbound_window))
                if total_received < resolved_config.min_total_received:
                    continue
                if outbound_count < resolved_config.min_outgoing_transaction_count:
                    continue
                if outflow_ratio < resolved_config.min_outflow_ratio:
                    continue
                if retained_ratio > resolved_config.max_retained_ratio:
                    continue
                inbound_ids = tuple(inbound_window["transaction_id"].astype(str).tolist())
                outbound_ids = tuple(outbound_window["transaction_id"].astype(str).tolist())
                account_rows.append(
                    {
                        "account_id": account_id,
                        "detection_window_start": start.isoformat(),
                        "detection_window_end": end.isoformat(),
                        "inbound_transaction_count": int(len(inbound_window)),
                        "outbound_transaction_count": outbound_count,
                        "total_received": total_received,
                        "total_sent_out": total_sent_out,
                        "outflow_ratio": float(outflow_ratio),
                        "retained_amount": float(retained_amount),
                        "retained_ratio": float(retained_ratio),
                        "inbound_evidence_ids": inbound_ids,
                        "outbound_evidence_ids": outbound_ids,
                        "evidence_ids": inbound_ids + outbound_ids,
                    }
                )
            if not account_rows:
                continue
            rows.append(sorted(account_rows, key=_rapid_movement_window_strength_key)[0])

        if not rows:
            return pd.DataFrame(columns=RAPID_MOVEMENT_DETECTION_COLUMNS)
        return (
            pd.DataFrame(rows, columns=RAPID_MOVEMENT_DETECTION_COLUMNS)
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
        raise RuleExecutionError(f"Failed to detect rapid movement windows: {exc}") from exc


def build_rapid_movement_alerts(
    detections: pd.DataFrame,
    accounts: pd.DataFrame,
    config: RapidMovementRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Convert rapid movement detections into common AlertRecord objects."""

    resolved_config = RapidMovementRuleConfig() if config is None else config
    try:
        if detections.empty:
            return ()
        require_columns(detections, RAPID_MOVEMENT_DETECTION_COLUMNS, "detections")
        with_customers = attach_customer_ids(detections, accounts)
        alerts: list[AlertRecord] = []
        for record in with_customers.sort_values(
            ["account_id", "detection_window_start"],
            kind="mergesort",
        ).to_dict(orient="records"):
            evidence_ids = tuple(str(value) for value in record["evidence_ids"])
            outflow_ratio = float(record["outflow_ratio"])
            risk_score = (
                resolved_config.high_ratio_risk_score
                if outflow_ratio >= resolved_config.high_ratio_threshold
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
                reason_code=build_rapid_movement_reason_code(
                    outflow_ratio,
                    resolved_config.outflow_window_hours,
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
        raise RuleExecutionError(f"Failed to build rapid movement alerts: {exc}") from exc


def run_rapid_movement_rule(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    config: RapidMovementRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Run the deterministic rapid movement rule without persistence."""

    resolved_config = RapidMovementRuleConfig() if config is None else config
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
        detections = detect_rapid_movement_windows(transactions, resolved_config)
        return build_rapid_movement_alerts(
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
        raise RuleExecutionError(f"Failed to run rapid movement rule: {exc}") from exc


def _normalise_transaction_types(
    values: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    transaction_types = tuple(str(value).strip().lower() for value in values if str(value).strip())
    if not transaction_types:
        raise RuleConfigurationError(f"at least one {field_name} value must be configured")
    return transaction_types


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


def _rapid_movement_outflow_recipient_type(row: pd.Series | dict[str, object]) -> str | None:
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


def _rapid_movement_window_strength_key(
    item: dict[str, object],
) -> tuple[float, float, float, str]:
    return (
        -float(cast(Any, item["outflow_ratio"])),
        -float(cast(Any, item["total_sent_out"])),
        -float(cast(Any, item["total_received"])),
        str(item["detection_window_start"]),
    )
