"""Conversion helpers for PostgreSQL raw table records."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

import pandas as pd


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(cast(Any, value))
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, bool) else False


def _serialisable_value(value: object) -> object:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "item"):
        try:
            item_value: Any = value.item()
            return item_value
        except (AttributeError, ValueError):
            return str(value)
    return value


def normalise_missing_values(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert pandas missing values to Python None values."""

    rows = [
        {column: None if _is_missing(value) else value for column, value in row.items()}
        for row in frame.astype(object).to_dict(orient="records")
    ]
    return pd.DataFrame(rows, columns=frame.columns, dtype=object)


def build_raw_payload(row: dict[str, object]) -> dict[str, object]:
    """Build a JSON-serialisable raw payload from a source row."""

    return {key: _serialisable_value(value) for key, value in row.items()}


def build_record_hash(payload: dict[str, object]) -> str:
    """Build a deterministic SHA-256 hash for a raw payload."""

    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _transaction_field(payload: dict[str, object], field: str) -> object:
    return payload.get(field)


def dataframe_to_raw_records(
    frame: pd.DataFrame,
    source_system: str,
    source_file: str,
    table_name: str,
) -> list[dict[str, object]]:
    """Convert a source DataFrame into common raw table records."""

    normalised = normalise_missing_values(frame)
    records: list[dict[str, object]] = []
    for row in normalised.to_dict(orient="records"):
        source_row = {str(key): value for key, value in row.items()}
        payload = build_raw_payload(source_row)
        record: dict[str, object] = {
            "source_system": source_system,
            "source_file": source_file,
            "raw_payload": payload,
            "record_hash": build_record_hash(payload),
        }
        if table_name == "transactions":
            record.update(
                {
                    "transaction_id": _transaction_field(payload, "transaction_id"),
                    "sender_account_id": _transaction_field(payload, "sender_account_id"),
                    "receiver_account_id": _transaction_field(payload, "receiver_account_id"),
                    "transaction_timestamp": _transaction_field(
                        payload,
                        "transaction_timestamp",
                    ),
                    "amount": _transaction_field(payload, "amount"),
                    "currency": _transaction_field(payload, "currency"),
                }
            )
        records.append(record)
    return records
