"""Tests for PostgreSQL schema SQL file structure."""

import re
from pathlib import Path

from graph_aml.database.schemas import get_schema_sql_dir

CREATE_ORDER = ("raw", "staging", "mart", "aml", "governance")
DROP_ORDER = ("governance", "aml", "mart", "staging", "raw")
CREATE_SQL_PATH = get_schema_sql_dir() / "001_create_schemas.sql"
DROP_SQL_PATH = get_schema_sql_dir() / "002_drop_schemas.sql"


def read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_schema_order(sql: str, verb: str) -> list[str]:
    pattern = rf"{verb} SCHEMA IF (?:NOT )?EXISTS ([a-z_]+)"
    return re.findall(pattern, sql, flags=re.IGNORECASE)


def test_schema_sql_files_exist() -> None:
    assert CREATE_SQL_PATH.is_file()
    assert DROP_SQL_PATH.is_file()


def test_create_sql_creates_schemas_in_canonical_order() -> None:
    assert tuple(extract_schema_order(read_sql(CREATE_SQL_PATH), "CREATE")) == CREATE_ORDER


def test_drop_sql_drops_schemas_in_reverse_order() -> None:
    assert tuple(extract_schema_order(read_sql(DROP_SQL_PATH), "DROP")) == DROP_ORDER


def test_create_sql_is_idempotent() -> None:
    sql = read_sql(CREATE_SQL_PATH)

    assert sql.count("IF NOT EXISTS") == len(CREATE_ORDER)


def test_drop_sql_is_idempotent() -> None:
    sql = read_sql(DROP_SQL_PATH)

    assert sql.count("IF EXISTS") == len(DROP_ORDER)


def test_sql_files_do_not_contain_environment_credentials() -> None:
    combined_sql = read_sql(CREATE_SQL_PATH) + read_sql(DROP_SQL_PATH)

    for forbidden_value in ("POSTGRES_PASSWORD", "change_me", "graph_aml_user"):
        assert forbidden_value not in combined_sql


def test_sql_files_do_not_contain_table_or_data_load_statements() -> None:
    combined_sql = (read_sql(CREATE_SQL_PATH) + read_sql(DROP_SQL_PATH)).upper()

    for forbidden_statement in ("CREATE TABLE", "INSERT INTO", "COPY"):
        assert forbidden_statement not in combined_sql
