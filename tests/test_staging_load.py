"""Tests for staging load utilities."""

import pandas as pd
import pytest

from graph_aml.staging import STAGING_TABLE_MAPPING
from graph_aml.staging.exceptions import StagingLoadError
from graph_aml.staging.load import load_staging_dataset, upsert_staging_table


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.executions: list[tuple[str, object]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object, parameters: object | None = None) -> None:
        if self.fail:
            raise RuntimeError("load failed")
        self.executions.append((str(statement), parameters))


class FakeEngine:
    def __init__(self, fail: bool = False) -> None:
        self.connection = FakeConnection(fail=fail)

    def begin(self) -> FakeConnection:
        return self.connection


def test_staging_table_mapping_includes_all_logical_tables() -> None:
    assert set(STAGING_TABLE_MAPPING) == {
        "countries",
        "customers",
        "accounts",
        "counterparties",
        "devices",
        "transactions",
    }


def test_upsert_staging_table_returns_zero_for_empty_dataframe() -> None:
    assert upsert_staging_table(FakeEngine(), "countries", pd.DataFrame(), ("country_code",)) == 0


def test_upsert_staging_table_builds_sql_with_on_conflict() -> None:
    engine = FakeEngine()
    frame = pd.DataFrame([{"country_code": "AU", "country_name": "Australia"}])

    upsert_staging_table(engine, "countries", frame, ("country_code",))

    assert "ON CONFLICT (country_code) DO UPDATE" in engine.connection.executions[0][0]


def test_upsert_staging_table_uses_bound_parameters() -> None:
    engine = FakeEngine()
    frame = pd.DataFrame([{"country_code": "AU", "country_name": "Australia"}])

    upsert_staging_table(engine, "countries", frame, ("country_code",))

    params = engine.connection.executions[0][1]
    assert isinstance(params, list)
    assert params[0]["country_code"] == "AU"


def test_load_staging_dataset_loads_tables_in_dependency_safe_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded: list[str] = []

    def fake_upsert(engine, table_name, frame, conflict_columns):
        loaded.append(table_name)
        return len(frame)

    monkeypatch.setattr("graph_aml.staging.load.upsert_staging_table", fake_upsert)

    load_staging_dataset(FakeEngine(), _staging_dataset())

    assert loaded == [
        "countries",
        "customers",
        "accounts",
        "counterparties",
        "devices",
        "transactions",
    ]


def test_load_staging_dataset_returns_row_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.staging.load.upsert_staging_table",
        lambda engine, table_name, frame, conflict_columns: len(frame),
    )

    row_counts = load_staging_dataset(FakeEngine(), _staging_dataset())

    assert row_counts == {table_name: 1 for table_name in STAGING_TABLE_MAPPING}


def test_load_failures_raise_staging_load_error() -> None:
    frame = pd.DataFrame([{"country_code": "AU", "country_name": "Australia"}])

    with pytest.raises(StagingLoadError):
        upsert_staging_table(FakeEngine(fail=True), "countries", frame, ("country_code",))


def _staging_dataset() -> dict[str, pd.DataFrame]:
    return {
        "countries": pd.DataFrame([{"country_code": "AU"}]),
        "customers": pd.DataFrame([{"customer_id": "CUST_001"}]),
        "accounts": pd.DataFrame([{"account_id": "ACC_001"}]),
        "counterparties": pd.DataFrame([{"counterparty_id": "CP_001"}]),
        "devices": pd.DataFrame([{"device_id": "DEV_001"}]),
        "transactions": pd.DataFrame([{"transaction_id": "TXN_001"}]),
    }
