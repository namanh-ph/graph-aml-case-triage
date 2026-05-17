"""Tests for circular flow alert helper functions."""

import pandas as pd
import pytest

from graph_aml.rules import (
    CircularFlowRuleConfig,
    RuleExecutionError,
    RuleInputError,
    attach_circular_flow_customer_ids,
    build_circular_flow_reason_code,
    calculate_circular_flow_rule_score,
    detect_circular_flows,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_accounts_fixture,
    build_circular_flow_three_hop_transactions_fixture,
    build_circular_flow_two_hop_transactions_fixture,
)


def _two_hop_detection() -> dict[str, object]:
    detections = detect_circular_flows(build_circular_flow_two_hop_transactions_fixture())
    return detections.iloc[0].to_dict()


def test_reason_code_includes_cycle_length_amount_and_time_span() -> None:
    reason = build_circular_flow_reason_code(4, 25000.0, 36)

    assert "4-account circular flow" in reason
    assert "25000.00" in reason
    assert "36.0 hours" in reason


def test_reason_code_handles_missing_time_span() -> None:
    reason = build_circular_flow_reason_code(4, 25000.0, None)

    assert reason == "4-account circular flow with 25000.00 total value"


def test_custom_reason_code_template_works() -> None:
    reason = build_circular_flow_reason_code(
        3,
        12345.6,
        4,
        template="{cycle_length}:{total_amount_formatted}:{time_span_hours_formatted}",
    )

    assert reason == "3:12345.60:4.0"


@pytest.mark.parametrize(
    ("cycle_length", "amount", "span"),
    [
        (1, 100.0, 1),
        (2, -1.0, 1),
        (2, 100.0, -1),
        ("bad", 100.0, 1),
        (2, "bad", 1),
    ],
)
def test_invalid_reason_code_inputs_raise(
    cycle_length: object,
    amount: object,
    span: object,
) -> None:
    with pytest.raises(RuleInputError):
        build_circular_flow_reason_code(cycle_length, amount, span)


def test_customer_id_attachment_joins_primary_account_customer_ids() -> None:
    detections = detect_circular_flows(build_circular_flow_two_hop_transactions_fixture())
    accounts = build_circular_flow_accounts_fixture()

    output = attach_circular_flow_customer_ids(detections, accounts)

    assert output.loc[0, "customer_id"] == "CUST_CF_A"


def test_customer_id_attachment_leaves_missing_customer_ids_null() -> None:
    detections = detect_circular_flows(build_circular_flow_two_hop_transactions_fixture())
    accounts = pd.DataFrame(columns=["account_id", "customer_id"])

    output = attach_circular_flow_customer_ids(detections, accounts)

    assert output.loc[0, "customer_id"] is None


def test_rule_score_uses_base_score_by_default() -> None:
    detection = _two_hop_detection()

    score = calculate_circular_flow_rule_score(detection, CircularFlowRuleConfig())

    assert score == 85.0


def test_rule_score_uses_high_amount_score_when_threshold_is_met() -> None:
    detection = _two_hop_detection()

    score = calculate_circular_flow_rule_score(
        detection,
        CircularFlowRuleConfig(high_amount_threshold=10000.0),
    )

    assert score == 90.0


def test_rule_score_uses_long_cycle_score_when_hop_threshold_is_met() -> None:
    detection = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture()).iloc[0]

    score = calculate_circular_flow_rule_score(
        detection,
        CircularFlowRuleConfig(long_cycle_hop_threshold=3, long_cycle_risk_score=91.0),
    )

    assert score == 91.0


def test_rule_score_uses_maximum_applicable_score() -> None:
    detection = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture()).iloc[0]

    score = calculate_circular_flow_rule_score(
        detection,
        CircularFlowRuleConfig(
            high_amount_threshold=1000.0,
            high_amount_risk_score=88.0,
            long_cycle_hop_threshold=3,
            long_cycle_risk_score=93.0,
        ),
    )

    assert score == 93.0


def test_invalid_score_payload_raises_rule_execution_error() -> None:
    with pytest.raises(RuleExecutionError):
        calculate_circular_flow_rule_score({"total_amount": "bad", "cycle_length": 2})
