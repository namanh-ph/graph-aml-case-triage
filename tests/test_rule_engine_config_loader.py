"""Tests for unified rule engine YAML configuration loading."""

from pathlib import Path

import pytest

from graph_aml.rules import (
    RULE_CIRCULAR_FLOW,
    RULE_DORMANT_REACTIVATION,
    RULE_FAN_IN,
    RULE_FAN_OUT,
    RULE_RAPID_MOVEMENT,
    RULE_STRUCTURING,
    CircularFlowDetectionConfig,
    CircularFlowRuleConfig,
    DormantReactivationRuleConfig,
    FanInRuleConfig,
    FanOutRuleConfig,
    RapidMovementRuleConfig,
    RuleEngineConfigurationError,
    RuleEngineRunConfig,
    StructuringRuleConfig,
    load_individual_rule_configs,
    load_rule_engine_run_config,
)


def _write_rules_yaml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "rules.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_rule_engine_run_config_stores_enabled_rules_as_tuple() -> None:
    config = RuleEngineRunConfig(enabled_rules=["fan-in", "structuring"])

    assert config.enabled_rules == (RULE_FAN_IN, RULE_STRUCTURING)


def test_invalid_limits_raise_configuration_error() -> None:
    with pytest.raises(RuleEngineConfigurationError):
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,), limit=-1)


def test_config_loader_reads_enabled_rules_from_yaml(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(
        tmp_path,
        """
rules:
  structuring:
    enabled: true
  fan_in:
    enabled: true
  fan_out:
    enabled: false
""",
    )

    config = load_rule_engine_run_config(config_path)

    assert config.enabled_rules == (RULE_STRUCTURING, RULE_FAN_IN)


def test_disabled_yaml_rules_are_excluded(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(
        tmp_path,
        """
rules:
  structuring:
    enabled: false
  fan_in:
    enabled: true
""",
    )

    assert load_rule_engine_run_config(config_path).enabled_rules == (RULE_FAN_IN,)


def test_requested_cli_rules_narrow_enabled_rules(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(
        tmp_path,
        """
rules:
  structuring:
    enabled: true
  fan_in:
    enabled: true
""",
    )

    config = load_rule_engine_run_config(config_path, requested_rule_keys=["fan-in"])

    assert config.enabled_rules == (RULE_FAN_IN,)


def test_excluded_cli_rules_remove_enabled_rules(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(
        tmp_path,
        """
rules:
  structuring:
    enabled: true
  fan_in:
    enabled: true
""",
    )

    config = load_rule_engine_run_config(config_path, disabled_rule_keys=["fan-in"])

    assert config.enabled_rules == (RULE_STRUCTURING,)


def test_individual_config_loader_builds_structuring_config(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(tmp_path, "rules:\n  structuring:\n    enabled: true\n")

    configs = load_individual_rule_configs(config_path)

    assert isinstance(configs[RULE_STRUCTURING], StructuringRuleConfig)


def test_individual_config_loader_builds_fan_in_config(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(tmp_path, "rules:\n  fan_in:\n    enabled: true\n")

    configs = load_individual_rule_configs(config_path)

    assert isinstance(configs[RULE_FAN_IN], FanInRuleConfig)


def test_individual_config_loader_builds_fan_out_config(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(tmp_path, "rules:\n  fan_out:\n    enabled: true\n")

    configs = load_individual_rule_configs(config_path)

    assert isinstance(configs[RULE_FAN_OUT], FanOutRuleConfig)


def test_individual_config_loader_builds_rapid_movement_config(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(tmp_path, "rules:\n  rapid_movement:\n    enabled: true\n")

    configs = load_individual_rule_configs(config_path)

    assert isinstance(configs[RULE_RAPID_MOVEMENT], RapidMovementRuleConfig)


def test_individual_config_loader_builds_dormant_reactivation_config(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(
        tmp_path,
        "rules:\n  dormant_reactivation:\n    enabled: true\n",
    )

    configs = load_individual_rule_configs(config_path)

    assert isinstance(configs[RULE_DORMANT_REACTIVATION], DormantReactivationRuleConfig)


def test_individual_config_loader_builds_circular_flow_configs(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(tmp_path, "rules:\n  circular_flow:\n    enabled: true\n")

    configs = load_individual_rule_configs(config_path)
    circular_config = configs[RULE_CIRCULAR_FLOW]

    assert isinstance(circular_config, dict)
    assert isinstance(circular_config["detection_config"], CircularFlowDetectionConfig)
    assert isinstance(circular_config["alert_config"], CircularFlowRuleConfig)


def test_circular_flow_flat_config_remains_supported(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(
        tmp_path,
        """
rules:
  circular_flow:
    enabled: true
    max_cycle_hops: 3
    min_cycle_hops: 2
    min_total_amount: 100.0
    max_time_span_hours: 24
    transaction_types:
      - transfer
    include_counterparty_edges: false
    include_self_loops: false
    max_cycles_per_account: 2
    max_total_cycles: 10
""",
    )

    config = load_individual_rule_configs(config_path)[RULE_CIRCULAR_FLOW]

    assert isinstance(config, dict)
    assert config["detection_config"].max_cycle_hops == 3


def test_invalid_rule_config_raises_configuration_error(tmp_path: Path) -> None:
    config_path = _write_rules_yaml(
        tmp_path,
        """
rules:
  fan_out:
    enabled: true
    include_counterparties: false
    include_internal_accounts: false
""",
    )

    with pytest.raises(RuleEngineConfigurationError):
        load_individual_rule_configs(config_path)
