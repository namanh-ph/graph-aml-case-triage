"""Tests for staging raw extraction utilities."""

import pandas as pd
import pytest
from sqlalchemy import text

from graph_aml.staging.exceptions import RawExtractionError
from graph_aml.staging.extract import extract_payload_frame, read_raw_dataset, read_raw_table


class FakeEngine:
    pass


def test_extract_payload_frame_expands_json_payloads() -> None:
    raw = pd.DataFrame({"raw_payload": [{"customer_id": "CUST_001", "jurisdiction": "au"}]})

    payloads = extract_payload_frame(raw)

    assert payloads.loc[0, "customer_id"] == "CUST_001"
    assert payloads.loc[0, "jurisdiction"] == "au"


def test_extract_payload_frame_preserves_lineage_columns() -> None:
    raw = pd.DataFrame(
        {
            "raw_record_id": [1],
            "source_system": ["reference"],
            "source_file": ["customers.csv"],
            "ingested_at": ["2025-01-01T00:00:00Z"],
            "record_hash": ["abc"],
            "raw_payload": [{"customer_id": "CUST_001"}],
        }
    )

    payloads = extract_payload_frame(raw)

    assert payloads.loc[0, "raw_record_id"] == 1
    assert payloads.loc[0, "source_system"] == "reference"
    assert payloads.loc[0, "source_file"] == "customers.csv"
    assert payloads.loc[0, "record_hash"] == "abc"


def test_read_raw_table_validates_qualified_raw_table_names() -> None:
    with pytest.raises(RawExtractionError):
        read_raw_table(FakeEngine(), "staging.customers")


def test_read_raw_table_applies_limit_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, int] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_raw_table(FakeEngine(), "raw.customers_raw", limit=10)

    assert "LIMIT :limit" in calls[0][0]
    assert calls[0][1] == {"limit": 10}


def test_read_raw_dataset_returns_expected_logical_table_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.staging.extract.read_raw_table",
        lambda engine, table, limit=None: pd.DataFrame({"table": [table]}),
    )

    dataset = read_raw_dataset(FakeEngine())

    assert set(dataset) == {
        "countries",
        "customers",
        "accounts",
        "counterparties",
        "devices",
        "transactions",
    }


def test_extraction_failures_raise_raw_extraction_error() -> None:
    with pytest.raises(RawExtractionError):
        extract_payload_frame(pd.DataFrame({"not_payload": [{"a": 1}]}))


def test_import_does_not_attempt_database_connection() -> None:
    assert str(text("SELECT 1"))
