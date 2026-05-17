"""Read staged PostgreSQL inputs and run AML rules."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.alerts import persist_alerts
from graph_aml.rules.audit import write_rule_execution_audit_event
from graph_aml.rules.circular_artefacts import (
    write_circular_flow_alerts_json,
    write_circular_flow_detections_csv,
    write_circular_flow_detections_json,
    write_circular_flow_summary_json,
)
from graph_aml.rules.circular_flow import (
    CircularFlowDetectionConfig,
    CircularFlowRuleConfig,
    detect_circular_flows,
    run_circular_flow_detection_and_alerts,
)
from graph_aml.rules.dormant_reactivation import (
    DormantReactivationRuleConfig,
    run_dormant_reactivation_rule,
)
from graph_aml.rules.exceptions import RuleAuditError, RuleDataReadError, RuleExecutionError
from graph_aml.rules.fan_in import FanInRuleConfig, run_fan_in_rule
from graph_aml.rules.fan_out import FanOutRuleConfig, run_fan_out_rule
from graph_aml.rules.rapid_movement import RapidMovementRuleConfig, run_rapid_movement_rule
from graph_aml.rules.structuring import StructuringRuleConfig, run_structuring_rule
from graph_aml.rules.summary import (
    summarise_circular_flow_detections,
    summarise_rule_alerts,
)


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise RuleDataReadError("limit must be non-negative")
    return int(limit)


def read_staged_transactions_for_rules(
    engine: Engine,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read staging.transactions for deterministic rule execution."""

    safe_limit = _validate_limit(limit)
    sql = """
        SELECT
            transaction_id,
            sender_account_id,
            receiver_account_id,
            counterparty_id,
            device_id,
            transaction_timestamp,
            amount,
            currency,
            transaction_type,
            channel,
            origin_country,
            destination_country,
            is_cross_border,
            is_labelled_suspicious,
            typology_label,
            source_file
        FROM staging.transactions
        ORDER BY transaction_timestamp, transaction_id
    """
    params: dict[str, int] | None = None
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params = {"limit": safe_limit}
    try:
        return pd.read_sql_query(text(sql), engine, params=params)
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read staging.transactions: {exc}") from exc


def read_staged_accounts_for_rules(engine: Engine) -> pd.DataFrame:
    """Read staging.accounts for rule account and customer context."""

    try:
        return pd.read_sql_query(
            text(
                """
                SELECT
                    account_id,
                    customer_id,
                    account_type,
                    account_status,
                    currency,
                    home_country
                FROM staging.accounts
                ORDER BY account_id
                """
            ),
            engine,
        )
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read staging.accounts: {exc}") from exc


def read_structuring_rule_inputs(
    engine: Engine,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read staged transactions and accounts for the structuring rule."""

    try:
        transactions = read_staged_transactions_for_rules(engine, limit=limit)
        accounts = read_staged_accounts_for_rules(engine)
        return transactions, accounts
    except RuleDataReadError:
        raise
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read structuring rule inputs: {exc}") from exc


def read_fan_in_rule_inputs(
    engine: Engine,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read staged transactions and accounts for the fan-in rule."""

    try:
        transactions = read_staged_transactions_for_rules(engine, limit=limit)
        accounts = read_staged_accounts_for_rules(engine)
        return transactions, accounts
    except RuleDataReadError:
        raise
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read fan-in rule inputs: {exc}") from exc


def read_fan_out_rule_inputs(
    engine: Engine,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read staged transactions and accounts for the fan-out rule."""

    try:
        transactions = read_staged_transactions_for_rules(engine, limit=limit)
        accounts = read_staged_accounts_for_rules(engine)
        return transactions, accounts
    except RuleDataReadError:
        raise
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read fan-out rule inputs: {exc}") from exc


def read_rapid_movement_rule_inputs(
    engine: Engine,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read staged transactions and accounts for the rapid movement rule."""

    try:
        transactions = read_staged_transactions_for_rules(engine, limit=limit)
        accounts = read_staged_accounts_for_rules(engine)
        return transactions, accounts
    except RuleDataReadError:
        raise
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read rapid movement rule inputs: {exc}") from exc


def read_dormant_reactivation_rule_inputs(
    engine: Engine,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read staged transactions and accounts for the dormant reactivation rule."""

    try:
        transactions = read_staged_transactions_for_rules(engine, limit=limit)
        accounts = read_staged_accounts_for_rules(engine)
        return transactions, accounts
    except RuleDataReadError:
        raise
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read dormant reactivation rule inputs: {exc}") from exc


def read_circular_flow_detection_inputs(
    engine: Engine,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read staged transactions for circular flow detection."""

    try:
        return read_staged_transactions_for_rules(engine, limit=limit)
    except RuleDataReadError:
        raise
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read circular flow detection inputs: {exc}") from exc


def read_circular_flow_rule_inputs(
    engine: Engine,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read staged transactions and accounts for circular flow alert conversion."""

    try:
        transactions = read_staged_transactions_for_rules(engine, limit=limit)
        accounts = read_staged_accounts_for_rules(engine)
        return transactions, accounts
    except RuleDataReadError:
        raise
    except Exception as exc:
        raise RuleDataReadError(f"Failed to read circular flow rule inputs: {exc}") from exc


def run_structuring_rule_from_staged(
    engine: Engine,
    config: StructuringRuleConfig | None = None,
    limit: int | None = None,
    persist: bool = False,
    write_audit: bool = True,
) -> dict[str, object]:
    """Read staged inputs, run structuring detection, and optionally persist alerts."""

    resolved_config = StructuringRuleConfig() if config is None else config
    try:
        transactions, accounts = read_structuring_rule_inputs(engine, limit=limit)
        alerts = run_structuring_rule(transactions, accounts, resolved_config)
        alerts_persisted = 0
        if persist:
            persistence_summary = persist_alerts(
                engine,
                alerts,
                write_audit=write_audit,
                metadata={"rule_name": resolved_config.rule_name, "limit": limit},
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
        rule_summary = summarise_rule_alerts(alerts)
        if write_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=resolved_config.rule_name,
                alerts_generated=len(alerts),
                alerts_persisted=alerts_persisted,
                status="completed",
                metadata={
                    "limit": limit,
                    "persisted": persist,
                    "reporting_threshold": resolved_config.reporting_threshold,
                    "below_threshold_margin": resolved_config.below_threshold_margin,
                    "min_transaction_count": resolved_config.min_transaction_count,
                    "window_hours": resolved_config.window_hours,
                },
            )
        return {
            "rule_name": resolved_config.rule_name,
            "alerts": alerts,
            "alerts_generated": len(alerts),
            "alerts_persisted": alerts_persisted,
            "unique_account_count": rule_summary["unique_account_count"],
            "persisted": persist,
        }
    except RuleDataReadError:
        raise
    except RuleAuditError as exc:
        raise RuleExecutionError(f"Failed to audit structuring rule execution: {exc}") from exc
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to run structuring rule from staging: {exc}") from exc


def run_fan_in_rule_from_staged(
    engine: Engine,
    config: FanInRuleConfig | None = None,
    limit: int | None = None,
    persist: bool = False,
    write_audit: bool = True,
) -> dict[str, object]:
    """Read staged inputs, run fan-in detection, and optionally persist alerts."""

    resolved_config = FanInRuleConfig() if config is None else config
    try:
        transactions, accounts = read_fan_in_rule_inputs(engine, limit=limit)
        alerts = run_fan_in_rule(transactions, accounts, resolved_config)
        alerts_persisted = 0
        if persist:
            persistence_summary = persist_alerts(
                engine,
                alerts,
                write_audit=write_audit,
                metadata={"rule_name": resolved_config.rule_name, "limit": limit},
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
        rule_summary = summarise_rule_alerts(alerts)
        if write_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=resolved_config.rule_name,
                alerts_generated=len(alerts),
                alerts_persisted=alerts_persisted,
                status="completed",
                metadata={
                    "limit": limit,
                    "persisted": persist,
                    "min_unique_senders": resolved_config.min_unique_senders,
                    "window_days": resolved_config.window_days,
                    "min_total_amount": resolved_config.min_total_amount,
                },
                action="run_fan_in_rule",
            )
        return {
            "rule_name": resolved_config.rule_name,
            "alerts": alerts,
            "alerts_generated": len(alerts),
            "alerts_persisted": alerts_persisted,
            "unique_account_count": rule_summary["unique_account_count"],
            "persisted": persist,
        }
    except RuleDataReadError:
        raise
    except RuleAuditError as exc:
        raise RuleExecutionError(f"Failed to audit fan-in rule execution: {exc}") from exc
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to run fan-in rule from staging: {exc}") from exc


def run_fan_out_rule_from_staged(
    engine: Engine,
    config: FanOutRuleConfig | None = None,
    limit: int | None = None,
    persist: bool = False,
    write_audit: bool = True,
) -> dict[str, object]:
    """Read staged inputs, run fan-out detection, and optionally persist alerts."""

    resolved_config = FanOutRuleConfig() if config is None else config
    try:
        transactions, accounts = read_fan_out_rule_inputs(engine, limit=limit)
        alerts = run_fan_out_rule(transactions, accounts, resolved_config)
        alerts_persisted = 0
        if persist:
            persistence_summary = persist_alerts(
                engine,
                alerts,
                write_audit=write_audit,
                metadata={"rule_name": resolved_config.rule_name, "limit": limit},
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
        rule_summary = summarise_rule_alerts(alerts)
        if write_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=resolved_config.rule_name,
                alerts_generated=len(alerts),
                alerts_persisted=alerts_persisted,
                status="completed",
                metadata={
                    "limit": limit,
                    "persisted": persist,
                    "min_unique_recipients": resolved_config.min_unique_recipients,
                    "window_days": resolved_config.window_days,
                    "min_total_amount": resolved_config.min_total_amount,
                },
                action="run_fan_out_rule",
            )
        return {
            "rule_name": resolved_config.rule_name,
            "alerts": alerts,
            "alerts_generated": len(alerts),
            "alerts_persisted": alerts_persisted,
            "unique_account_count": rule_summary["unique_account_count"],
            "persisted": persist,
        }
    except RuleDataReadError:
        raise
    except RuleAuditError as exc:
        raise RuleExecutionError(f"Failed to audit fan-out rule execution: {exc}") from exc
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to run fan-out rule from staging: {exc}") from exc


def run_rapid_movement_rule_from_staged(
    engine: Engine,
    config: RapidMovementRuleConfig | None = None,
    limit: int | None = None,
    persist: bool = False,
    write_audit: bool = True,
) -> dict[str, object]:
    """Read staged inputs, run rapid movement detection, and optionally persist alerts."""

    resolved_config = RapidMovementRuleConfig() if config is None else config
    try:
        transactions, accounts = read_rapid_movement_rule_inputs(engine, limit=limit)
        alerts = run_rapid_movement_rule(transactions, accounts, resolved_config)
        alerts_persisted = 0
        if persist:
            persistence_summary = persist_alerts(
                engine,
                alerts,
                write_audit=write_audit,
                metadata={"rule_name": resolved_config.rule_name, "limit": limit},
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
        rule_summary = summarise_rule_alerts(alerts)
        if write_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=resolved_config.rule_name,
                alerts_generated=len(alerts),
                alerts_persisted=alerts_persisted,
                status="completed",
                metadata={
                    "limit": limit,
                    "persisted": persist,
                    "outflow_window_hours": resolved_config.outflow_window_hours,
                    "min_total_received": resolved_config.min_total_received,
                    "min_outflow_ratio": resolved_config.min_outflow_ratio,
                    "max_retained_ratio": resolved_config.max_retained_ratio,
                    "min_outgoing_transaction_count": (
                        resolved_config.min_outgoing_transaction_count
                    ),
                },
                action="run_rapid_movement_rule",
            )
        return {
            "rule_name": resolved_config.rule_name,
            "alerts": alerts,
            "alerts_generated": len(alerts),
            "alerts_persisted": alerts_persisted,
            "unique_account_count": rule_summary["unique_account_count"],
            "persisted": persist,
        }
    except RuleDataReadError:
        raise
    except RuleAuditError as exc:
        raise RuleExecutionError(f"Failed to audit rapid movement rule execution: {exc}") from exc
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to run rapid movement rule from staging: {exc}") from exc


def run_dormant_reactivation_rule_from_staged(
    engine: Engine,
    config: DormantReactivationRuleConfig | None = None,
    limit: int | None = None,
    persist: bool = False,
    write_audit: bool = True,
) -> dict[str, object]:
    """Read staged inputs, run dormant reactivation detection, and optionally persist alerts."""

    resolved_config = DormantReactivationRuleConfig() if config is None else config
    try:
        transactions, accounts = read_dormant_reactivation_rule_inputs(engine, limit=limit)
        alerts = run_dormant_reactivation_rule(transactions, accounts, resolved_config)
        alerts_persisted = 0
        if persist:
            persistence_summary = persist_alerts(
                engine,
                alerts,
                write_audit=write_audit,
                metadata={"rule_name": resolved_config.rule_name, "limit": limit},
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
        rule_summary = summarise_rule_alerts(alerts)
        if write_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=resolved_config.rule_name,
                alerts_generated=len(alerts),
                alerts_persisted=alerts_persisted,
                status="completed",
                metadata={
                    "limit": limit,
                    "persisted": persist,
                    "dormant_days_threshold": resolved_config.dormant_days_threshold,
                    "reactivation_window_days": resolved_config.reactivation_window_days,
                    "min_outbound_amount": resolved_config.min_outbound_amount,
                    "min_total_outbound_amount": resolved_config.min_total_outbound_amount,
                    "min_outbound_transaction_count": (
                        resolved_config.min_outbound_transaction_count
                    ),
                },
                action="run_dormant_reactivation_rule",
            )
        return {
            "rule_name": resolved_config.rule_name,
            "alerts": alerts,
            "alerts_generated": len(alerts),
            "alerts_persisted": alerts_persisted,
            "unique_account_count": rule_summary["unique_account_count"],
            "persisted": persist,
        }
    except RuleDataReadError:
        raise
    except RuleAuditError as exc:
        raise RuleExecutionError(
            f"Failed to audit dormant reactivation rule execution: {exc}"
        ) from exc
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to run dormant reactivation rule from staging: {exc}"
        ) from exc


def run_circular_flow_detection_from_staged(
    engine: Engine,
    config: CircularFlowDetectionConfig | None = None,
    limit: int | None = None,
    output_dir: Path | str = "reports/model_validation",
    write_artefacts: bool = True,
    write_audit: bool = True,
) -> dict[str, object]:
    """Read staged transactions, detect circular flows, and optionally write artefacts."""

    resolved_config = CircularFlowDetectionConfig() if config is None else config
    try:
        transactions = read_circular_flow_detection_inputs(engine, limit=limit)
        detections = detect_circular_flows(transactions, resolved_config)
        detection_summary = summarise_circular_flow_detections(detections)
        artefact_paths: dict[str, Path] = {}
        if write_artefacts:
            directory = Path(output_dir)
            artefact_paths = {
                "detections_json": write_circular_flow_detections_json(
                    detections,
                    directory / "circular_flow_detections.json",
                ),
                "detections_csv": write_circular_flow_detections_csv(
                    detections,
                    directory / "circular_flow_detections.csv",
                ),
                "summary_json": write_circular_flow_summary_json(
                    detection_summary,
                    directory / "circular_flow_summary.json",
                ),
            }
        if write_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=resolved_config.rule_name,
                alerts_generated=0,
                alerts_persisted=0,
                status="completed",
                metadata={
                    "limit": limit,
                    "persisted": False,
                    "cycles_detected": detection_summary["cycle_count"],
                    "artefacts_written": write_artefacts,
                    "artefact_paths": {key: str(path) for key, path in artefact_paths.items()},
                    "max_cycle_hops": resolved_config.max_cycle_hops,
                    "min_cycle_hops": resolved_config.min_cycle_hops,
                    "min_total_amount": resolved_config.min_total_amount,
                    "max_time_span_hours": resolved_config.max_time_span_hours,
                },
                action="detect_circular_flows",
            )
        return {
            "rule_name": resolved_config.rule_name,
            "cycles_detected": detection_summary["cycle_count"],
            "unique_primary_account_count": detection_summary["unique_primary_account_count"],
            "artefacts_written": write_artefacts,
            "persisted": False,
        }
    except RuleDataReadError:
        raise
    except RuleAuditError as exc:
        raise RuleExecutionError(
            f"Failed to audit circular flow detection execution: {exc}"
        ) from exc
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to run circular flow detection from staging: {exc}"
        ) from exc


def run_circular_flow_rule_from_staged(
    engine: Engine,
    detection_config: CircularFlowDetectionConfig | None = None,
    alert_config: CircularFlowRuleConfig | None = None,
    limit: int | None = None,
    persist: bool = False,
    write_audit: bool = True,
    write_artefacts: bool = True,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, object]:
    """Read staged inputs, run circular-flow alert conversion, and optionally persist alerts."""

    resolved_alert_config = CircularFlowRuleConfig() if alert_config is None else alert_config
    resolved_detection_config = (
        detection_config if detection_config is not None else resolved_alert_config.detection_config
    )
    try:
        transactions, accounts = read_circular_flow_rule_inputs(engine, limit=limit)
        result = run_circular_flow_detection_and_alerts(
            transactions,
            accounts,
            detection_config=resolved_detection_config,
            alert_config=resolved_alert_config,
        )
        detections = result["detections"]
        alerts = result["alerts"]
        detection_summary = result["detection_summary"]
        alert_summary = result["alert_summary"]
        if not isinstance(detections, pd.DataFrame):
            raise RuleExecutionError("circular flow detections payload must be a DataFrame")
        if not isinstance(alerts, tuple):
            raise RuleExecutionError("circular flow alerts payload must be a tuple")
        if not isinstance(detection_summary, dict):
            raise RuleExecutionError("circular flow detection summary must be a dictionary")
        if not isinstance(alert_summary, dict):
            raise RuleExecutionError("circular flow alert summary must be a dictionary")

        artefact_paths: dict[str, Path] = {}
        if write_artefacts:
            directory = Path(output_dir)
            artefact_paths = {
                "detections_json": write_circular_flow_detections_json(
                    detections,
                    directory / "circular_flow_detections.json",
                ),
                "detections_csv": write_circular_flow_detections_csv(
                    detections,
                    directory / "circular_flow_detections.csv",
                ),
                "summary_json": write_circular_flow_summary_json(
                    detection_summary,
                    directory / "circular_flow_summary.json",
                ),
                "alerts_json": write_circular_flow_alerts_json(
                    alerts,
                    directory / "circular_flow_alerts.json",
                ),
            }
        alerts_persisted = 0
        if persist:
            persistence_summary = persist_alerts(
                engine,
                alerts,
                write_audit=write_audit,
                metadata={"rule_name": resolved_alert_config.rule_name, "limit": limit},
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
        if write_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=resolved_alert_config.rule_name,
                alerts_generated=len(alerts),
                alerts_persisted=alerts_persisted,
                status="completed",
                metadata={
                    "limit": limit,
                    "persisted": persist,
                    "cycles_detected": detection_summary["cycle_count"],
                    "artefacts_written": write_artefacts,
                    "artefact_paths": {key: str(path) for key, path in artefact_paths.items()},
                    "max_cycle_hops": resolved_detection_config.max_cycle_hops
                    if resolved_detection_config is not None
                    else None,
                    "min_cycle_hops": resolved_detection_config.min_cycle_hops
                    if resolved_detection_config is not None
                    else None,
                    "min_total_amount": resolved_detection_config.min_total_amount
                    if resolved_detection_config is not None
                    else None,
                    "max_time_span_hours": resolved_detection_config.max_time_span_hours
                    if resolved_detection_config is not None
                    else None,
                    "high_amount_threshold": resolved_alert_config.high_amount_threshold,
                    "long_cycle_hop_threshold": (resolved_alert_config.long_cycle_hop_threshold),
                },
                action="run_circular_flow_rule",
            )
        return {
            "rule_name": resolved_alert_config.rule_name,
            "cycles_detected": detection_summary["cycle_count"],
            "alerts": alerts,
            "alerts_generated": len(alerts),
            "alerts_persisted": alerts_persisted,
            "unique_account_count": alert_summary["unique_account_count"],
            "artefacts_written": write_artefacts,
            "artefacts": artefact_paths,
            "persisted": persist,
        }
    except RuleDataReadError:
        raise
    except RuleAuditError as exc:
        raise RuleExecutionError(f"Failed to audit circular flow rule execution: {exc}") from exc
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to run circular flow rule from staging: {exc}") from exc
