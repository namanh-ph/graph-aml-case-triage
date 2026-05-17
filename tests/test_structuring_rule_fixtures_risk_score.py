"""Fixture-based risk score tests for structuring alerts."""

import pytest

from graph_aml.rules import (
    RuleConfigurationError,
    StructuringRuleConfig,
    run_structuring_rule,
)
from tests.fixtures.structuring_fixtures import (
    build_structuring_accounts_fixture,
    build_structuring_trigger_transactions_fixture,
)


def test_base_risk_score_is_used_for_standard_detections() -> None:
    alert = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(count=8),
        build_structuring_accounts_fixture(),
    )[0]

    assert alert.risk_score_rule == 80.0


def test_high_count_risk_score_is_used_when_multiplier_is_reached() -> None:
    config = StructuringRuleConfig(min_transaction_count=8, high_count_multiplier=1.5)

    alert = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(count=12),
        build_structuring_accounts_fixture(),
        config,
    )[0]

    assert alert.risk_score_rule == 90.0


def test_custom_base_risk_score_is_respected() -> None:
    config = StructuringRuleConfig(base_risk_score=72.5, high_count_multiplier=2.0)

    alert = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(count=8),
        build_structuring_accounts_fixture(),
        config,
    )[0]

    assert alert.risk_score_rule == 72.5


def test_custom_high_count_risk_score_is_respected() -> None:
    config = StructuringRuleConfig(high_count_risk_score=95.0, high_count_multiplier=1.5)

    alert = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(count=12),
        build_structuring_accounts_fixture(),
        config,
    )[0]

    assert alert.risk_score_rule == 95.0


def test_risk_scores_remain_within_zero_to_one_hundred() -> None:
    alert = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(),
        build_structuring_accounts_fixture(),
    )[0]

    assert 0 <= alert.risk_score_rule <= 100


def test_invalid_score_configuration_is_rejected() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(high_count_risk_score=-1)
