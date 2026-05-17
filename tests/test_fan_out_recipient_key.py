"""Tests for fan-out recipient key generation."""

from graph_aml.rules import build_fan_out_recipient_key


def test_receiver_account_id_is_used_when_present() -> None:
    assert build_fan_out_recipient_key({"receiver_account_id": "ACC_2"}) == "ACC_2"


def test_counterparty_id_is_used_when_receiver_is_missing() -> None:
    assert (
        build_fan_out_recipient_key({"receiver_account_id": None, "counterparty_id": "CP_1"})
        == "CP_1"
    )


def test_receiver_account_id_takes_precedence_over_counterparty_id() -> None:
    assert (
        build_fan_out_recipient_key({"receiver_account_id": "ACC_2", "counterparty_id": "CP_1"})
        == "ACC_2"
    )


def test_missing_receiver_and_counterparty_returns_none() -> None:
    assert build_fan_out_recipient_key({}) is None


def test_null_like_strings_are_treated_as_missing() -> None:
    assert (
        build_fan_out_recipient_key({"receiver_account_id": "nan", "counterparty_id": "None"})
        is None
    )
    assert (
        build_fan_out_recipient_key({"receiver_account_id": "null", "counterparty_id": "CP_1"})
        == "CP_1"
    )


def test_recipient_key_generation_is_deterministic() -> None:
    row = {"receiver_account_id": " ACC_2 ", "counterparty_id": "CP_1"}

    assert build_fan_out_recipient_key(row) == build_fan_out_recipient_key(row)


def test_input_rows_are_not_mutated() -> None:
    row = {"receiver_account_id": " ACC_2 ", "counterparty_id": "CP_1"}
    original = row.copy()

    build_fan_out_recipient_key(row)

    assert row == original
