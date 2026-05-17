"""Deterministic masking utilities for privacy-safe exports."""

from __future__ import annotations

import hashlib
import os
from typing import Any, cast

import pandas as pd

from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import DataMaskingError


def _config(config: SecurityControlConfig | None) -> SecurityControlConfig:
    return config or SecurityControlConfig()


def resolve_masking_salt(config: SecurityControlConfig | None = None) -> str:
    """Resolve masking salt from environment, falling back to local-dev salt."""

    resolved = _config(config)
    return os.getenv(resolved.masking.salt_env_var) or resolved.masking.fallback_salt


def mask_value(
    value: object,
    strategy: str,
    salt: str | None = None,
    config: SecurityControlConfig | None = None,
) -> object:
    """Mask one value using a configured strategy."""

    resolved = _config(config)
    if value is None or bool(pd.isna(cast(Any, value))):
        return resolved.masking.null_token
    if strategy == "none":
        return value
    if strategy == "redact":
        return resolved.masking.redaction_token
    text = str(value)
    if strategy == "hash":
        digest = hashlib.sha256(
            f"{salt or resolve_masking_salt(resolved)}|{text}".encode()
        ).hexdigest()
        return digest
    if strategy == "preserve_last_4":
        suffix = text[-4:] if len(text) >= 4 else text
        return f"****{suffix}" if suffix else resolved.masking.redaction_token
    raise DataMaskingError(f"unsupported masking strategy: {strategy}")


def mask_dataframe(
    frame: pd.DataFrame,
    sensitive_fields: pd.DataFrame,
    config: SecurityControlConfig | None = None,
) -> pd.DataFrame:
    """Return a masked copy of a DataFrame using sensitive-field inventory rows."""

    if not isinstance(frame, pd.DataFrame) or not isinstance(sensitive_fields, pd.DataFrame):
        raise DataMaskingError("frame and sensitive_fields must be DataFrames")
    if "column_name" not in sensitive_fields.columns:
        raise DataMaskingError("sensitive_fields must include column_name")
    strategy_column = "recommended_masking_strategy"
    if strategy_column not in sensitive_fields.columns:
        raise DataMaskingError("sensitive_fields must include recommended_masking_strategy")
    resolved = _config(config)
    output = frame.copy(deep=True)
    salt = resolve_masking_salt(resolved)
    for row in sensitive_fields.to_dict("records"):
        column = str(row.get("column_name", ""))
        strategy = str(row.get(strategy_column) or resolved.masking.default_strategy)
        if column and column in output.columns:
            masked_values = [
                mask_value(value, strategy, salt=salt, config=resolved)
                for value in output[column].tolist()
            ]
            output[column] = pd.Series(masked_values, index=output.index, dtype="object")
    return output


def build_masking_preview(
    frame: pd.DataFrame,
    sensitive_fields: pd.DataFrame,
    config: SecurityControlConfig | None = None,
    max_rows: int = 10,
) -> pd.DataFrame:
    """Build a bounded masked preview frame."""

    if max_rows <= 0:
        raise DataMaskingError("max_rows must be positive")
    return cast("pd.DataFrame", mask_dataframe(frame.head(max_rows), sensitive_fields, config))
