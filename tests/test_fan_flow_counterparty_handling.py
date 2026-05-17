"""Counterparty handling tests for fan-flow rules."""

import pytest

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    RuleConfigurationError,
    filter_fan_in_candidate_transactions,
    filter_fan_out_candidate_transactions,
    run_fan_out_rule,
)
from tests.fixtures.fan_flow_fixtures import (
    build_fan_flow_accounts_fixture,
    build_fan_flow_counterparty_mixed_transactions_fixture,
)


def test_fan_out_includes_counterparty_recipients_when_enabled() -> None:
    candidates = filter_fan_out_candidate_transactions(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=4, include_counterparties=True),
    )

    assert "counterparty" in set(candidates["recipient_type"])


def test_fan_out_excludes_counterparty_only_recipients_when_disabled() -> None:
    candidates = filter_fan_out_candidate_transactions(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=2, include_counterparties=False),
    )

    assert "counterparty" not in set(candidates["recipient_type"])


def test_fan_out_includes_internal_receiver_accounts_when_enabled() -> None:
    candidates = filter_fan_out_candidate_transactions(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=4, include_internal_accounts=True),
    )

    assert "account" in set(candidates["recipient_type"])


def test_fan_out_excludes_internal_receiver_accounts_when_disabled() -> None:
    candidates = filter_fan_out_candidate_transactions(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=2, include_internal_accounts=False),
    )

    assert "account" not in set(candidates["recipient_type"])


def test_fan_out_config_rejects_disabling_both_recipient_sources() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(include_counterparties=False, include_internal_accounts=False)


def test_fan_in_excludes_rows_without_valid_internal_receiver_accounts() -> None:
    candidates = filter_fan_in_candidate_transactions(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        FanInRuleConfig(min_unique_senders=2),
    )

    assert "TXN_FLOW_MIXED_NO_RECEIVER" not in set(candidates["transaction_id"])


def test_fan_in_returns_empty_candidates_when_internal_receipts_disabled() -> None:
    candidates = filter_fan_in_candidate_transactions(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        FanInRuleConfig(min_unique_senders=2, include_internal_account_receipts=False),
    )

    assert candidates.empty


def test_mixed_internal_and_counterparty_fan_out_can_trigger_when_both_enabled() -> None:
    alerts = run_fan_out_rule(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )

    assert len(alerts) == 1


def test_recipient_ids_are_deterministic_across_internal_and_counterparty_types() -> None:
    first = filter_fan_out_candidate_transactions(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )
    second = filter_fan_out_candidate_transactions(
        build_fan_flow_counterparty_mixed_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )

    assert first["recipient_id"].tolist() == second["recipient_id"].tolist()
