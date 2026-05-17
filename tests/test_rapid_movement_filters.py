"""Tests for rapid movement inbound and outbound filters."""

import pandas as pd

from graph_aml.rules import (
    RapidMovementRuleConfig,
    filter_rapid_movement_inbound_transactions,
    filter_rapid_movement_outbound_transactions,
)
from tests.fixtures.rapid_movement_fixtures import (
    build_rapid_movement_counterparty_transactions_fixture,
    build_rapid_movement_trigger_transactions_fixture,
)


def test_inbound_filter_keeps_valid_receiver_account_ids() -> None:
    output = filter_rapid_movement_inbound_transactions(
        build_rapid_movement_trigger_transactions_fixture()
    )

    assert "TXN_RM_IN_001" in output["transaction_id"].tolist()


def test_inbound_filter_respects_configured_transaction_types() -> None:
    config = RapidMovementRuleConfig(inbound_transaction_types=("cash_deposit",))

    output = filter_rapid_movement_inbound_transactions(
        build_rapid_movement_trigger_transactions_fixture(),
        config,
    )

    assert output.empty


def test_inbound_filter_adds_canonical_account_id() -> None:
    output = filter_rapid_movement_inbound_transactions(
        build_rapid_movement_trigger_transactions_fixture()
    )

    assert output.loc[0, "account_id"] == output.loc[0, "receiver_account_id"]


def test_outbound_filter_keeps_valid_sender_and_recipient() -> None:
    output = filter_rapid_movement_outbound_transactions(
        build_rapid_movement_trigger_transactions_fixture()
    )

    assert "TXN_RM_OUT_001" in output["transaction_id"].tolist()


def test_outbound_filter_respects_configured_transaction_types() -> None:
    config = RapidMovementRuleConfig(outbound_transaction_types=("cash_withdrawal",))

    output = filter_rapid_movement_outbound_transactions(
        build_rapid_movement_trigger_transactions_fixture(),
        config,
    )

    assert output.empty


def test_outbound_filter_excludes_self_transfers() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "receiver_account_id"] = "ACC_PASS_001"

    output = filter_rapid_movement_outbound_transactions(frame)

    assert "TXN_RM_OUT_001" not in output["transaction_id"].tolist()


def test_outbound_filter_excludes_counterparty_when_disabled() -> None:
    config = RapidMovementRuleConfig(include_counterparty_outflows=False)

    output = filter_rapid_movement_outbound_transactions(
        build_rapid_movement_counterparty_transactions_fixture(),
        config,
    )

    assert "TXN_RM_COUNTERPARTY_OUT" not in output["transaction_id"].tolist()


def test_outbound_filter_excludes_internal_receiver_when_disabled() -> None:
    config = RapidMovementRuleConfig(include_internal_account_outflows=False)

    output = filter_rapid_movement_outbound_transactions(
        build_rapid_movement_trigger_transactions_fixture(),
        config,
    )

    assert output.empty


def test_outbound_filter_adds_canonical_account_id() -> None:
    output = filter_rapid_movement_outbound_transactions(
        build_rapid_movement_trigger_transactions_fixture()
    )

    assert output.loc[0, "account_id"] == output.loc[0, "sender_account_id"]


def test_filters_return_deterministic_ordering() -> None:
    frame = pd.concat(
        [
            build_rapid_movement_trigger_transactions_fixture(),
            build_rapid_movement_counterparty_transactions_fixture(),
        ],
        ignore_index=True,
    ).sample(frac=1, random_state=3)

    inbound = filter_rapid_movement_inbound_transactions(frame)
    outbound = filter_rapid_movement_outbound_transactions(frame)

    for _, account_frame in inbound.groupby("account_id"):
        assert account_frame["transaction_timestamp"].is_monotonic_increasing
    for _, account_frame in outbound.groupby("account_id"):
        assert account_frame["transaction_timestamp"].is_monotonic_increasing


def test_filters_do_not_mutate_input_dataframes() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    original = frame.copy(deep=True)

    filter_rapid_movement_inbound_transactions(frame)
    filter_rapid_movement_outbound_transactions(frame)

    pd.testing.assert_frame_equal(frame, original)
