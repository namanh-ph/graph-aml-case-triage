"""Static tests for release readiness database DDL."""

from pathlib import Path

DDL = Path("src/graph_aml/database/sql/003_create_core_tables.sql")


def test_release_database_tables_exist() -> None:
    text = DDL.read_text(encoding="utf-8").lower()
    for table in (
        "governance.release_readiness_runs",
        "governance.release_repository_checks",
        "governance.release_documentation_checks",
        "governance.release_artefact_checks",
        "governance.release_evidence_index",
        "governance.release_portfolio_pack",
    ):
        assert table in text
    assert "release_run_id text primary key" in text
    assert "metadata jsonb" in text
    assert "idx_release_readiness_runs_version" in text
    assert "drop table" not in text
