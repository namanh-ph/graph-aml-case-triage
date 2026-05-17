"""Tests for case lifecycle action models."""

from datetime import UTC, datetime

import pytest

from graph_aml.cases import (
    CaseLifecycleAction,
    CaseLifecycleValidationError,
    build_case_action_id,
    lifecycle_action_to_record,
    validate_case_lifecycle_action,
)


def action(**overrides) -> CaseLifecycleAction:
    payload = {
        "case_id": "CASE1",
        "action_type": "status_change",
        "analyst_id": "analyst",
        "from_status": "New",
        "to_status": "In review",
        "action_timestamp": datetime(2026, 1, 1, tzinfo=UTC),
    }
    payload.update(overrides)
    return CaseLifecycleAction(**payload)


def test_action_stores_required_fields() -> None:
    lifecycle_action = action()
    assert lifecycle_action.case_id == "CASE1"
    assert lifecycle_action.analyst_id == "analyst"


def test_action_id_is_deterministic_and_changes_with_content() -> None:
    assert build_case_action_id(action()) == build_case_action_id(action())
    assert build_case_action_id(action()) != build_case_action_id(action(comment="changed"))


def test_action_converts_to_record() -> None:
    record = lifecycle_action_to_record(action())
    assert record["action_id"].startswith("CASE_ACTION_")
    assert record["case_id"] == "CASE1"
    assert record["action_timestamp"] is not None


def test_invalid_actions_raise() -> None:
    with pytest.raises(CaseLifecycleValidationError):
        validate_case_lifecycle_action(action(case_id=""))
    with pytest.raises(CaseLifecycleValidationError):
        validate_case_lifecycle_action(action(analyst_id=""))
    with pytest.raises(CaseLifecycleValidationError):
        validate_case_lifecycle_action(action(action_type="bad"))
    with pytest.raises(CaseLifecycleValidationError):
        validate_case_lifecycle_action(action(from_status="bad"))


def test_closure_requires_reason_and_comment() -> None:
    with pytest.raises(CaseLifecycleValidationError):
        validate_case_lifecycle_action(
            action(action_type="close_suspicious", to_status="Closed suspicious")
        )
    with pytest.raises(CaseLifecycleValidationError):
        validate_case_lifecycle_action(
            action(
                action_type="close_suspicious",
                to_status="Closed suspicious",
                decision_reason="Suspicious",
            )
        )
