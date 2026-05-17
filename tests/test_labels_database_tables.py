from __future__ import annotations

from pathlib import Path

SQL = Path("src/graph_aml/database/sql/003_create_core_tables.sql")


def _text() -> str:
    return SQL.read_text(encoding="utf-8")


def test_case_labels_table_ddl_exists() -> None:
    assert "CREATE TABLE IF NOT EXISTS aml.case_labels" in _text()


def test_account_labels_table_ddl_exists() -> None:
    assert "CREATE TABLE IF NOT EXISTS aml.account_labels" in _text()


def test_case_supervised_dataset_table_ddl_exists() -> None:
    assert "CREATE TABLE IF NOT EXISTS mart.case_supervised_dataset" in _text()


def test_account_supervised_dataset_table_ddl_exists() -> None:
    assert "CREATE TABLE IF NOT EXISTS mart.account_supervised_dataset" in _text()


def test_label_tables_contain_version_and_binary_label_columns() -> None:
    text = _text()
    assert "label_version TEXT NOT NULL" in text
    assert "case_label INTEGER NOT NULL" in text
    assert "account_label INTEGER NOT NULL" in text


def test_dataset_tables_contain_dataset_version_and_feature_columns() -> None:
    text = _text()
    assert "dataset_version TEXT NOT NULL" in text
    assert "case_risk_score DOUBLE PRECISION" in text
    assert "account_risk_score DOUBLE PRECISION" in text


def test_ddl_includes_primary_keys() -> None:
    text = _text()
    assert "PRIMARY KEY (case_id, label_version)" in text
    assert "PRIMARY KEY (account_id, dataset_version)" in text


def test_ddl_includes_useful_indexes() -> None:
    text = _text()
    assert "idx_case_labels_case_label" in text
    assert "idx_account_supervised_dataset_label" in text


def test_ddl_is_non_destructive() -> None:
    section = _text().split("CREATE TABLE IF NOT EXISTS aml.case_labels", maxsplit=1)[1]
    assert "DROP TABLE" not in section
    assert "TRUNCATE" not in section
