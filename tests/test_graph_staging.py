"""Tests for graph staged input readers."""

import pandas as pd
import pytest
from sqlalchemy.sql.elements import TextClause

import graph_aml.graph.staging as staging_module
from graph_aml.graph import GraphLoadError, read_graph_inputs


class FakeEngine:
    pass


def _capture_read_sql(monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, object]] | None = None):
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read_sql(query: TextClause, engine: object, params: dict[str, object] | None = None):
        calls.append((str(query), params))
        return pd.DataFrame([] if rows is None else rows)

    monkeypatch.setattr(staging_module.pd, "read_sql_query", fake_read_sql)
    return calls


@pytest.mark.parametrize(
    ("reader_name", "table_name"),
    (
        ("read_graph_customers", "staging.customers"),
        ("read_graph_accounts", "staging.accounts"),
        ("read_graph_transactions", "staging.transactions"),
        ("read_graph_counterparties", "staging.counterparties"),
        ("read_graph_countries", "staging.countries"),
        ("read_graph_alerts", "aml.alerts"),
    ),
)
def test_graph_readers_query_expected_tables(
    monkeypatch: pytest.MonkeyPatch, reader_name: str, table_name: str
) -> None:
    calls = _capture_read_sql(monkeypatch)

    getattr(staging_module, reader_name)(FakeEngine(), limit=10)

    assert table_name in calls[0][0]
    assert calls[0][1] == {"limit": 10}
    assert "LIMIT :limit" in calls[0][0]


def test_read_graph_inputs_returns_all_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    _capture_read_sql(monkeypatch)

    inputs = read_graph_inputs(FakeEngine())

    assert set(inputs) == {
        "customers",
        "accounts",
        "transactions",
        "counterparties",
        "countries",
        "alerts",
    }


def test_include_alerts_false_skips_alert_read(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_read_sql(monkeypatch)

    inputs = read_graph_inputs(FakeEngine(), include_alerts=False)

    assert all("aml.alerts" not in query for query, _ in calls)
    assert list(inputs["alerts"].columns) == list(staging_module.GRAPH_ALERT_COLUMNS)


def test_invalid_limits_raise_graph_load_error() -> None:
    with pytest.raises(GraphLoadError):
        staging_module.read_graph_customers(FakeEngine(), limit=-1)


def test_staged_read_failures_raise_graph_load_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> pd.DataFrame:
        raise RuntimeError("boom")

    monkeypatch.setattr(staging_module.pd, "read_sql_query", fail)

    with pytest.raises(GraphLoadError):
        staging_module.read_graph_accounts(FakeEngine())
