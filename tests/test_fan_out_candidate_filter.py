"""Tests for fan-out candidate filtering."""

import pandas as pd

from graph_aml.rules import FanOutRuleConfig, filter_fan_out_candidate_transactions
from tests.fixtures.fan_out_fixtures import (
    build_fan_out_counterparty_transactions_fixture,
    build_fan_out_invalid_transactions_fixture,
    build_fan_out_trigger_transactions_fixture,
)


def test_candidate_filter_keeps_outbound_transactions_with_internal_receiver_account() -> None:
    candidates = filter_fan_out_candidate_transactions(build_fan_out_trigger_transactions_fixture())

    assert len(candidates) == 20


def test_candidate_filter_keeps_external_counterparty_when_enabled() -> None:
    candidates = filter_fan_out_candidate_transactions(
        build_fan_out_counterparty_transactions_fixture()
    )

    assert "TXN_FAN_OUT_COUNTERPARTY_001" in set(candidates["transaction_id"])


def test_candidate_filter_excludes_transactions_with_no_recipient_key() -> None:
    candidates = filter_fan_out_candidate_transactions(build_fan_out_invalid_transactions_fixture())

    assert "TXN_FAN_OUT_INVALID_RECIPIENT" not in set(candidates["transaction_id"])


def test_candidate_filter_excludes_self_transfers() -> None:
    frame = build_fan_out_trigger_transactions_fixture(unique_recipient_count=2)
    frame.loc[0, "receiver_account_id"] = "ACC_DISPERSE_001"

    candidates = filter_fan_out_candidate_transactions(frame)

    assert "TXN_FAN_OUT_TRIGGER_001" not in set(candidates["transaction_id"])


def test_candidate_filter_respects_configured_transaction_types() -> None:
    frame = build_fan_out_trigger_transactions_fixture()
    frame.loc[0, "transaction_type"] = "card"

    candidates = filter_fan_out_candidate_transactions(frame)

    assert "TXN_FAN_OUT_TRIGGER_001" not in set(candidates["transaction_id"])


def test_candidate_filter_excludes_non_positive_amounts_after_normalisation() -> None:
    frame = build_fan_out_trigger_transactions_fixture()
    frame.loc[0, "amount"] = 0

    candidates = filter_fan_out_candidate_transactions(frame)

    assert "TXN_FAN_OUT_TRIGGER_001" not in set(candidates["transaction_id"])


def test_candidate_filter_adds_canonical_account_id_equal_to_sender_account_id() -> None:
    candidates = filter_fan_out_candidate_transactions(build_fan_out_trigger_transactions_fixture())

    assert candidates["account_id"].eq(candidates["sender_account_id"]).all()


def test_candidate_filter_adds_canonical_recipient_id() -> None:
    candidates = filter_fan_out_candidate_transactions(build_fan_out_trigger_transactions_fixture())

    assert candidates["recipient_id"].eq(candidates["receiver_account_id"]).all()


def test_candidate_filter_adds_canonical_recipient_type() -> None:
    candidates = filter_fan_out_candidate_transactions(build_fan_out_trigger_transactions_fixture())

    assert set(candidates["recipient_type"]) == {"account"}


def test_candidate_filter_excludes_counterparty_only_rows_when_counterparties_disabled() -> None:
    config = FanOutRuleConfig(include_counterparties=False)

    candidates = filter_fan_out_candidate_transactions(
        build_fan_out_counterparty_transactions_fixture(),
        config,
    )

    assert "counterparty" not in set(candidates["recipient_type"])


def test_candidate_filter_excludes_internal_receiver_rows_when_internal_accounts_disabled() -> None:
    config = FanOutRuleConfig(include_internal_accounts=False)

    candidates = filter_fan_out_candidate_transactions(
        build_fan_out_counterparty_transactions_fixture(),
        config,
    )

    assert "account" not in set(candidates["recipient_type"])


def test_candidate_filter_returns_deterministic_ordering() -> None:
    frame = build_fan_out_trigger_transactions_fixture().sample(frac=1, random_state=4)

    candidates = filter_fan_out_candidate_transactions(frame)

    assert candidates["transaction_id"].tolist() == [
        f"TXN_FAN_OUT_TRIGGER_{index:03d}" for index in range(1, 21)
    ]


def test_candidate_filter_does_not_mutate_input_dataframes() -> None:
    frame = build_fan_out_trigger_transactions_fixture()
    original = frame.copy(deep=True)

    filter_fan_out_candidate_transactions(frame)

    pd.testing.assert_frame_equal(frame, original)
