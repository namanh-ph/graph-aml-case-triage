"""Tests for unified rule engine execution result helpers."""

import json
from pathlib import Path

from graph_aml.alerts import AlertRecord
from graph_aml.rules import (
    RULE_FAN_IN,
    RULE_STRUCTURING,
    RuleEngineExecutionResult,
    RuleExecutionResult,
    build_rule_execution_result,
    combine_rule_execution_results,
)


def _alert(
    alert_id: str,
    account_id: str,
    rule_name: str = "Structuring",
    typology: str = "structuring",
) -> AlertRecord:
    return AlertRecord(
        alert_id=alert_id,
        account_id=account_id,
        customer_id=f"CUST_{account_id}",
        rule_name=rule_name,
        typology=typology,
        severity="high",
        risk_score_rule=80.0,
        reason_code="test",
        evidence_ids=(f"TXN_{alert_id}",),
        detection_window_start="2025-01-01T00:00:00+00:00",
        detection_window_end="2025-01-01T01:00:00+00:00",
    )


def test_rule_execution_result_defaults_are_safe() -> None:
    result = RuleExecutionResult("structuring", "Structuring", "structuring")

    assert result.alerts == ()
    assert result.artefacts == {}
    assert result.metadata == {}


def test_rule_engine_execution_result_stores_combined_fields() -> None:
    result = RuleEngineExecutionResult((), (), 0, 0, 0, 0, 0, False, {}, {})

    assert result.rule_results == ()
    assert result.alerts == ()


def test_build_rule_execution_result_counts_alerts() -> None:
    result = build_rule_execution_result(RULE_STRUCTURING, [_alert("A1", "ACC_1")])

    assert result.alerts_generated == 1


def test_build_rule_execution_result_counts_unique_accounts() -> None:
    result = build_rule_execution_result(
        RULE_STRUCTURING,
        [_alert("A1", "ACC_1"), _alert("A2", "ACC_1")],
    )

    assert result.unique_account_count == 1


def test_result_metadata_is_preserved() -> None:
    result = build_rule_execution_result(RULE_STRUCTURING, [], metadata={"x": 1})

    assert result.metadata == {"x": 1}


def test_artefact_paths_are_preserved() -> None:
    result = build_rule_execution_result(
        RULE_STRUCTURING,
        [],
        artefacts={"summary_json": Path("summary.json")},
    )

    assert result.artefacts["summary_json"] == Path("summary.json")


def test_combine_rule_execution_results_concatenates_alerts_in_rule_order() -> None:
    fan_in = RuleExecutionResult(
        RULE_FAN_IN,
        "Fan-in",
        "fan_in",
        alerts=(_alert("F1", "ACC_2", "Fan-in", "fan_in"),),
        alerts_generated=1,
    )
    structuring = RuleExecutionResult(
        RULE_STRUCTURING,
        "Structuring",
        "structuring",
        alerts=(_alert("S1", "ACC_1"),),
        alerts_generated=1,
    )

    result = combine_rule_execution_results([fan_in, structuring])

    assert [alert.alert_id for alert in result.alerts] == ["S1", "F1"]


def test_combined_result_sums_generated_alerts() -> None:
    result = combine_rule_execution_results(
        [
            RuleExecutionResult(RULE_STRUCTURING, "Structuring", "structuring", alerts_generated=2),
            RuleExecutionResult(RULE_FAN_IN, "Fan-in", "fan_in", alerts_generated=3),
        ]
    )

    assert result.alerts_generated == 5


def test_combined_result_sums_persisted_alerts() -> None:
    result = combine_rule_execution_results(
        [
            RuleExecutionResult(
                RULE_STRUCTURING,
                "Structuring",
                "structuring",
                alerts_persisted=1,
            ),
            RuleExecutionResult(RULE_FAN_IN, "Fan-in", "fan_in", alerts_persisted=2),
        ]
    )

    assert result.alerts_persisted == 3


def test_combined_result_counts_unique_rules_and_typologies() -> None:
    result = combine_rule_execution_results(
        [
            RuleExecutionResult(RULE_STRUCTURING, "Structuring", "structuring"),
            RuleExecutionResult(RULE_FAN_IN, "Fan-in", "fan_in"),
        ]
    )

    assert result.unique_rule_count == 2
    assert result.unique_typology_count == 2


def test_combined_summary_is_json_serialisable() -> None:
    result = combine_rule_execution_results(
        [build_rule_execution_result(RULE_STRUCTURING, [_alert("A1", "ACC_1")])]
    )

    json.dumps(result.summary)


def test_empty_result_collections_are_handled_gracefully() -> None:
    result = combine_rule_execution_results([])

    assert result.alerts_generated == 0
    assert result.summary["rules_run"] == []
