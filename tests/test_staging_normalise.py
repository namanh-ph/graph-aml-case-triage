"""Tests for staging normalisation helpers."""

import pandas as pd

from graph_aml.staging import (
    ensure_columns,
    normalise_boolean,
    normalise_country_code,
    normalise_currency,
    normalise_identifier,
    normalise_numeric,
    normalise_string,
    parse_timestamp,
)


def test_empty_strings_and_null_like_values_normalise_to_none() -> None:
    assert normalise_string("") is None
    assert normalise_string(" nan ") is None
    assert normalise_string("None") is None
    assert normalise_string(None) is None
    assert normalise_string(pd.NA) is None


def test_country_codes_are_uppercase() -> None:
    assert normalise_country_code(" au ") == "AU"


def test_currency_codes_are_uppercase() -> None:
    assert normalise_currency(" aud ") == "AUD"
    assert normalise_currency(None) == "USD"


def test_boolean_parsing_handles_booleans_numbers_and_strings() -> None:
    assert normalise_boolean(True) is True
    assert normalise_boolean(1) is True
    assert normalise_boolean(0) is False
    assert normalise_boolean("yes") is True
    assert normalise_boolean("false") is False


def test_numeric_parsing_handles_strings_and_numbers() -> None:
    assert normalise_numeric("12.5") == 12.5
    assert normalise_numeric(7) == 7.0
    assert normalise_numeric("bad", default=None) is None


def test_timestamp_parsing_handles_valid_timestamps_and_missing_values() -> None:
    parsed = parse_timestamp("2025-01-01T00:00:00Z")

    assert parsed is not None
    assert parsed.year == 2025
    assert parse_timestamp(None) is None


def test_ensure_columns_adds_missing_columns() -> None:
    frame = ensure_columns(pd.DataFrame({"a": [1]}), ("a", "b"))

    assert list(frame.columns) == ["a", "b"]
    assert pd.isna(frame.loc[0, "b"])


def test_identifier_normalisation_preserves_deterministic_ids() -> None:
    assert normalise_identifier(" acc_001 ") == "ACC_001"
    assert normalise_identifier("001", prefix="acc") == "ACC_001"
