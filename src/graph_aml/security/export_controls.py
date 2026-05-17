"""Privacy-safe export controls."""

from __future__ import annotations

from typing import cast

import pandas as pd

from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import ExportControlError, PermissionPolicyError
from graph_aml.security.masking import mask_dataframe
from graph_aml.security.permissions import is_action_allowed, normalise_role


def _config(config: SecurityControlConfig | None) -> SecurityControlConfig:
    return config or SecurityControlConfig()


def validate_export_request(
    role: str | None,
    export_mode: str | None = None,
    row_count: int | None = None,
    config: SecurityControlConfig | None = None,
) -> None:
    """Validate export mode, row count, and role permission."""

    resolved = _config(config)
    mode = export_mode or resolved.export_controls.default_export_mode
    if mode not in {"sanitised", "sensitive"}:
        raise ExportControlError("export_mode must be sanitised or sensitive")
    if row_count is not None and row_count > resolved.export_controls.max_export_rows:
        raise ExportControlError("export row limit exceeded")
    selected_role = normalise_role(role, resolved)
    if mode == "sanitised":
        if not is_action_allowed(selected_role, "export_sanitised", resolved):
            raise PermissionPolicyError(f"{selected_role} cannot export sanitised data")
        return
    if not resolved.export_controls.allow_sensitive_exports:
        raise ExportControlError("sensitive exports are disabled")
    if (
        selected_role != resolved.export_controls.require_role_for_sensitive_export
        and selected_role != "admin"
    ):
        raise PermissionPolicyError("sensitive export requires authorised role")
    if not is_action_allowed(selected_role, "export_sensitive", resolved):
        raise PermissionPolicyError(f"{selected_role} cannot export sensitive data")


def sanitise_export_dataframe(
    frame: pd.DataFrame,
    sensitive_fields: pd.DataFrame,
    role: str | None = None,
    export_mode: str | None = None,
    config: SecurityControlConfig | None = None,
) -> pd.DataFrame:
    """Prepare a DataFrame for export, masking or blocking sensitive data."""

    if not isinstance(frame, pd.DataFrame):
        raise ExportControlError("frame must be a DataFrame")
    resolved = _config(config)
    mode = export_mode or resolved.export_controls.default_export_mode
    validate_export_request(role, mode, len(frame), resolved)
    blocked = {column.lower() for column in resolved.export_controls.blocked_columns}
    output = frame.drop(
        columns=[column for column in frame.columns if column.lower() in blocked],
        errors="ignore",
    ).copy(deep=True)
    if mode == "sensitive":
        return output
    return mask_dataframe(output, sensitive_fields, resolved)


def dataframe_to_sanitised_csv_bytes(
    frame: pd.DataFrame,
    sensitive_fields: pd.DataFrame,
    role: str | None = None,
    export_mode: str | None = None,
    config: SecurityControlConfig | None = None,
) -> bytes:
    """Return privacy-safe CSV bytes."""

    export_frame = sanitise_export_dataframe(frame, sensitive_fields, role, export_mode, config)
    return cast("bytes", export_frame.to_csv(index=False).encode("utf-8"))


def build_export_control_summary(
    frame: pd.DataFrame,
    sensitive_fields: pd.DataFrame,
    role: str | None = None,
    export_mode: str | None = None,
    config: SecurityControlConfig | None = None,
) -> dict[str, object]:
    """Summarise how an export would be controlled."""

    resolved = _config(config)
    mode = export_mode or resolved.export_controls.default_export_mode
    validate_export_request(role, mode, len(frame), resolved)
    sensitive_columns = (
        sorted(set(sensitive_fields["column_name"]).intersection(frame.columns))
        if "column_name" in sensitive_fields.columns
        else []
    )
    blocked_columns = [
        column
        for column in frame.columns
        if column.lower() in set(resolved.export_controls.blocked_columns)
    ]
    return {
        "export_mode": mode,
        "role": normalise_role(role, resolved),
        "row_count": int(len(frame)),
        "sensitive_column_count": len(sensitive_columns),
        "sensitive_columns": sensitive_columns,
        "blocked_columns": blocked_columns,
        "sanitised": mode == "sanitised",
    }
