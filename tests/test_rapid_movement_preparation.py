"""Tests for rapid movement transaction preparation."""

import pandas as pd

from graph_aml.rules import prepare_rapid_movement_transactions
from tests.fixtures.rapid_movement_fixtures import (
    build_rapid_movement_invalid_transactions_fixture,
    build_rapid_movement_trigger_transactions_fixture,
)


def test_preparation_parses_timestamps() -> None:
    output = prepare_rapid_movement_transactions(
        build_rapid_movement_trigger_transactions_fixture()
    )

    assert pd.api.types.is_datetime64_any_dtype(output["transaction_timestamp"])


def test_preparation_coerces_amounts() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame["amount"] = frame["amount"].astype(str)

    output = prepare_rapid_movement_transactions(frame)

    assert output["amount"].tolist() == [10000.0, 9000.0]


def test_preparation_lowercases_transaction_types() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame["transaction_type"] = ["TRANSFER", "WIRE"]

    output = prepare_rapid_movement_transactions(frame)

    assert output["transaction_type"].tolist() == ["transfer", "wire"]


def test_preparation_adds_inbound_account_id() -> None:
    output = prepare_rapid_movement_transactions(
        build_rapid_movement_trigger_transactions_fixture()
    )

    assert output.loc[0, "inbound_account_id"] == "ACC_PASS_001"


def test_preparation_adds_outbound_account_id() -> None:
    output = prepare_rapid_movement_transactions(
        build_rapid_movement_trigger_transactions_fixture()
    )

    assert output.loc[1, "outbound_account_id"] == "ACC_PASS_001"


def test_preparation_adds_outflow_recipient_id() -> None:
    output = prepare_rapid_movement_transactions(
        build_rapid_movement_trigger_transactions_fixture()
    )

    assert output.loc[1, "outflow_recipient_id"] == "ACC_RECIPIENT_001"


def test_preparation_drops_missing_transaction_ids() -> None:
    output = prepare_rapid_movement_transactions(
        build_rapid_movement_invalid_transactions_fixture()
    )

    assert output["transaction_id"].notna().all()


def test_preparation_drops_non_positive_amounts() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "amount"] = 0

    output = prepare_rapid_movement_transactions(frame)

    assert len(output) == 1


def test_preparation_returns_deterministic_ordering() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture().iloc[::-1].reset_index(drop=True)

    output = prepare_rapid_movement_transactions(frame)

    assert output["transaction_id"].tolist() == ["TXN_RM_IN_001", "TXN_RM_OUT_001"]


def test_preparation_does_not_mutate_input_dataframe() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    original = frame.copy(deep=True)

    prepare_rapid_movement_transactions(frame)

    pd.testing.assert_frame_equal(frame, original)
