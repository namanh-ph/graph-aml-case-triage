"""Tests for case risk persistence preparation and SQL."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseRiskPersistenceError,
    CaseRiskScorePersistenceConfig,
    build_case_risk_score_upsert_sql,
    build_case_snapshot_update_sql,
    prepare_case_risk_scores_for_persistence,
)
from tests.fixtures.case_risk import case_risk_score_result


def test_default_persistence_config_is_valid() -> None:
    CaseRiskScorePersistenceConfig()


def test_invalid_persistence_config_raises() -> None:
    with pytest.raises(CaseRiskPersistenceError):
        CaseRiskScorePersistenceConfig(score_name="")
    with pytest.raises(CaseRiskPersistenceError):
        CaseRiskScorePersistenceConfig(batch_size=0)


def test_prepare_scores_for_persistence() -> None:
    prepared = prepare_case_risk_scores_for_persistence(case_risk_score_result())
    assert "weights" in prepared.columns
    assert "metadata" in prepared.columns
    assert "scored_at" in prepared.columns


def test_upsert_and_snapshot_sql() -> None:
    sql = build_case_risk_score_upsert_sql()
    assert "INSERT INTO aml.case_risk_scores" in sql
    assert ":case_id" in sql
    assert "ON CONFLICT" in sql
    assert "created_at = EXCLUDED.created_at" not in sql
    assert "UPDATE aml.cases" in build_case_snapshot_update_sql()


def test_prepare_does_not_mutate_input_scores() -> None:
    result = case_risk_score_result()
    original = result.scores.copy(deep=True)
    prepare_case_risk_scores_for_persistence(result)
    pd.testing.assert_frame_equal(result.scores, original)
