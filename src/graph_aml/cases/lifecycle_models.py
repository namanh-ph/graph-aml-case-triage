"""Data models for AML case lifecycle actions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from graph_aml.cases.exceptions import CaseLifecycleValidationError
from graph_aml.cases.lifecycle_config import CaseLifecycleConfig


@dataclass(frozen=True)
class CaseLifecycleAction:
    case_id: str
    action_type: str
    analyst_id: str
    from_status: str | None = None
    to_status: str | None = None
    assigned_to: str | None = None
    queue: str | None = None
    decision_reason: str | None = None
    comment: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    action_timestamp: datetime | None = None


@dataclass(frozen=True)
class CaseLifecycleActionResult:
    case_id: str
    action_type: str
    from_status: str | None
    to_status: str | None
    current_status: str | None
    analyst_id: str
    action_id: str
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return cast(Any, value).item()
        except (AttributeError, ValueError):
            return str(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def build_case_action_id(action: CaseLifecycleAction) -> str:
    payload = {
        "case_id": action.case_id,
        "action_type": action.action_type,
        "analyst_id": action.analyst_id,
        "from_status": action.from_status,
        "to_status": action.to_status,
        "assigned_to": action.assigned_to,
        "queue": action.queue,
        "decision_reason": action.decision_reason,
        "comment": action.comment,
        "metadata": _json_safe(action.metadata),
        "action_timestamp": action.action_timestamp.isoformat()
        if action.action_timestamp
        else None,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return f"CASE_ACTION_{digest.upper()}"


def lifecycle_action_to_record(
    action: CaseLifecycleAction,
    action_id: str | None = None,
) -> dict[str, object]:
    timestamp = action.action_timestamp or datetime.now(UTC)
    action_with_timestamp = CaseLifecycleAction(
        **{**action.__dict__, "action_timestamp": timestamp}
    )
    resolved_id = action_id or build_case_action_id(action_with_timestamp)
    return {
        "action_id": resolved_id,
        "case_id": action.case_id,
        "action_type": action.action_type,
        "analyst_id": action.analyst_id,
        "from_status": action.from_status,
        "to_status": action.to_status,
        "assigned_to": action.assigned_to,
        "queue": action.queue,
        "decision_reason": action.decision_reason,
        "comment": action.comment,
        "metadata": _json_safe(action.metadata),
        "action_timestamp": timestamp,
    }


def validate_case_lifecycle_action(
    action: CaseLifecycleAction,
    config: CaseLifecycleConfig | None = None,
) -> None:
    resolved = CaseLifecycleConfig() if config is None else config
    if not isinstance(action, CaseLifecycleAction):
        raise CaseLifecycleValidationError("action must be CaseLifecycleAction")
    if not action.case_id.strip():
        raise CaseLifecycleValidationError("case_id must be non-empty")
    if not action.analyst_id.strip():
        raise CaseLifecycleValidationError("analyst_id must be non-empty")
    if action.action_type not in resolved.decision_types:
        raise CaseLifecycleValidationError("action_type is not configured")
    valid_statuses = set(resolved.statuses)
    if action.from_status is not None and action.from_status.strip() not in valid_statuses:
        raise CaseLifecycleValidationError("from_status is invalid")
    if action.to_status is not None and action.to_status.strip() not in valid_statuses:
        raise CaseLifecycleValidationError("to_status is invalid")
    closure_action = action.action_type in {"close_false_positive", "close_suspicious"} or (
        action.to_status in {"Closed false positive", "Closed suspicious"}
    )
    if closure_action and resolved.analyst.require_decision_reason:
        if not (action.decision_reason or "").strip():
            raise CaseLifecycleValidationError("closure actions require a decision reason")
    if closure_action and resolved.analyst.require_comment_for_closure:
        if not (action.comment or "").strip():
            raise CaseLifecycleValidationError("closure actions require a comment")
