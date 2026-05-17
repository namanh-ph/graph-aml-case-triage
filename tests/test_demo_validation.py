from __future__ import annotations

import json

import pandas as pd
import pytest

from graph_aml.demo import (
    DemoValidationError,
    build_demo_validation_summary,
    read_demo_database_counts,
    validate_demo_artefacts,
    validate_demo_database_counts,
)


class FakeEngine:
    pass


def test_database_count_reader_queries_expected_tables(monkeypatch) -> None:
    queries: list[str] = []

    def fake_read_sql_query(sql, engine, params=None):  # noqa: ANN001
        queries.append(str(sql))
        return pd.DataFrame({"row_count": [1]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    counts = read_demo_database_counts(FakeEngine())  # type: ignore[arg-type]
    assert counts["transactions"] == 1
    assert any("staging.transactions" in query for query in queries)
    assert any("aml.case_evidence_packs" in query for query in queries)


def test_count_validation_passes_when_thresholds_are_met() -> None:
    counts = {
        "transactions": 1,
        "accounts": 1,
        "alerts": 1,
        "cases": 1,
        "case_risk_scores": 1,
        "case_evidence_packs": 1,
        "audit_events": 1,
    }
    assert validate_demo_database_counts(counts)["status"] == "ok"


def test_count_validation_reports_warnings_when_thresholds_unmet() -> None:
    assert validate_demo_database_counts({})["status"] == "warning"


def test_artefact_validation_counts_report_files(tmp_path) -> None:
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")
    result = validate_demo_artefacts(str(tmp_path))
    assert result["file_count"] == 1


def test_artefact_validation_handles_missing_report_directory(tmp_path) -> None:
    result = validate_demo_artefacts(str(tmp_path / "missing"))
    assert result["file_count"] == 0


def test_validation_summary_combines_counts_and_artefacts(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "graph_aml.demo.validation.read_demo_database_counts",
        lambda engine: {
            "transactions": 1,
            "accounts": 1,
            "alerts": 1,
            "cases": 1,
            "case_risk_scores": 1,
            "case_evidence_packs": 1,
            "audit_events": 1,
        },
    )
    summary = build_demo_validation_summary(FakeEngine())  # type: ignore[arg-type]
    assert "database" in summary


def test_validation_helpers_return_json_serialisable_payloads(tmp_path) -> None:
    json.dumps(validate_demo_artefacts(str(tmp_path)), default=str)


def test_validation_functions_do_not_create_engines_internally(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *args, **kwargs: pytest.fail("no engine"),
    )
    assert build_demo_validation_summary(engine=None)["database"]["status"] == "skipped"


def test_read_failures_raise_demo_validation_error(monkeypatch) -> None:
    def fail_read_sql_query(sql, engine, params=None):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)
    with pytest.raises(DemoValidationError):
        read_demo_database_counts(FakeEngine())  # type: ignore[arg-type]
