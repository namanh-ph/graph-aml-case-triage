"""Sensitive field inventory builders."""

from __future__ import annotations

from typing import cast

import pandas as pd

from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import SensitiveFieldError

SENSITIVE_FIELD_COLUMNS = (
    "security_run_id",
    "schema_name",
    "table_name",
    "column_name",
    "classification",
    "matched_pattern",
    "recommended_masking_strategy",
    "metadata",
)


def _config(config: SecurityControlConfig | None) -> SecurityControlConfig:
    return config or SecurityControlConfig()


def classify_column_name(
    column_name: str,
    config: SecurityControlConfig | None = None,
) -> tuple[str, str | None]:
    """Classify a column name using configured sensitive-field patterns."""

    if not isinstance(column_name, str) or not column_name.strip():
        raise SensitiveFieldError("column_name must be a non-empty string")
    resolved = _config(config)
    lowered = column_name.strip().lower()
    for pattern in resolved.sensitive_fields.restricted_patterns:
        if pattern.lower() in lowered:
            return "restricted", pattern
    for pattern in resolved.sensitive_fields.confidential_patterns:
        if pattern.lower() in lowered:
            return "confidential", pattern
    return resolved.sensitive_fields.default_classification, None


def recommend_masking_strategy(
    column_name: str,
    classification: str,
    config: SecurityControlConfig | None = None,
) -> str:
    """Recommend a masking strategy for a classified column."""

    resolved = _config(config)
    lowered = column_name.strip().lower()
    for key, strategy in resolved.masking.strategies.items():
        if key.lower() == lowered or key.lower() in lowered:
            return strategy
    if classification == "restricted":
        return "redact"
    if classification == "confidential":
        return resolved.masking.default_strategy
    return "none"


def build_sensitive_field_inventory(
    table_columns: pd.DataFrame,
    config: SecurityControlConfig | None = None,
    security_run_id: str | None = None,
) -> pd.DataFrame:
    """Build a deterministic sensitive field inventory from table-column metadata."""

    if not isinstance(table_columns, pd.DataFrame):
        raise SensitiveFieldError("table_columns must be a DataFrame")
    required = {"schema_name", "table_name", "column_name"}
    missing = required.difference(table_columns.columns)
    if missing:
        raise SensitiveFieldError(f"table_columns missing required columns: {sorted(missing)}")
    resolved = _config(config)
    rows: list[dict[str, object]] = []
    source = table_columns.copy(deep=True)
    for row in source.sort_values(["schema_name", "table_name", "column_name"]).to_dict("records"):
        column_name = str(row["column_name"])
        classification, matched = classify_column_name(column_name, resolved)
        strategy = recommend_masking_strategy(column_name, classification, resolved)
        rows.append(
            {
                "security_run_id": security_run_id or "",
                "schema_name": str(row["schema_name"]),
                "table_name": str(row["table_name"]),
                "column_name": column_name,
                "classification": classification,
                "matched_pattern": matched,
                "recommended_masking_strategy": strategy,
                "metadata": {
                    "data_type": row.get("data_type"),
                    "default_classification": resolved.sensitive_fields.default_classification,
                },
            }
        )
    return cast("pd.DataFrame", pd.DataFrame(rows, columns=SENSITIVE_FIELD_COLUMNS))
