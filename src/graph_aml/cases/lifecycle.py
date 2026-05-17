"""Case lifecycle transition and high-level action helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Engine

from graph_aml.cases.exceptions import (
    CaseLifecyclePersistenceError,
    CaseLifecycleTransitionError,
    CaseLifecycleValidationError,
)
from graph_aml.cases.lifecycle_config import CaseLifecycleConfig
from graph_aml.cases.lifecycle_models import (
    CaseLifecycleAction,
    validate_case_lifecycle_action,
)

if TYPE_CHECKING:
    from graph_aml.cases.lifecycle_persistence import CaseLifecyclePersistenceResult


def _config(config: CaseLifecycleConfig | None) -> CaseLifecycleConfig:
    return CaseLifecycleConfig() if config is None else config


def _clean_status(status: str) -> str:
    return str(status).strip()


def is_terminal_status(
    status: str,
    config: CaseLifecycleConfig | None = None,
) -> bool:
    return _clean_status(status) in set(_config(config).terminal_statuses)


def is_valid_case_status(
    status: str,
    config: CaseLifecycleConfig | None = None,
) -> bool:
    return _clean_status(status) in set(_config(config).statuses)


def is_allowed_transition(
    from_status: str,
    to_status: str,
    config: CaseLifecycleConfig | None = None,
) -> bool:
    resolved = _config(config)
    source = _clean_status(from_status)
    target = _clean_status(to_status)
    return target in resolved.allowed_transitions.get(source, ())


def validate_case_status_transition(
    from_status: str,
    to_status: str,
    config: CaseLifecycleConfig | None = None,
) -> None:
    resolved = _config(config)
    source = _clean_status(from_status)
    target = _clean_status(to_status)
    if not is_valid_case_status(source, resolved):
        raise CaseLifecycleTransitionError(f"Invalid source status: {source}")
    if not is_valid_case_status(target, resolved):
        raise CaseLifecycleTransitionError(f"Invalid target status: {target}")
    if not is_allowed_transition(source, target, resolved):
        raise CaseLifecycleTransitionError(f"Transition from {source} to {target} is not allowed")


def infer_action_type_for_status_change(to_status: str) -> str:
    mapping = {
        "Escalated": "escalate",
        "Information requested": "request_information",
        "Closed false positive": "close_false_positive",
        "Closed suspicious": "close_suspicious",
        "Archived": "archive",
    }
    return mapping.get(_clean_status(to_status), "status_change")


def build_status_change_action(
    case_id: str,
    from_status: str,
    to_status: str,
    analyst_id: str | None = None,
    decision_reason: str | None = None,
    comment: str | None = None,
    config: CaseLifecycleConfig | None = None,
) -> CaseLifecycleAction:
    resolved = _config(config)
    validate_case_status_transition(from_status, to_status, resolved)
    action = CaseLifecycleAction(
        case_id=case_id,
        action_type=infer_action_type_for_status_change(to_status),
        analyst_id=analyst_id or resolved.analyst.default_analyst_id,
        from_status=_clean_status(from_status),
        to_status=_clean_status(to_status),
        decision_reason=decision_reason,
        comment=comment,
    )
    validate_case_lifecycle_action(action, resolved)
    return action


def build_assignment_action(
    case_id: str,
    assigned_to: str,
    analyst_id: str | None = None,
    queue: str | None = None,
    comment: str | None = None,
    config: CaseLifecycleConfig | None = None,
) -> CaseLifecycleAction:
    resolved = _config(config)
    if not assigned_to.strip():
        raise CaseLifecycleValidationError("assigned_to must be non-empty")
    action = CaseLifecycleAction(
        case_id=case_id,
        action_type="assign",
        analyst_id=analyst_id or resolved.analyst.default_analyst_id,
        assigned_to=assigned_to,
        queue=queue or resolved.analyst.default_queue,
        comment=comment,
    )
    validate_case_lifecycle_action(action, resolved)
    return action


def build_comment_action(
    case_id: str,
    analyst_id: str | None = None,
    comment: str | None = None,
    config: CaseLifecycleConfig | None = None,
) -> CaseLifecycleAction:
    resolved = _config(config)
    if not (comment or "").strip():
        raise CaseLifecycleValidationError("comment must be non-empty")
    action = CaseLifecycleAction(
        case_id=case_id,
        action_type="comment",
        analyst_id=analyst_id or resolved.analyst.default_analyst_id,
        comment=comment,
    )
    validate_case_lifecycle_action(action, resolved)
    return action


def change_case_status(
    engine: Engine,
    case_id: str,
    to_status: str,
    analyst_id: str | None = None,
    decision_reason: str | None = None,
    comment: str | None = None,
    config: CaseLifecycleConfig | None = None,
) -> CaseLifecyclePersistenceResult:
    try:
        from graph_aml.cases.lifecycle_persistence import apply_case_lifecycle_action
        from graph_aml.cases.lifecycle_readers import read_case_current_status

        resolved = _config(config)
        current_status = read_case_current_status(engine, case_id)
        if current_status is None:
            raise CaseLifecycleTransitionError(f"Case {case_id} was not found")
        action = build_status_change_action(
            case_id,
            current_status,
            to_status,
            analyst_id=analyst_id,
            decision_reason=decision_reason,
            comment=comment,
            config=resolved,
        )
        return apply_case_lifecycle_action(engine, action, resolved)
    except (CaseLifecyclePersistenceError, CaseLifecycleTransitionError):
        raise
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to change case status: {exc}") from exc


def assign_case(
    engine: Engine,
    case_id: str,
    assigned_to: str,
    analyst_id: str | None = None,
    queue: str | None = None,
    comment: str | None = None,
    config: CaseLifecycleConfig | None = None,
) -> CaseLifecyclePersistenceResult:
    try:
        from graph_aml.cases.lifecycle_persistence import apply_case_lifecycle_action

        resolved = _config(config)
        action = build_assignment_action(
            case_id,
            assigned_to,
            analyst_id=analyst_id,
            queue=queue,
            comment=comment,
            config=resolved,
        )
        return apply_case_lifecycle_action(engine, action, resolved)
    except (CaseLifecyclePersistenceError, CaseLifecycleValidationError):
        raise
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to assign case: {exc}") from exc


def add_case_comment(
    engine: Engine,
    case_id: str,
    analyst_id: str | None = None,
    comment: str | None = None,
    config: CaseLifecycleConfig | None = None,
) -> CaseLifecyclePersistenceResult:
    try:
        from graph_aml.cases.lifecycle_persistence import apply_case_lifecycle_action

        resolved = _config(config)
        action = build_comment_action(
            case_id,
            analyst_id=analyst_id,
            comment=comment,
            config=resolved,
        )
        return apply_case_lifecycle_action(engine, action, resolved)
    except (CaseLifecyclePersistenceError, CaseLifecycleValidationError):
        raise
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to add case comment: {exc}") from exc
