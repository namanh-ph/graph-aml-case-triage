"""Tests for dormant reactivation helper functions."""

import pytest

from graph_aml.rules import (
    RuleInputError,
    build_dormant_reactivation_reason_code,
    build_dormant_reactivation_recipient_key,
)


def test_recipient_helper_uses_receiver_account_id_when_present() -> None:
    assert (
        build_dormant_reactivation_recipient_key(
            {"receiver_account_id": "ACC_RECIPIENT_001", "counterparty_id": None}
        )
        == "ACC_RECIPIENT_001"
    )


def test_recipient_helper_uses_counterparty_id_when_receiver_missing() -> None:
    assert (
        build_dormant_reactivation_recipient_key(
            {"receiver_account_id": None, "counterparty_id": "CP_DR_001"}
        )
        == "CP_DR_001"
    )


def test_receiver_account_id_takes_precedence_over_counterparty_id() -> None:
    assert (
        build_dormant_reactivation_recipient_key(
            {"receiver_account_id": "ACC_RECIPIENT_001", "counterparty_id": "CP_DR_001"}
        )
        == "ACC_RECIPIENT_001"
    )


def test_missing_receiver_and_counterparty_returns_none() -> None:
    assert (
        build_dormant_reactivation_recipient_key(
            {"receiver_account_id": None, "counterparty_id": None}
        )
        is None
    )


def test_null_like_strings_are_treated_as_missing() -> None:
    assert (
        build_dormant_reactivation_recipient_key(
            {"receiver_account_id": "None", "counterparty_id": "null"}
        )
        is None
    )


def test_recipient_key_generation_is_deterministic() -> None:
    row = {"receiver_account_id": None, "counterparty_id": "CP_DR_001"}

    assert build_dormant_reactivation_recipient_key(
        row
    ) == build_dormant_reactivation_recipient_key(row)


def test_reason_code_includes_dormant_days_amount_and_window() -> None:
    reason = build_dormant_reactivation_reason_code(120, 10000.0, 7)

    assert reason == "120 inactive days followed by 10000.00 outbound value within 7 days"


def test_custom_reason_code_template_works() -> None:
    reason = build_dormant_reactivation_reason_code(
        121,
        12345.678,
        3,
        template="{dormant_days}|{total_outbound_amount_formatted}|{reactivation_window_days}",
    )

    assert reason == "121|12345.68|3"


def test_invalid_reason_code_inputs_raise() -> None:
    with pytest.raises(RuleInputError):
        build_dormant_reactivation_reason_code(0, 10000.0, 7)
    with pytest.raises(RuleInputError):
        build_dormant_reactivation_reason_code(120, -1, 7)
    with pytest.raises(RuleInputError):
        build_dormant_reactivation_reason_code(120, 10000.0, 0)


def test_input_rows_are_not_mutated() -> None:
    row = {"receiver_account_id": None, "counterparty_id": "CP_DR_001"}
    original = row.copy()

    build_dormant_reactivation_recipient_key(row)

    assert row == original
