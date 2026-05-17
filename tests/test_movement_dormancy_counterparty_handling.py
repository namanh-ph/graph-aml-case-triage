"""Counterparty and internal-recipient handling tests for both rules."""

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
    build_rapid_movement_only_transactions_fixture,
)


def test_rapid_includes_counterparty_outflows_when_enabled() -> None:
    frame = _rapid_counterparty_fixture()

    assert run_rapid_movement_rule(frame, build_movement_dormancy_accounts_fixture())


def test_rapid_excludes_counterparty_only_outflows_when_disabled() -> None:
    frame = _rapid_counterparty_fixture()
    config = RapidMovementRuleConfig(include_counterparty_outflows=False)

    assert (
        run_rapid_movement_rule(
            frame,
            build_movement_dormancy_accounts_fixture(),
            config,
        )
        == ()
    )


def test_rapid_includes_internal_outflows_when_enabled() -> None:
    assert run_rapid_movement_rule(
        build_rapid_movement_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )


def test_rapid_excludes_internal_outflows_when_disabled() -> None:
    config = RapidMovementRuleConfig(include_internal_account_outflows=False)

    assert (
        run_rapid_movement_rule(
            build_rapid_movement_only_transactions_fixture(),
            build_movement_dormancy_accounts_fixture(),
            config,
        )
        == ()
    )


def test_rapid_config_rejects_disabling_both_outflow_sources() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(
            include_counterparty_outflows=False,
            include_internal_account_outflows=False,
        )


def test_dormant_includes_counterparty_outflows_when_enabled() -> None:
    frame = _dormant_counterparty_fixture()

    assert run_dormant_reactivation_rule(frame, build_movement_dormancy_accounts_fixture())


def test_dormant_excludes_counterparty_only_outflows_when_disabled() -> None:
    frame = _dormant_counterparty_fixture()
    config = DormantReactivationRuleConfig(include_counterparty_outflows=False)

    assert (
        run_dormant_reactivation_rule(
            frame,
            build_movement_dormancy_accounts_fixture(),
            config,
        )
        == ()
    )


def test_dormant_includes_internal_outflows_when_enabled() -> None:
    assert run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )


def test_dormant_excludes_internal_outflows_when_disabled() -> None:
    config = DormantReactivationRuleConfig(include_internal_account_outflows=False)

    assert (
        run_dormant_reactivation_rule(
            build_dormant_reactivation_only_transactions_fixture(),
            build_movement_dormancy_accounts_fixture(),
            config,
        )
        == ()
    )


def test_dormant_config_rejects_disabling_both_outflow_sources() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(
            include_counterparty_outflows=False,
            include_internal_account_outflows=False,
        )


def _rapid_counterparty_fixture():
    frame = build_rapid_movement_only_transactions_fixture()
    outbound_mask = frame["transaction_id"].str.contains("OUT")
    frame.loc[outbound_mask, "receiver_account_id"] = None
    frame.loc[outbound_mask, "counterparty_id"] = "CP_MD_RM_COUNTER"
    return frame


def _dormant_counterparty_fixture():
    frame = build_dormant_reactivation_only_transactions_fixture()
    react_mask = frame["transaction_id"].str.contains("REACT")
    frame.loc[react_mask, "receiver_account_id"] = None
    frame.loc[react_mask, "counterparty_id"] = "CP_MD_DR_COUNTER"
    return frame
