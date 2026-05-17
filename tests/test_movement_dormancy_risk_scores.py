"""Risk-score tests for rapid movement and dormant reactivation."""

import pytest

from graph_aml.rules import (
    DormantReactivationRuleConfig,
    RapidMovementRuleConfig,
    RuleConfigurationError,
    run_dormant_reactivation_rule,
    run_rapid_movement_rule,
)
from tests.fixtures.movement_dormancy_fixtures import (
    build_dormant_reactivation_only_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
    build_movement_dormancy_high_value_transactions_fixture,
    build_rapid_movement_only_transactions_fixture,
)


def test_rapid_base_risk_score_is_used_for_standard_detections() -> None:
    alert = run_rapid_movement_rule(
        build_rapid_movement_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert alert.risk_score_rule == 80.0


def test_rapid_high_ratio_score_is_used_at_threshold() -> None:
    alerts = run_rapid_movement_rule(
        build_movement_dormancy_high_value_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )

    assert alerts[0].risk_score_rule == 90.0


def test_dormant_base_risk_score_is_used_for_standard_detections() -> None:
    alert = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert alert.risk_score_rule == 80.0


def test_dormant_high_value_score_is_used_at_multiplier() -> None:
    alerts = run_dormant_reactivation_rule(
        build_movement_dormancy_high_value_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )

    assert alerts[0].risk_score_rule == 90.0


def test_custom_rapid_base_risk_score_is_respected() -> None:
    config = RapidMovementRuleConfig(base_risk_score=77.0)
    alert = run_rapid_movement_rule(
        build_rapid_movement_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
        config,
    )[0]

    assert alert.risk_score_rule == 77.0


def test_custom_rapid_high_ratio_risk_score_is_respected() -> None:
    config = RapidMovementRuleConfig(high_ratio_risk_score=96.0)
    alert = run_rapid_movement_rule(
        build_movement_dormancy_high_value_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
        config,
    )[0]

    assert alert.risk_score_rule == 96.0


def test_custom_dormant_base_risk_score_is_respected() -> None:
    config = DormantReactivationRuleConfig(base_risk_score=76.0)
    alert = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
        config,
    )[0]

    assert alert.risk_score_rule == 76.0


def test_custom_dormant_high_value_risk_score_is_respected() -> None:
    config = DormantReactivationRuleConfig(high_value_risk_score=97.0)
    alert = run_dormant_reactivation_rule(
        build_movement_dormancy_high_value_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
        config,
    )[0]

    assert alert.risk_score_rule == 97.0


def test_invalid_rapid_score_configuration_is_rejected() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(base_risk_score=-1)


def test_invalid_dormant_score_configuration_is_rejected() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(high_value_risk_score=101)
