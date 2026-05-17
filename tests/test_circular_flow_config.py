"""Tests for circular flow detection configuration."""

import pytest

from graph_aml.rules import CircularFlowDetectionConfig, RuleConfigurationError


def test_default_circular_flow_config_is_valid() -> None:
    config = CircularFlowDetectionConfig()

    assert config.rule_name == "Circular flow"
    assert config.typology == "circular_flow"
    assert config.max_cycle_hops == 4


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_cycle_hops", 1),
        ("min_cycle_hops", 1),
        ("min_total_amount", -1.0),
        ("max_time_span_hours", 0),
        ("transaction_types", ()),
        ("max_cycles_per_account", 0),
        ("max_total_cycles", 0),
    ],
)
def test_invalid_circular_flow_config_values_raise(
    field: str,
    value: object,
) -> None:
    with pytest.raises(RuleConfigurationError):
        CircularFlowDetectionConfig(**{field: value})


def test_max_cycle_hops_below_min_cycle_hops_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        CircularFlowDetectionConfig(max_cycle_hops=2, min_cycle_hops=3)


def test_constructor_overrides_are_respected() -> None:
    config = CircularFlowDetectionConfig(
        rule_name="Custom circular",
        typology="custom_circular",
        max_cycle_hops=5,
        min_cycle_hops=3,
        min_total_amount=1000.0,
        max_time_span_hours=None,
        transaction_types=("WIRE",),
        include_counterparty_edges=True,
        include_self_loops=True,
        max_cycles_per_account=2,
        max_total_cycles=10,
    )

    assert config.rule_name == "Custom circular"
    assert config.typology == "custom_circular"
    assert config.max_cycle_hops == 5
    assert config.min_cycle_hops == 3
    assert config.transaction_types == ("wire",)
    assert config.include_counterparty_edges is True
    assert config.include_self_loops is True
