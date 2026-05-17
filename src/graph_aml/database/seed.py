"""Deterministic smoke seed helpers for local database checks."""

from pathlib import Path

from sqlalchemy import Engine

from graph_aml.database.exceptions import DatabaseResetRefusedError, DatabaseSeedError
from graph_aml.database.execution import execute_sql

SEED_SMOKE_DATA_SQL = "005_seed_smoke_data.sql"
DELETE_SMOKE_SEED_DATA_SQL = "006_delete_smoke_seed_data.sql"


def _get_seed_sql_dir() -> Path:
    return Path(__file__).resolve().parent / "sql"


def _read_seed_sql(filename: str) -> str:
    path = _get_seed_sql_dir() / filename
    if not path.is_file():
        raise FileNotFoundError(f"Seed SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def read_seed_smoke_data_sql() -> str:
    """Return idempotent smoke seed SQL."""

    return _read_seed_sql(SEED_SMOKE_DATA_SQL)


def read_delete_smoke_seed_data_sql() -> str:
    """Return targeted smoke seed cleanup SQL."""

    return _read_seed_sql(DELETE_SMOKE_SEED_DATA_SQL)


def seed_smoke_data(engine: Engine) -> dict[str, int]:
    """Insert deterministic smoke data for local database checks."""

    try:
        count = execute_sql(engine, read_seed_smoke_data_sql())
    except Exception as exc:
        raise DatabaseSeedError(f"Smoke seed execution failed: {exc}") from exc
    return {"seed_statements_executed": count}


def delete_smoke_seed_data(engine: Engine, confirm: bool = False) -> dict[str, int]:
    """Delete only deterministic smoke seed data."""

    if not confirm:
        raise DatabaseResetRefusedError(
            "Smoke seed deletion refused. Pass confirm=True for destructive operations."
        )
    try:
        count = execute_sql(engine, read_delete_smoke_seed_data_sql())
    except Exception as exc:
        raise DatabaseSeedError(f"Smoke seed cleanup failed: {exc}") from exc
    return {"delete_seed_statements_executed": count}
