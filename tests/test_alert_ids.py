"""Tests for deterministic alert ID helpers."""

from __future__ import annotations

import pytest

from graph_aml.alerts import (
    AlertValidationError,
    build_alert_id,
    build_sequential_alert_id,
    normalise_rule_name_for_id,
)


def test_normalise_rule_name_for_id_returns_uppercase_identifier() -> None:
    assert normalise_rule_name_for_id("Structuring") == "STRUCTURING"


def test_build_alert_id_is_deterministic_for_same_inputs() -> None:
    first = build_alert_id("Structuring", "ACC_001", "2025-01-01", ["T2", "T1"])
    second = build_alert_id("Structuring", "ACC_001", "2025-01-01", ["T2", "T1"])

    assert first == second


def test_build_alert_id_changes_when_evidence_changes() -> None:
    first = build_alert_id("Structuring", "ACC_001", "2025-01-01", ["T1"])
    second = build_alert_id("Structuring", "ACC_001", "2025-01-01", ["T2"])

    assert first != second


def test_build_alert_id_is_independent_of_evidence_order() -> None:
    first = build_alert_id("Structuring", "ACC_001", "2025-01-01", ["T1", "T2"])
    second = build_alert_id("Structuring", "ACC_001", "2025-01-01", ["T2", "T1"])

    assert first == second


def test_generated_alert_ids_start_with_al_prefix() -> None:
    assert build_alert_id("Structuring", "ACC_001", None, ["T1"]).startswith("AL_")


def test_build_sequential_alert_id_returns_padded_id() -> None:
    assert build_sequential_alert_id("AL", 42) == "AL000042"


def test_invalid_sequence_values_raise_alert_validation_error() -> None:
    with pytest.raises(AlertValidationError):
        build_sequential_alert_id("AL", -1)


def test_empty_rule_names_or_account_ids_raise_alert_validation_error() -> None:
    with pytest.raises(AlertValidationError):
        build_alert_id("", "ACC_001", None, ["T1"])
    with pytest.raises(AlertValidationError):
        build_alert_id("Structuring", "", None, ["T1"])
