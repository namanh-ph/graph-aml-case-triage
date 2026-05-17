"""Tests for fan-in candidate filtering."""

import pandas as pd

from graph_aml.rules import FanInRuleConfig, filter_fan_in_candidate_transactions
from tests.fixtures.fan_in_fixtures import (
    build_fan_in_invalid_transactions_fixture,
    build_fan_in_trigger_transactions_fixture,
)


def test_candidate_filter_keeps_inbound_transactions_with_valid_receiver_account() -> None:
    candidates = filter_fan_in_candidate_transactions(build_fan_in_trigger_transactions_fixture())

    assert len(candidates) == 15


def test_candidate_filter_excludes_transactions_with_missing_receiver_account() -> None:
    candidates = filter_fan_in_candidate_transactions(build_fan_in_invalid_transactions_fixture())

    assert "TXN_FAN_IN_INVALID_RECEIVER" not in set(candidates["transaction_id"])


def test_candidate_filter_excludes_self_transfers() -> None:
    frame = build_fan_in_trigger_transactions_fixture(unique_sender_count=2)
    frame.loc[0, "sender_account_id"] = "ACC_COLLECT_001"

    candidates = filter_fan_in_candidate_transactions(frame)

    assert "TXN_FAN_IN_TRIGGER_001" not in set(candidates["transaction_id"])


def test_candidate_filter_respects_configured_transaction_types() -> None:
    frame = build_fan_in_trigger_transactions_fixture()
    frame.loc[0, "transaction_type"] = "card"

    candidates = filter_fan_in_candidate_transactions(frame)

    assert "TXN_FAN_IN_TRIGGER_001" not in set(candidates["transaction_id"])


def test_candidate_filter_excludes_non_positive_amounts_after_normalisation() -> None:
    frame = build_fan_in_trigger_transactions_fixture()
    frame.loc[0, "amount"] = 0

    candidates = filter_fan_in_candidate_transactions(frame)

    assert "TXN_FAN_IN_TRIGGER_001" not in set(candidates["transaction_id"])


def test_candidate_filter_adds_canonical_account_id_equal_to_receiver_account_id() -> None:
    candidates = filter_fan_in_candidate_transactions(build_fan_in_trigger_transactions_fixture())

    assert candidates["account_id"].eq(candidates["receiver_account_id"]).all()


def test_candidate_filter_adds_canonical_sender_id_equal_to_sender_account_id() -> None:
    candidates = filter_fan_in_candidate_transactions(build_fan_in_trigger_transactions_fixture())

    assert candidates["sender_id"].eq(candidates["sender_account_id"]).all()


def test_candidate_filter_returns_deterministic_ordering() -> None:
    frame = build_fan_in_trigger_transactions_fixture().sample(frac=1, random_state=4)

    candidates = filter_fan_in_candidate_transactions(frame)

    assert candidates["transaction_id"].tolist() == [
        f"TXN_FAN_IN_TRIGGER_{index:03d}" for index in range(1, 16)
    ]


def test_candidate_filter_does_not_mutate_input_dataframes() -> None:
    frame = build_fan_in_trigger_transactions_fixture()
    original = frame.copy(deep=True)

    filter_fan_in_candidate_transactions(frame)

    pd.testing.assert_frame_equal(frame, original)


def test_candidate_filter_empty_when_internal_receipts_disabled() -> None:
    config = FanInRuleConfig(include_internal_account_receipts=False)

    candidates = filter_fan_in_candidate_transactions(
        build_fan_in_trigger_transactions_fixture(),
        config,
    )

    assert candidates.empty
