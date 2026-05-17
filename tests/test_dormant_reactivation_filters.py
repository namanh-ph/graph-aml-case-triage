"""Tests for dormant reactivation activity history and candidate filters."""

import pandas as pd

from graph_aml.rules import (
    DormantReactivationRuleConfig,
    build_account_activity_history,
    filter_dormant_reactivation_outbound_candidates,
)
from tests.fixtures.dormant_reactivation_fixtures import (
    build_dormant_reactivation_counterparty_transactions_fixture,
    build_dormant_reactivation_trigger_transactions_fixture,
)


def test_activity_history_includes_outbound_sender_activity() -> None:
    history = build_account_activity_history(
        build_dormant_reactivation_trigger_transactions_fixture()
    )

    assert set(history.loc[history["activity_direction"].eq("outbound"), "account_id"]) == {
        "ACC_SOURCE_001",
        "ACC_DORMANT_001",
    }


def test_activity_history_includes_inbound_receiver_activity() -> None:
    history = build_account_activity_history(
        build_dormant_reactivation_trigger_transactions_fixture()
    )

    assert (
        "ACC_DORMANT_001"
        in history.loc[
            history["activity_direction"].eq("inbound"),
            "account_id",
        ].tolist()
    )


def test_activity_history_uses_deterministic_ordering() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture().iloc[::-1]

    history = build_account_activity_history(frame)

    assert history["account_id"].tolist() == sorted(history["account_id"].tolist())


def test_outbound_candidate_filter_keeps_high_value_outbound_transactions() -> None:
    output = filter_dormant_reactivation_outbound_candidates(
        build_dormant_reactivation_trigger_transactions_fixture()
    )

    assert output["transaction_id"].tolist() == ["TXN_DR_REACT_001"]


def test_outbound_candidate_filter_respects_configured_outbound_types() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture()
    frame.loc[1, "transaction_type"] = "card"

    output = filter_dormant_reactivation_outbound_candidates(frame)

    assert output.empty


def test_outbound_candidate_filter_excludes_self_transfers() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture()
    frame.loc[1, "receiver_account_id"] = "ACC_DORMANT_001"

    output = filter_dormant_reactivation_outbound_candidates(frame)

    assert output.empty


def test_outbound_candidate_filter_excludes_counterparty_outflows_when_disabled() -> None:
    config = DormantReactivationRuleConfig(include_counterparty_outflows=False)

    output = filter_dormant_reactivation_outbound_candidates(
        build_dormant_reactivation_counterparty_transactions_fixture(),
        config,
    )

    assert output.empty


def test_outbound_candidate_filter_excludes_internal_outflows_when_disabled() -> None:
    config = DormantReactivationRuleConfig(include_internal_account_outflows=False)

    output = filter_dormant_reactivation_outbound_candidates(
        build_dormant_reactivation_trigger_transactions_fixture(),
        config,
    )

    assert output.empty


def test_outbound_candidate_filter_adds_canonical_account_id() -> None:
    output = filter_dormant_reactivation_outbound_candidates(
        build_dormant_reactivation_trigger_transactions_fixture()
    )

    assert output.loc[0, "account_id"] == "ACC_DORMANT_001"


def test_filters_do_not_mutate_input_dataframes() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture()
    original = frame.copy(deep=True)

    build_account_activity_history(frame)
    filter_dormant_reactivation_outbound_candidates(frame)

    pd.testing.assert_frame_equal(frame, original)
