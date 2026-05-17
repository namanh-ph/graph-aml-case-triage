"""Unified execution engine for deterministic AML rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine

from graph_aml.alerts.schema import AlertRecord
from graph_aml.rules.audit import write_rule_engine_audit_event
from graph_aml.rules.circular_flow import CircularFlowDetectionConfig, CircularFlowRuleConfig
from graph_aml.rules.config_loader import RuleEngineRunConfig, load_individual_rule_configs
from graph_aml.rules.exceptions import RuleEngineError, RuleRegistryError
from graph_aml.rules.registry import (
    DEFAULT_RULE_ORDER,
    RULE_CIRCULAR_FLOW,
    get_rule_definition,
    validate_rule_keys,
)
from graph_aml.rules.summary import summarise_rule_alerts


@dataclass(frozen=True)
class RuleExecutionResult:
    """Normalised result for one deterministic AML rule execution."""

    rule_key: str
    rule_name: str
    typology: str
    alerts: tuple[AlertRecord, ...] = field(default_factory=tuple)
    alerts_generated: int = 0
    alerts_persisted: int = 0
    unique_account_count: int = 0
    persisted: bool = False
    artefacts: dict[str, Path] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RuleEngineExecutionResult:
    """Combined result for a unified AML rule-engine execution."""

    rule_results: tuple[RuleExecutionResult, ...]
    alerts: tuple[AlertRecord, ...]
    alerts_generated: int
    alerts_persisted: int
    unique_account_count: int
    unique_rule_count: int
    unique_typology_count: int
    persisted: bool
    artefacts: dict[str, Path]
    summary: dict[str, object]


def summarise_engine_alerts(
    alerts: tuple[AlertRecord, ...] | list[AlertRecord],
) -> dict[str, object]:
    """Summarise alerts produced by the unified rule engine."""

    return summarise_rule_alerts(tuple(alerts))


def build_rule_execution_result(
    rule_key: str,
    alerts: tuple[AlertRecord, ...] | list[AlertRecord],
    alerts_persisted: int = 0,
    persisted: bool = False,
    artefacts: dict[str, Path] | None = None,
    metadata: dict[str, object] | None = None,
) -> RuleExecutionResult:
    """Build a normalised single-rule execution result from alert records."""

    definition = get_rule_definition(rule_key)
    alert_tuple = tuple(alerts)
    alert_summary = summarise_rule_alerts(alert_tuple)
    return RuleExecutionResult(
        rule_key=definition.rule_key,
        rule_name=definition.rule_name,
        typology=definition.typology,
        alerts=alert_tuple,
        alerts_generated=len(alert_tuple),
        alerts_persisted=int(alerts_persisted),
        unique_account_count=int(cast(Any, alert_summary["unique_account_count"])),
        persisted=bool(persisted),
        artefacts={} if artefacts is None else dict(artefacts),
        metadata={} if metadata is None else dict(metadata),
    )


def combine_rule_execution_results(
    results: tuple[RuleExecutionResult, ...] | list[RuleExecutionResult],
    persisted: bool = False,
) -> RuleEngineExecutionResult:
    """Combine ordered rule results into one engine-level result."""

    ordered_results = tuple(sorted(results, key=lambda result: _rule_order_index(result.rule_key)))
    alerts = tuple(alert for result in ordered_results for alert in result.alerts)
    alert_summary = summarise_engine_alerts(alerts)
    artefacts: dict[str, Path] = {}
    for result in ordered_results:
        for key, path in result.artefacts.items():
            artefacts[f"{result.rule_key}.{key}"] = path
    alerts_generated = sum(result.alerts_generated for result in ordered_results)
    alerts_persisted = sum(result.alerts_persisted for result in ordered_results)
    unique_rule_count = len({result.rule_key for result in ordered_results})
    unique_typology_count = len({result.typology for result in ordered_results})
    summary = {
        "rules_run": [result.rule_key for result in ordered_results],
        "alerts_generated": alerts_generated,
        "alerts_persisted": alerts_persisted,
        "unique_account_count": int(cast(Any, alert_summary["unique_account_count"])),
        "severity_counts": alert_summary["severity_counts"],
        "rule_name_counts": alert_summary["rule_name_counts"],
        "typology_counts": alert_summary["typology_counts"],
        "persisted": bool(persisted),
        "artefact_count": len(artefacts),
    }
    return RuleEngineExecutionResult(
        rule_results=ordered_results,
        alerts=alerts,
        alerts_generated=alerts_generated,
        alerts_persisted=alerts_persisted,
        unique_account_count=int(cast(Any, alert_summary["unique_account_count"])),
        unique_rule_count=unique_rule_count,
        unique_typology_count=unique_typology_count,
        persisted=bool(persisted),
        artefacts=artefacts,
        summary=summary,
    )


def run_rule_in_memory(
    rule_key: str,
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    rule_config: object | None = None,
    model_run_id: str | None = None,
) -> RuleExecutionResult:
    """Run one registered deterministic AML rule against in-memory DataFrames."""

    try:
        definition = get_rule_definition(rule_key)
        if definition.rule_key == RULE_CIRCULAR_FLOW:
            detection_config, alert_config = _split_circular_flow_config(rule_config)
            alerts = definition.run_in_memory(
                transactions,
                accounts,
                detection_config=detection_config,
                alert_config=alert_config,
                model_run_id=model_run_id,
            )
        else:
            alerts = definition.run_in_memory(
                transactions,
                accounts,
                rule_config,
                model_run_id=model_run_id,
            )
        return build_rule_execution_result(definition.rule_key, tuple(alerts))
    except RuleRegistryError:
        raise
    except Exception as exc:
        raise RuleEngineError(f"Failed to run rule {rule_key}: {exc}") from exc


def run_rules_in_memory(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    rule_keys: tuple[str, ...] | list[str] | None = None,
    rule_configs: dict[str, object] | None = None,
    model_run_id: str | None = None,
) -> RuleEngineExecutionResult:
    """Run selected deterministic AML rules against in-memory DataFrames."""

    try:
        selected_rule_keys = (
            validate_rule_keys(rule_keys) if rule_keys is not None else tuple(DEFAULT_RULE_ORDER)
        )
        normalised_configs = _normalise_rule_config_mapping(rule_configs)
        results = tuple(
            run_rule_in_memory(
                rule_key,
                transactions,
                accounts,
                rule_config=normalised_configs.get(rule_key),
                model_run_id=model_run_id,
            )
            for rule_key in selected_rule_keys
        )
        return combine_rule_execution_results(results, persisted=False)
    except RuleRegistryError:
        raise
    except RuleEngineError:
        raise
    except Exception as exc:
        raise RuleEngineError(f"Failed to run AML rules in memory: {exc}") from exc


def run_rule_from_staged(
    engine: Engine,
    rule_key: str,
    rule_config: object | None = None,
    limit: int | None = None,
    persist: bool = False,
    write_audit: bool = True,
    write_artefacts: bool = True,
    output_dir: Path | str = "reports/model_validation",
) -> RuleExecutionResult:
    """Run one registered deterministic AML rule against staged database tables."""

    try:
        definition = get_rule_definition(rule_key)
        if definition.rule_key == RULE_CIRCULAR_FLOW:
            detection_config, alert_config = _split_circular_flow_config(rule_config)
            payload = definition.run_from_staged(
                engine,
                detection_config=detection_config,
                alert_config=alert_config,
                limit=limit,
                persist=persist,
                write_audit=write_audit,
                write_artefacts=write_artefacts,
                output_dir=output_dir,
            )
        else:
            payload = definition.run_from_staged(
                engine,
                config=rule_config,
                limit=limit,
                persist=persist,
                write_audit=write_audit,
            )
        if not isinstance(payload, dict):
            raise RuleEngineError(f"Staged rule {definition.rule_key} returned invalid payload")
        return _build_result_from_staged_payload(definition.rule_key, payload)
    except RuleRegistryError:
        raise
    except RuleEngineError:
        raise
    except Exception as exc:
        raise RuleEngineError(f"Failed to run staged rule {rule_key}: {exc}") from exc


def run_rules_from_staged(
    engine: Engine,
    rule_keys: tuple[str, ...] | list[str] | None = None,
    rule_configs: dict[str, object] | None = None,
    limit: int | None = None,
    persist: bool = False,
    write_audit: bool = True,
    write_artefacts: bool = True,
    output_dir: Path | str = "reports/model_validation",
) -> RuleEngineExecutionResult:
    """Run selected deterministic AML rules against staged database tables."""

    try:
        selected_rule_keys = (
            validate_rule_keys(rule_keys) if rule_keys is not None else tuple(DEFAULT_RULE_ORDER)
        )
        normalised_configs = _normalise_rule_config_mapping(rule_configs)
        results = tuple(
            run_rule_from_staged(
                engine,
                rule_key,
                rule_config=normalised_configs.get(rule_key),
                limit=limit,
                persist=persist,
                write_audit=write_audit,
                write_artefacts=write_artefacts,
                output_dir=output_dir,
            )
            for rule_key in selected_rule_keys
        )
        return combine_rule_execution_results(results, persisted=persist)
    except RuleRegistryError:
        raise
    except RuleEngineError:
        raise
    except Exception as exc:
        raise RuleEngineError(f"Failed to run AML rules from staged data: {exc}") from exc


def run_rule_engine_from_staged(
    engine: Engine,
    run_config: RuleEngineRunConfig | None = None,
    rule_configs: dict[str, object] | None = None,
    write_engine_audit: bool = True,
) -> RuleEngineExecutionResult:
    """Run the unified AML rule engine against staged data with optional audit."""

    resolved_run_config = (
        RuleEngineRunConfig(enabled_rules=tuple(DEFAULT_RULE_ORDER))
        if run_config is None
        else run_config
    )
    try:
        resolved_rule_configs = (
            load_individual_rule_configs(rule_keys=resolved_run_config.enabled_rules)
            if rule_configs is None
            else _normalise_rule_config_mapping(rule_configs)
        )
        result = run_rules_from_staged(
            engine,
            rule_keys=resolved_run_config.enabled_rules,
            rule_configs=resolved_rule_configs,
            limit=resolved_run_config.limit,
            persist=resolved_run_config.persist_alerts,
            write_audit=resolved_run_config.write_audit,
            write_artefacts=resolved_run_config.write_artefacts,
            output_dir=resolved_run_config.output_dir,
        )
        if write_engine_audit and resolved_run_config.write_audit:
            write_rule_engine_audit_event(
                engine,
                rules_run=tuple(cast(list[str], result.summary["rules_run"])),
                alerts_generated=result.alerts_generated,
                alerts_persisted=result.alerts_persisted,
                status="completed",
                metadata=result.summary,
            )
        return result
    except RuleEngineError:
        raise
    except Exception as exc:
        raise RuleEngineError(f"Failed to run AML rule engine from staged data: {exc}") from exc


def _build_result_from_staged_payload(
    rule_key: str,
    payload: dict[str, object],
) -> RuleExecutionResult:
    definition = get_rule_definition(rule_key)
    alerts = payload.get("alerts", ())
    alert_tuple = tuple(alerts) if isinstance(alerts, tuple | list) else ()
    artefacts_payload = payload.get("artefacts", {})
    artefacts = (
        {str(key): Path(value) for key, value in artefacts_payload.items()}
        if isinstance(artefacts_payload, dict)
        else {}
    )
    return RuleExecutionResult(
        rule_key=definition.rule_key,
        rule_name=str(payload.get("rule_name", definition.rule_name)),
        typology=definition.typology,
        alerts=cast(tuple[AlertRecord, ...], alert_tuple),
        alerts_generated=int(cast(Any, payload.get("alerts_generated", len(alert_tuple))) or 0),
        alerts_persisted=int(cast(Any, payload.get("alerts_persisted", 0)) or 0),
        unique_account_count=int(cast(Any, payload.get("unique_account_count", 0)) or 0),
        persisted=bool(payload.get("persisted", False)),
        artefacts=artefacts,
        metadata={
            key: value
            for key, value in payload.items()
            if key
            not in {
                "alerts",
                "alerts_generated",
                "alerts_persisted",
                "unique_account_count",
                "persisted",
                "artefacts",
            }
        },
    )


def _split_circular_flow_config(
    rule_config: object | None,
) -> tuple[CircularFlowDetectionConfig | None, CircularFlowRuleConfig | None]:
    if rule_config is None:
        return None, None
    if isinstance(rule_config, CircularFlowRuleConfig):
        return rule_config.detection_config, rule_config
    if isinstance(rule_config, CircularFlowDetectionConfig):
        return rule_config, CircularFlowRuleConfig(detection_config=rule_config)
    if isinstance(rule_config, dict):
        detection_config = cast(
            CircularFlowDetectionConfig | None,
            rule_config.get("detection_config") or rule_config.get("detection"),
        )
        alert_config = cast(
            CircularFlowRuleConfig | None,
            rule_config.get("alert_config") or rule_config.get("alert"),
        )
        if alert_config is not None and detection_config is None:
            detection_config = alert_config.detection_config
        return detection_config, alert_config
    raise RuleEngineError("Unsupported circular flow rule config payload")


def _normalise_rule_config_mapping(
    rule_configs: dict[str, object] | None,
) -> dict[str, object]:
    if not rule_configs:
        return {}
    normalised: dict[str, object] = {}
    for rule_key, config in rule_configs.items():
        normalised[validate_rule_keys([rule_key])[0]] = config
    return normalised


def _rule_order_index(rule_key: str) -> int:
    try:
        return DEFAULT_RULE_ORDER.index(rule_key)
    except ValueError:
        return len(DEFAULT_RULE_ORDER)
