"""Tests for case lifecycle transitions and action builders."""

import pytest

from graph_aml.cases import (
    CaseLifecycleTransitionError,
    CaseLifecycleValidationError,
    build_assignment_action,
    build_comment_action,
    build_status_change_action,
    infer_action_type_for_status_change,
    is_allowed_transition,
    is_terminal_status,
    is_valid_case_status,
    validate_case_status_transition,
)


def test_status_helpers() -> None:
    assert is_valid_case_status("New")
    assert is_terminal_status("Closed suspicious")
    assert is_allowed_transition("New", "In review")


def test_invalid_or_disallowed_transitions_raise() -> None:
    validate_case_status_transition("New", "In review")
    with pytest.raises(CaseLifecycleTransitionError):
        validate_case_status_transition("Archived", "In review")
    with pytest.raises(CaseLifecycleTransitionError):
        validate_case_status_transition("Bad", "In review")
    with pytest.raises(CaseLifecycleTransitionError):
        validate_case_status_transition("New", "Bad")


def test_action_type_inference() -> None:
    assert infer_action_type_for_status_change("Escalated") == "escalate"
    assert infer_action_type_for_status_change("Closed suspicious") == "close_suspicious"
    assert infer_action_type_for_status_change("In review") == "status_change"


def test_action_builders_validate_inputs() -> None:
    status = build_status_change_action("CASE1", "New", "In review", decision_reason="Start review")
    assert status.action_type == "status_change"
    assignment = build_assignment_action("CASE1", "analyst_1")
    assert assignment.assigned_to == "analyst_1"
    comment = build_comment_action("CASE1", comment="Reviewed")
    assert comment.action_type == "comment"
    with pytest.raises(CaseLifecycleValidationError):
        build_assignment_action("CASE1", "")
    with pytest.raises(CaseLifecycleValidationError):
        build_comment_action("CASE1", comment="")
