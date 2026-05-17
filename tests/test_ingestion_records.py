"""Tests for raw ingestion record conversion."""

import json

import pandas as pd

from graph_aml.ingestion import (
    build_raw_payload,
    build_record_hash,
    dataframe_to_raw_records,
    normalise_missing_values,
)


def test_normalise_missing_values_converts_missing_values_to_none() -> None:
    frame = pd.DataFrame({"value": [1, pd.NA, None, float("nan")]})

    normalised = normalise_missing_values(frame)

    assert normalised.loc[1, "value"] is None
    assert normalised.loc[2, "value"] is None
    assert normalised.loc[3, "value"] is None


def test_build_raw_payload_returns_dictionary() -> None:
    payload = build_raw_payload({"timestamp": pd.Timestamp("2025-01-01"), "value": 1})

    assert payload == {"timestamp": "2025-01-01T00:00:00", "value": 1}


def test_build_record_hash_is_deterministic() -> None:
    payload = {"b": 2, "a": 1}

    assert build_record_hash(payload) == build_record_hash({"a": 1, "b": 2})


def test_build_record_hash_changes_when_payload_changes() -> None:
    assert build_record_hash({"a": 1}) != build_record_hash({"a": 2})


def test_dataframe_to_raw_records_returns_one_record_per_row() -> None:
    frame = pd.DataFrame({"id": ["one", "two"]})

    records = dataframe_to_raw_records(frame, "reference", "customers.csv", "customers")

    assert len(records) == 2


def test_raw_records_include_common_raw_columns() -> None:
    frame = pd.DataFrame({"id": ["one"]})

    record = dataframe_to_raw_records(frame, "reference", "customers.csv", "customers")[0]

    assert record["source_system"] == "reference"
    assert record["source_file"] == "customers.csv"
    assert record["raw_payload"] == {"id": "one"}
    assert "record_hash" in record


def test_transaction_records_include_extracted_fields() -> None:
    frame = pd.DataFrame(
        {
            "transaction_id": ["TXN_001"],
            "sender_account_id": ["ACC_001"],
            "receiver_account_id": ["ACC_002"],
            "transaction_timestamp": ["2025-01-01T00:00:00"],
            "amount": [10.5],
            "currency": ["USD"],
        }
    )

    record = dataframe_to_raw_records(frame, "reference", "transactions.csv", "transactions")[0]

    assert record["transaction_id"] == "TXN_001"
    assert record["sender_account_id"] == "ACC_001"
    assert record["receiver_account_id"] == "ACC_002"
    assert record["transaction_timestamp"] == "2025-01-01T00:00:00"
    assert record["amount"] == 10.5
    assert record["currency"] == "USD"


def test_json_serialisation_is_stable_for_hash_generation() -> None:
    payload = {"b": 2, "a": 1}
    expected_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    assert expected_json == '{"a":1,"b":2}'
    assert build_record_hash(payload) == build_record_hash({"a": 1, "b": 2})
