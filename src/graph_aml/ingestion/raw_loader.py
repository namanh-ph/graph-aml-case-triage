"""Raw PostgreSQL loaders for silver-layer parquet datasets."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.ingestion.audit import write_ingestion_audit_event
from graph_aml.ingestion.exceptions import IngestionSourceError, RawIngestionError
from graph_aml.ingestion.records import dataframe_to_raw_records
from graph_aml.ingestion.sources import DEFAULT_SILVER_DIR, resolve_silver_paths

RAW_TABLE_MAPPING = {
    "countries": "raw.countries_raw",
    "customers": "raw.customers_raw",
    "accounts": "raw.accounts_raw",
    "counterparties": "raw.counterparties_raw",
    "devices": "raw.devices_raw",
    "transactions": "raw.transactions_raw",
}

DEFAULT_SOURCE_SYSTEM = "core_banking_export"


def read_table_file(path: Path | str) -> pd.DataFrame:
    """Read a silver-layer table file (parquet preferred; CSV supported for legacy)."""

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Ingestion table file not found: {file_path}")
    if file_path.suffix == ".parquet":
        try:
            return pd.read_parquet(file_path)
        except ImportError as exc:
            raise IngestionSourceError("Parquet input requires pyarrow or fastparquet.") from exc
    if file_path.suffix == ".csv":
        return pd.read_csv(file_path)
    raise IngestionSourceError(f"Unsupported ingestion file extension: {file_path.suffix}")


def _insert_sql(qualified_table_name: str) -> str:
    if qualified_table_name == "raw.transactions_raw":
        return """
            INSERT INTO raw.transactions_raw (
                source_system,
                source_file,
                raw_payload,
                record_hash,
                transaction_id,
                sender_account_id,
                receiver_account_id,
                transaction_timestamp,
                amount,
                currency
            )
            VALUES (
                :source_system,
                :source_file,
                CAST(:raw_payload AS JSONB),
                :record_hash,
                :transaction_id,
                :sender_account_id,
                :receiver_account_id,
                :transaction_timestamp,
                :amount,
                :currency
            )
        """
    if qualified_table_name in set(RAW_TABLE_MAPPING.values()):
        return f"""
            INSERT INTO {qualified_table_name} (
                source_system,
                source_file,
                raw_payload,
                record_hash
            )
            VALUES (
                :source_system,
                :source_file,
                CAST(:raw_payload AS JSONB),
                :record_hash
            )
        """
    raise RawIngestionError(f"Unsupported raw table: {qualified_table_name}")


def _prepare_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    prepared: list[dict[str, object]] = []
    for record in records:
        row = dict(record)
        row["raw_payload"] = json.dumps(row["raw_payload"], sort_keys=True, default=str)
        prepared.append(row)
    return prepared


def insert_raw_records(
    engine: Engine,
    qualified_table_name: str,
    records: list[dict[str, object]],
) -> int:
    """Insert raw records into a raw PostgreSQL table."""

    if not records:
        return 0
    statement = text(_insert_sql(qualified_table_name))
    try:
        with engine.begin() as connection:
            connection.execute(statement, _prepare_records(records))
    except Exception as exc:
        raise RawIngestionError(
            f"Failed to insert raw records into {qualified_table_name}: {exc}"
        ) from exc
    return len(records)


def ingest_silver_to_raw(
    engine: Engine,
    silver_dir: Path | str = DEFAULT_SILVER_DIR,
    source_system: str = DEFAULT_SOURCE_SYSTEM,
    write_audit: bool = True,
) -> dict[str, int]:
    """Ingest silver-layer parquet files into PostgreSQL raw tables."""

    table_paths = resolve_silver_paths(silver_dir)
    row_counts: dict[str, int] = {}
    for logical_table, qualified_table in RAW_TABLE_MAPPING.items():
        if logical_table not in table_paths:
            raise FileNotFoundError(f"Silver table file missing: {logical_table}")
        table_path = table_paths[logical_table]
        frame = read_table_file(table_path)
        records = dataframe_to_raw_records(
            frame,
            source_system=source_system,
            source_file=table_path.name,
            table_name=logical_table,
        )
        row_counts[logical_table] = insert_raw_records(engine, qualified_table, records)
    if write_audit:
        write_ingestion_audit_event(
            engine,
            dataset_id="aml_core_banking",
            dataset_version="current",
            source_system=source_system,
            source_file=str(Path(silver_dir).resolve()),
            row_counts=row_counts,
            status="completed",
        )
    return row_counts
