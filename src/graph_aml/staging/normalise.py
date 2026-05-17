"""Deterministic field normalisation helpers for staging transformations."""

from __future__ import annotations

import re
from typing import Any, cast

import pandas as pd

NULL_STRINGS = {"", "nan", "none", "null", "<na>", "nat"}
TRUE_STRINGS = {"true", "1", "yes", "y", "t"}
FALSE_STRINGS = {"false", "0", "no", "n", "f"}


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(cast(Any, value))
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, bool) else False


def normalise_string(value: object) -> str | None:
    """Return a stripped string or None for null-like values."""

    if _is_missing(value):
        return None
    text = str(value).strip()
    if text.lower() in NULL_STRINGS:
        return None
    return text


def normalise_identifier(value: object, prefix: str | None = None) -> str | None:
    """Return a deterministic uppercase identifier."""

    text = normalise_string(value)
    if text is None:
        return None
    identifier = re.sub(r"\s+", "_", text).upper()
    if prefix is None:
        return identifier
    normalised_prefix = prefix.strip().upper().rstrip("_")
    if identifier.startswith(f"{normalised_prefix}_"):
        return identifier
    return f"{normalised_prefix}_{identifier}"


def normalise_country_code(value: object) -> str | None:
    """Return an uppercase country code."""

    text = normalise_string(value)
    return None if text is None else text.upper()


def normalise_currency(value: object, default: str = "USD") -> str:
    """Return an uppercase currency code."""

    text = normalise_string(value)
    return default.upper() if text is None else text.upper()


def normalise_boolean(value: object, default: bool = False) -> bool:
    """Parse a boolean-like value deterministically."""

    if _is_missing(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float) and not isinstance(value, bool):
        return bool(value)
    text = normalise_string(value)
    if text is None:
        return default
    lowered = text.lower()
    if lowered in TRUE_STRINGS:
        return True
    if lowered in FALSE_STRINGS:
        return False
    return default


def normalise_numeric(value: object, default: float | None = None) -> float | None:
    """Parse a numeric value as float."""

    if _is_missing(value):
        return default
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if _is_missing(parsed):
        return default
    return float(parsed)


def parse_timestamp(value: object) -> pd.Timestamp | None:
    """Parse a timestamp-like value to a UTC pandas Timestamp."""

    if _is_missing(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if _is_missing(parsed):
        return None
    return cast(pd.Timestamp, parsed)


def normalise_datetime_series(series: pd.Series) -> pd.Series:
    """Parse a Series into UTC timestamps, preserving nulls."""

    return series.apply(parse_timestamp)


def ensure_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    """Return a copy with the requested columns present."""

    output = frame.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output
