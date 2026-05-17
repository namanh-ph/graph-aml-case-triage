"""Dashboard adapters for case lifecycle mutations."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, cast

from sqlalchemy import Engine

from graph_aml.cases import add_case_comment, assign_case, change_case_status
from graph_aml.dashboard.exceptions import DashboardActionError
from graph_aml.security import (
    PermissionPolicyError,
    SecurityControlConfig,
    load_security_control_config,
    require_action_allowed,
)


def _as_payload(result: object) -> dict[str, object]:
    if is_dataclass(result) and not isinstance(result, type):
        payload = asdict(result)
    else:
        payload = dict(cast(Any, result))
    return {str(key): value for key, value in payload.items()}


def require_dashboard_action_allowed(
    role: str | None,
    action: str,
    security_config: SecurityControlConfig | None = None,
) -> None:
    """Authorize dashboard actions using the configured role policy."""

    try:
        require_action_allowed(role, action, security_config or load_security_control_config())
    except PermissionPolicyError as exc:
        raise DashboardActionError(f"Dashboard action is not authorised: {exc}") from exc


def submit_dashboard_status_change(
    engine: Engine,
    case_id: str,
    to_status: str,
    analyst_id: str,
    decision_reason: str | None = None,
    comment: str | None = None,
    role: str | None = None,
    security_config: SecurityControlConfig | None = None,
) -> dict[str, object]:
    try:
        require_dashboard_action_allowed(role, "case_status_change", security_config)
        return _as_payload(
            change_case_status(
                engine,
                case_id,
                to_status,
                analyst_id=analyst_id,
                decision_reason=decision_reason,
                comment=comment,
            )
        )
    except Exception as exc:
        raise DashboardActionError(f"Failed to submit status change: {exc}") from exc


def submit_dashboard_assignment(
    engine: Engine,
    case_id: str,
    assigned_to: str,
    analyst_id: str,
    queue: str | None = None,
    comment: str | None = None,
    role: str | None = None,
    security_config: SecurityControlConfig | None = None,
) -> dict[str, object]:
    try:
        require_dashboard_action_allowed(role, "case_assign", security_config)
        return _as_payload(
            assign_case(
                engine,
                case_id,
                assigned_to,
                analyst_id=analyst_id,
                queue=queue,
                comment=comment,
            )
        )
    except Exception as exc:
        raise DashboardActionError(f"Failed to submit assignment: {exc}") from exc


def submit_dashboard_comment(
    engine: Engine,
    case_id: str,
    analyst_id: str,
    comment: str,
    role: str | None = None,
    security_config: SecurityControlConfig | None = None,
) -> dict[str, object]:
    try:
        require_dashboard_action_allowed(role, "case_comment", security_config)
        return _as_payload(
            add_case_comment(engine, case_id, analyst_id=analyst_id, comment=comment)
        )
    except Exception as exc:
        raise DashboardActionError(f"Failed to submit comment: {exc}") from exc
