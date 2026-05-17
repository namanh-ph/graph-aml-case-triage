"""Role and permission policy helpers."""

from __future__ import annotations

from typing import cast

import pandas as pd

from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import PermissionPolicyError

PERMISSION_CHECK_COLUMNS = (
    "security_run_id",
    "role",
    "action",
    "allowed",
    "reason",
    "metadata",
)


def _config(config: SecurityControlConfig | None) -> SecurityControlConfig:
    return config or SecurityControlConfig()


def normalise_role(role: str | None, config: SecurityControlConfig | None = None) -> str:
    resolved = _config(config)
    selected = (role or resolved.permissions.default_role).strip()
    if selected not in resolved.permissions.roles:
        raise PermissionPolicyError(f"unknown role: {selected}")
    return selected


def list_allowed_actions(
    role: str | None,
    config: SecurityControlConfig | None = None,
) -> tuple[str, ...]:
    resolved = _config(config)
    return tuple(resolved.permissions.roles[normalise_role(role, resolved)])


def is_action_allowed(
    role: str | None,
    action: str,
    config: SecurityControlConfig | None = None,
) -> bool:
    if not action or not isinstance(action, str):
        raise PermissionPolicyError("action must be a non-empty string")
    actions = list_allowed_actions(role, config)
    return "*" in actions or action in actions


def require_action_allowed(
    role: str | None,
    action: str,
    config: SecurityControlConfig | None = None,
) -> None:
    resolved = _config(config)
    selected = normalise_role(role, resolved)
    if not is_action_allowed(selected, action, resolved):
        protected = action in resolved.permissions.protected_actions
        reason = (
            "protected action requires explicit permission"
            if protected
            else "action is not allowed"
        )
        raise PermissionPolicyError(f"{selected} cannot perform {action}: {reason}")


def build_permission_matrix(
    config: SecurityControlConfig | None = None,
    security_run_id: str | None = None,
) -> pd.DataFrame:
    """Build a deterministic permission matrix for configured roles and actions."""

    resolved = _config(config)
    all_actions = sorted(
        set(resolved.permissions.protected_actions).union(
            *[set(actions) for actions in resolved.permissions.roles.values()]
        )
        - {"*"}
    )
    rows: list[dict[str, object]] = []
    for role in sorted(resolved.permissions.roles):
        actions = set(resolved.permissions.roles[role])
        wildcard = "*" in actions
        for action in all_actions:
            allowed = wildcard or action in actions
            rows.append(
                {
                    "security_run_id": security_run_id or "",
                    "role": role,
                    "action": action,
                    "allowed": bool(allowed),
                    "reason": "wildcard"
                    if wildcard
                    else ("configured" if allowed else "not_configured"),
                    "metadata": {"protected": action in resolved.permissions.protected_actions},
                }
            )
    return cast("pd.DataFrame", pd.DataFrame(rows, columns=PERMISSION_CHECK_COLUMNS))
