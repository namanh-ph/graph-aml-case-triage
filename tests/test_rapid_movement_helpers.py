"""Tests for rapid movement helper functions."""

import pandas as pd
import pytest

from graph_aml.rules import (
    RuleInputError,
    build_rapid_movement_outflow_recipient_key,
    build_rapid_movement_reason_code,
)


def test_outflow_recipient_helper_uses_receiver_account_id_when_present() -> None:
    row = {"receiver_account_id": "ACC_RECIPIENT_001", "counterparty_id": "CP_001"}

    assert build_rapid_movement_outflow_recipient_key(row) == "ACC_RECIPIENT_001"


def test_outflow_recipient_helper_uses_counterparty_when_receiver_missing() -> None:
    row = {"receiver_account_id": None, "counterparty_id": "CP_001"}

    assert build_rapid_movement_outflow_recipient_key(row) == "CP_001"


def test_receiver_account_takes_precedence_over_counterparty() -> None:
    row = pd.Series({"receiver_account_id": "ACC_RECIPIENT_001", "counterparty_id": "CP_001"})

    assert build_rapid_movement_outflow_recipient_key(row) == "ACC_RECIPIENT_001"


def test_missing_receiver_and_counterparty_returns_none() -> None:
    row = {"receiver_account_id": None, "counterparty_id": None}

    assert build_rapid_movement_outflow_recipient_key(row) is None


def test_null_like_strings_are_treated_as_missing() -> None:
    for value in ("", "nan", "None", "null"):
        assert (
            build_rapid_movement_outflow_recipient_key(
                {"receiver_account_id": value, "counterparty_id": value}
            )
            is None
        )


def test_recipient_key_generation_is_deterministic() -> None:
    row = {"receiver_account_id": None, "counterparty_id": "cp_001"}

    assert build_rapid_movement_outflow_recipient_key(row) == "cp_001"
    assert build_rapid_movement_outflow_recipient_key(row) == "cp_001"


def test_reason_code_includes_percentage_and_window_hours() -> None:
    assert (
        build_rapid_movement_reason_code(0.9, 48)
        == "90 percent of received value sent out within 48 hours"
    )


def test_custom_reason_code_template_works() -> None:
    reason = build_rapid_movement_reason_code(
        0.925,
        24,
        template="{outflow_percentage}% out in {window_hours}h",
    )

    assert reason == "92% out in 24h"


def test_invalid_reason_code_inputs_raise_rule_input_error() -> None:
    with pytest.raises(RuleInputError):
        build_rapid_movement_reason_code(0, 48)
    with pytest.raises(RuleInputError):
        build_rapid_movement_reason_code(0.9, 0)


def test_input_rows_are_not_mutated() -> None:
    row = {"receiver_account_id": None, "counterparty_id": "CP_001"}
    original = row.copy()

    build_rapid_movement_outflow_recipient_key(row)

    assert row == original
