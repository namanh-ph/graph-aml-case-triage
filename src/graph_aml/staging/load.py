"""PostgreSQL staging table upsert utilities."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.staging.exceptions import StagingLoadError

STAGING_TABLE_MAPPING = {
    "countries": "staging.countries",
    "customers": "staging.customers",
    "accounts": "staging.accounts",
    "counterparties": "staging.counterparties",
    "devices": "staging.devices",
    "transactions": "staging.transactions",
}
CONFLICT_COLUMNS = {
    "countries": ("country_code",),
    "customers": ("customer_id",),
    "accounts": ("account_id",),
    "counterparties": ("counterparty_id",),
    "devices": ("device_id",),
    "transactions": ("transaction_id",),
}
LOAD_ORDER = (
    "countries",
    "customers",
    "accounts",
    "counterparties",
    "devices",
    "transactions",
)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(cast(Any, value))
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, bool) else False


def _to_db_value(value: object) -> object:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime | date):
        return value
    if hasattr(value, "item"):
        try:
            item_value: object = value.item()
            return item_value
        except (AttributeError, ValueError):
            return str(value)
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        {str(column): _to_db_value(value) for column, value in row.items()}
        for row in frame.astype(object).to_dict(orient="records")
    ]


def _upsert_sql(qualified_table_name: str, columns: tuple[str, ...], keys: tuple[str, ...]) -> str:
    insert_columns = ", ".join(columns)
    placeholders = ", ".join(f":{column}" for column in columns)
    conflict_columns = ", ".join(keys)
    update_columns = [column for column in columns if column not in keys]
    if update_columns:
        update_clause = ", ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
        return f"""
            INSERT INTO {qualified_table_name} ({insert_columns})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_columns}) DO UPDATE SET {update_clause}
        """
    return f"""
        INSERT INTO {qualified_table_name} ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_columns}) DO NOTHING
    """


def upsert_staging_table(
    engine: Engine,
    table_name: str,
    frame: pd.DataFrame,
    conflict_columns: tuple[str, ...],
) -> int:
    """Upsert one logical staging DataFrame into PostgreSQL."""

    if frame.empty:
        return 0
    if table_name not in STAGING_TABLE_MAPPING:
        raise StagingLoadError(f"Unsupported staging table: {table_name}")
    missing_conflict_columns = set(conflict_columns).difference(frame.columns)
    if missing_conflict_columns:
        raise StagingLoadError(
            f"{table_name} is missing conflict columns: {sorted(missing_conflict_columns)}"
        )

    columns = tuple(str(column) for column in frame.columns)
    statement = text(_upsert_sql(STAGING_TABLE_MAPPING[table_name], columns, conflict_columns))
    try:
        with engine.begin() as connection:
            connection.execute(statement, _records(frame))
    except Exception as exc:
        raise StagingLoadError(f"Failed to load {table_name} into staging: {exc}") from exc
    return len(frame)


def load_staging_dataset(
    engine: Engine,
    staging_dataset: dict[str, pd.DataFrame],
) -> dict[str, int]:
    """Load all staging tables in dependency-safe order."""

    row_counts: dict[str, int] = {}
    try:
        for table_name in LOAD_ORDER:
            frame = staging_dataset.get(table_name, pd.DataFrame())
            row_counts[table_name] = upsert_staging_table(
                engine,
                table_name,
                frame,
                CONFLICT_COLUMNS[table_name],
            )
        return row_counts
    except StagingLoadError:
        raise
    except Exception as exc:
        raise StagingLoadError(f"Failed to load staging dataset: {exc}") from exc
