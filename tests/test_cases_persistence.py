"""Tests for case persistence SQL and workflow."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CasePersistenceConfig,
    CasePersistenceError,
    build_case_alert_upsert_sql,
    build_case_entity_upsert_sql,
    build_case_upsert_sql,
    persist_cases,
    prepare_cases_for_persistence,
    validate_case_persistence_config,
)
from graph_aml.cases.generation import CaseGenerationResult


class FakeConnection:
    def __init__(self) -> None:
        self.executions: list[tuple[object, object]] = []

    def execute(self, statement, params=None):  # noqa: ANN001
        self.executions.append((statement, params))


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self):
        engine = self

        class Context:
            def __enter__(self_inner):
                return engine.connection

            def __exit__(self_inner, exc_type, exc, tb):  # noqa: ANN001
                return False

        return Context()


def result() -> CaseGenerationResult:
    cases = pd.DataFrame(
        {
            "case_id": ["CASE1"],
            "case_version": ["case_generation_v1"],
            "primary_account_id": ["A1"],
            "primary_customer_id": ["C1"],
            "related_accounts": [["A1"]],
            "related_customers": [["C1"]],
            "alert_ids": [["AL1"]],
            "typologies": [["structuring"]],
            "rule_names": [["Structuring"]],
            "total_transaction_value": [10.0],
            "alert_count": [1],
            "unique_typology_count": [1],
            "evidence_transaction_count": [1],
            "max_rule_risk_score": [80.0],
            "mean_rule_risk_score": [80.0],
            "max_account_risk_score": [88.0],
            "priority_score": [88.0],
            "severity": ["high"],
            "status": ["New"],
            "grouping_strategy": ["account"],
            "case_group_key": ["A1"],
            "summary": ["summary"],
            "created_at": [pd.Timestamp("2026-01-01", tz="UTC")],
            "updated_at": [pd.Timestamp("2026-01-01", tz="UTC")],
        }
    )
    return CaseGenerationResult(
        cases=cases,
        case_alerts=pd.DataFrame({"case_id": ["CASE1"], "alert_id": ["AL1"]}),
        case_entities=pd.DataFrame(
            {
                "case_id": ["CASE1"],
                "entity_type": ["account"],
                "entity_id": ["A1"],
                "relationship": ["primary_account"],
            }
        ),
        groups=pd.DataFrame(),
    )


def test_default_case_persistence_config_is_valid() -> None:
    validate_case_persistence_config(CasePersistenceConfig())


def test_invalid_persistence_config_raises() -> None:
    with pytest.raises(CasePersistenceError):
        CasePersistenceConfig(case_version="")
    with pytest.raises(CasePersistenceError):
        CasePersistenceConfig(batch_size=0)


def test_prepare_cases_for_persistence_returns_all_frames() -> None:
    prepared = prepare_cases_for_persistence(result())
    assert set(prepared) == {"cases", "case_alerts", "case_entities"}
    assert "metadata" in prepared["cases"].columns


def test_case_upsert_sql_targets_case_tables_and_named_params() -> None:
    assert "INSERT INTO aml.cases" in build_case_upsert_sql()
    assert ":case_id" in build_case_upsert_sql()
    assert "ON CONFLICT" in build_case_upsert_sql()
    assert "created_at = EXCLUDED.created_at" not in build_case_upsert_sql()
    assert "INSERT INTO aml.case_alerts" in build_case_alert_upsert_sql()
    assert "INSERT INTO aml.case_entities" in build_case_entity_upsert_sql()


def test_persist_cases_returns_result_and_skips_audit() -> None:
    engine = FakeEngine()
    persisted = persist_cases(engine, result(), CasePersistenceConfig(write_audit=False))
    assert persisted.cases_persisted == 1
    assert persisted.case_alert_links_persisted == 1
    assert persisted.case_entity_links_persisted == 1


def test_persistence_functions_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    persist_cases(FakeEngine(), result(), CasePersistenceConfig(write_audit=False))
