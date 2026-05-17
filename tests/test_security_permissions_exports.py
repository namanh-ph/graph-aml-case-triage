"""Tests for permission and export controls."""

import pandas as pd
import pytest

from graph_aml.security import (
    ExportControlError,
    PermissionPolicyError,
    build_sensitive_field_inventory,
    is_action_allowed,
    normalise_role,
    sanitise_export_dataframe,
    validate_export_request,
)


def _fields() -> pd.DataFrame:
    return build_sensitive_field_inventory(
        pd.DataFrame(
            [{"schema_name": "aml", "table_name": "cases", "column_name": "customer_name"}]
        )
    )


def test_role_permissions() -> None:
    assert normalise_role(None) == "analyst"
    assert is_action_allowed("viewer", "read_dashboard")
    assert not is_action_allowed("viewer", "case_close")
    assert is_action_allowed("senior_analyst", "case_close")
    assert is_action_allowed("admin", "read_governance_inventory")
    with pytest.raises(PermissionPolicyError):
        is_action_allowed("unknown", "read_dashboard")


def test_sanitised_export_masks_and_drops_columns() -> None:
    frame = pd.DataFrame({"customer_name": ["Jane"], "raw_payload": ["secret"], "amount": [1]})
    result = sanitise_export_dataframe(frame, _fields(), role="viewer")
    assert result.loc[0, "customer_name"] == "[REDACTED]"
    assert "raw_payload" not in result.columns
    assert "raw_payload" in frame.columns


def test_sensitive_export_and_row_limits_are_blocked() -> None:
    with pytest.raises(ExportControlError):
        validate_export_request("senior_analyst", "sensitive", 1)
    with pytest.raises(ExportControlError):
        validate_export_request("viewer", "sanitised", 10001)
