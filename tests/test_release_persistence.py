"""Tests for release readiness persistence SQL."""

import pytest

from graph_aml.release import ReleasePersistenceError
from graph_aml.release.persistence import (
    ReleasePersistenceConfig,
    build_release_artefact_check_insert_sql,
    build_release_documentation_check_insert_sql,
    build_release_evidence_index_insert_sql,
    build_release_portfolio_pack_upsert_sql,
    build_release_readiness_run_insert_sql,
    build_release_repository_check_insert_sql,
    validate_release_persistence_config,
)


def test_default_release_persistence_config_is_valid() -> None:
    validate_release_persistence_config(ReleasePersistenceConfig())


def test_invalid_release_persistence_config_raises() -> None:
    with pytest.raises(ReleasePersistenceError):
        validate_release_persistence_config(ReleasePersistenceConfig(batch_size=0))


@pytest.mark.parametrize(
    ("builder", "table"),
    [
        (build_release_readiness_run_insert_sql, "governance.release_readiness_runs"),
        (build_release_repository_check_insert_sql, "governance.release_repository_checks"),
        (build_release_documentation_check_insert_sql, "governance.release_documentation_checks"),
        (build_release_artefact_check_insert_sql, "governance.release_artefact_checks"),
        (build_release_evidence_index_insert_sql, "governance.release_evidence_index"),
        (build_release_portfolio_pack_upsert_sql, "governance.release_portfolio_pack"),
    ],
)
def test_release_sql_targets_expected_tables(builder: object, table: str) -> None:
    sql = builder()  # type: ignore[operator]
    assert table in sql
    assert ":" in sql
