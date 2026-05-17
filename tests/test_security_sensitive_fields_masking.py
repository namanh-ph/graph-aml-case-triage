"""Tests for sensitive field inventory and masking."""

import pandas as pd
import pytest

from graph_aml.security import (
    SENSITIVE_FIELD_COLUMNS,
    DataMaskingError,
    build_masking_preview,
    build_sensitive_field_inventory,
    classify_column_name,
    mask_dataframe,
    mask_value,
    recommend_masking_strategy,
)


def test_column_classification_and_recommendations() -> None:
    assert classify_column_name("customer_name")[0] == "restricted"
    assert classify_column_name("account_id")[0] == "confidential"
    assert classify_column_name("balance")[0] == "internal"
    assert recommend_masking_strategy("account_id", "confidential") == "hash"


def test_sensitive_field_inventory_columns_and_order() -> None:
    columns = pd.DataFrame(
        [
            {"schema_name": "aml", "table_name": "cases", "column_name": "case_id"},
            {"schema_name": "aml", "table_name": "cases", "column_name": "customer_name"},
        ]
    )
    result = build_sensitive_field_inventory(columns, security_run_id="run")
    assert tuple(result.columns) == SENSITIVE_FIELD_COLUMNS
    assert list(result["column_name"]) == ["case_id", "customer_name"]


def test_masking_strategies_are_deterministic() -> None:
    assert mask_value("ABC123", "hash", salt="s") == mask_value("ABC123", "hash", salt="s")
    assert mask_value("secret@example.com", "redact") == "[REDACTED]"
    assert str(mask_value("TXN123456", "preserve_last_4")).endswith("3456")
    with pytest.raises(DataMaskingError):
        mask_value("x", "bad")


def test_dataframe_masking_and_preview_do_not_mutate_inputs() -> None:
    frame = pd.DataFrame({"account_id": ["A1"], "amount": [10]})
    fields = build_sensitive_field_inventory(
        pd.DataFrame([{"schema_name": "mart", "table_name": "scores", "column_name": "account_id"}])
    )
    original = frame.copy(deep=True)
    masked = mask_dataframe(frame, fields)
    preview = build_masking_preview(frame, fields, max_rows=1)
    assert frame.equals(original)
    assert masked.loc[0, "account_id"] != "A1"
    assert len(preview) == 1
