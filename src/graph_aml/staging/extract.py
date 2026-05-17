"""Raw table extraction utilities for staging transformations."""

from __future__ import annotations

import json
from typing import cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.staging.exceptions import RawExtractionError

RAW_TABLE_MAPPING = {
    "countries": "raw.countries_raw",
    "customers": "raw.customers_raw",
    "accounts": "raw.accounts_raw",
    "counterparties": "raw.counterparties_raw",
    "devices": "raw.devices_raw",
    "transactions": "raw.transactions_raw",
}
ALLOWED_RAW_TABLES = frozenset(RAW_TABLE_MAPPING.values())
LINEAGE_COLUMNS = ("raw_record_id", "source_system", "source_file", "ingested_at", "record_hash")


def read_raw_table(
    engine: Engine,
    qualified_table_name: str,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read one whitelisted raw table into a DataFrame."""

    if qualified_table_name not in ALLOWED_RAW_TABLES:
        raise RawExtractionError(f"Unsupported raw table: {qualified_table_name}")
    if limit is not None and limit < 0:
        raise RawExtractionError("limit must be non-negative")

    sql = f"SELECT * FROM {qualified_table_name} ORDER BY raw_record_id"
    params: dict[str, int] | None = None
    if limit is not None:
        sql += " LIMIT :limit"
        params = {"limit": int(limit)}

    try:
        return pd.read_sql_query(text(sql), engine, params=params)
    except Exception as exc:
        raise RawExtractionError(f"Failed to read {qualified_table_name}: {exc}") from exc


def read_raw_dataset(engine: Engine, limit: int | None = None) -> dict[str, pd.DataFrame]:
    """Read all supported raw tables keyed by logical table name."""

    try:
        return {
            logical_table: read_raw_table(engine, qualified_table, limit=limit)
            for logical_table, qualified_table in RAW_TABLE_MAPPING.items()
        }
    except RawExtractionError:
        raise
    except Exception as exc:
        raise RawExtractionError(f"Failed to read raw dataset: {exc}") from exc


def _payload_to_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): payload_value for key, payload_value in value.items()}
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return {str(key): payload_value for key, payload_value in parsed.items()}
    raise RawExtractionError(f"raw_payload must be a JSON object, got {type(value).__name__}")


def extract_payload_frame(raw_frame: pd.DataFrame) -> pd.DataFrame:
    """Expand raw_payload JSON objects and preserve raw lineage columns."""

    if "raw_payload" not in raw_frame.columns:
        raise RawExtractionError("raw_frame is missing raw_payload column")
    try:
        payloads = [_payload_to_dict(value) for value in raw_frame["raw_payload"]]
        payload_frame = pd.DataFrame(payloads)
        lineage = raw_frame[[column for column in LINEAGE_COLUMNS if column in raw_frame.columns]]
        output = payload_frame.copy()
        for column in lineage.columns:
            if column in output.columns:
                output[f"raw_{column}"] = lineage[column].to_numpy()
            else:
                output[column] = lineage[column].to_numpy()
        return cast(pd.DataFrame, output)
    except RawExtractionError:
        raise
    except Exception as exc:
        raise RawExtractionError(f"Failed to extract raw payload frame: {exc}") from exc
