"""Tests for AML rule threshold documentation coverage."""

from graph_aml.rules import (
    CircularFlowDetectionConfig,
    CircularFlowRuleConfig,
    DormantReactivationRuleConfig,
    FanInRuleConfig,
    FanOutRuleConfig,
    RapidMovementRuleConfig,
    StructuringRuleConfig,
    get_rule_documentation,
)


def _threshold_names(rule_key: str) -> set[str]:
    return {threshold.name for threshold in get_rule_documentation(rule_key).thresholds}


def _threshold_defaults(rule_key: str) -> dict[str, object]:
    return {
        threshold.name: threshold.default_value
        for threshold in get_rule_documentation(rule_key).thresholds
    }


def test_structuring_threshold_docs_include_required_thresholds() -> None:
    assert {
        "reporting_threshold",
        "below_threshold_margin",
        "min_transaction_count",
        "window_hours",
        "transaction_types",
        "include_counterparty_payments",
        "base_risk_score",
        "high_count_risk_score",
        "high_count_multiplier",
    }.issubset(_threshold_names("structuring"))


def test_fan_in_threshold_docs_include_required_thresholds() -> None:
    assert {
        "min_unique_senders",
        "window_days",
        "min_total_amount",
        "transaction_types",
        "include_internal_account_receipts",
        "base_risk_score",
        "high_sender_risk_score",
        "high_sender_multiplier",
    }.issubset(_threshold_names("fan_in"))


def test_fan_out_threshold_docs_include_required_thresholds() -> None:
    assert {
        "min_unique_recipients",
        "window_days",
        "min_total_amount",
        "transaction_types",
        "include_counterparties",
        "include_internal_accounts",
        "base_risk_score",
        "high_recipient_risk_score",
        "high_recipient_multiplier",
    }.issubset(_threshold_names("fan_out"))


def test_rapid_movement_threshold_docs_include_required_thresholds() -> None:
    assert {
        "outflow_window_hours",
        "min_total_received",
        "min_outflow_ratio",
        "max_retained_ratio",
        "min_outgoing_transaction_count",
        "inbound_transaction_types",
        "outbound_transaction_types",
        "include_counterparty_outflows",
        "include_internal_account_outflows",
        "base_risk_score",
        "high_ratio_risk_score",
        "high_ratio_threshold",
    }.issubset(_threshold_names("rapid_movement"))


def test_dormant_reactivation_threshold_docs_include_required_thresholds() -> None:
    assert {
        "dormant_days_threshold",
        "reactivation_window_days",
        "min_outbound_amount",
        "min_total_outbound_amount",
        "min_outbound_transaction_count",
        "outbound_transaction_types",
        "include_counterparty_outflows",
        "include_internal_account_outflows",
        "base_risk_score",
        "high_value_risk_score",
        "high_value_multiplier",
    }.issubset(_threshold_names("dormant_reactivation"))


def test_circular_flow_threshold_docs_include_detection_and_alert_thresholds() -> None:
    assert {
        "max_cycle_hops",
        "min_cycle_hops",
        "min_total_amount",
        "max_time_span_hours",
        "transaction_types",
        "include_counterparty_edges",
        "include_self_loops",
        "max_cycles_per_account",
        "max_total_cycles",
        "severity",
        "base_risk_score",
        "high_amount_risk_score",
        "high_amount_threshold",
        "long_cycle_risk_score",
        "long_cycle_hop_threshold",
    }.issubset(_threshold_names("circular_flow"))


def test_each_threshold_has_config_path_rationale_and_tuning_guidance() -> None:
    for rule_key in (
        "structuring",
        "fan_in",
        "fan_out",
        "rapid_movement",
        "dormant_reactivation",
        "circular_flow",
    ):
        for threshold in get_rule_documentation(rule_key).thresholds:
            assert threshold.config_path.startswith(f"rules.{rule_key}.")
            assert "<rule_key>" not in threshold.config_path
            assert threshold.rationale
            assert threshold.tuning_guidance


def test_threshold_defaults_are_consistent_with_config_dataclasses() -> None:
    assert (
        _threshold_defaults("structuring")["window_hours"] == StructuringRuleConfig().window_hours
    )
    assert _threshold_defaults("fan_in")["window_days"] == FanInRuleConfig().window_days
    assert _threshold_defaults("fan_out")["window_days"] == FanOutRuleConfig().window_days
    assert (
        _threshold_defaults("rapid_movement")["outflow_window_hours"]
        == RapidMovementRuleConfig().outflow_window_hours
    )
    assert (
        _threshold_defaults("dormant_reactivation")["dormant_days_threshold"]
        == DormantReactivationRuleConfig().dormant_days_threshold
    )
    assert (
        _threshold_defaults("circular_flow")["max_cycle_hops"]
        == CircularFlowDetectionConfig().max_cycle_hops
    )
    assert (
        _threshold_defaults("circular_flow")["high_amount_threshold"]
        == CircularFlowRuleConfig().high_amount_threshold
    )
