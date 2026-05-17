"""Tests for account risk score persistence preparation and SQL."""

from datetime import date

import pandas as pd
import pytest

from graph_aml.scoring import (
    AccountRiskScorePersistenceConfig,
    ScoringPersistenceError,
    build_account_risk_score_upsert_sql,
    compute_account_risk_scores,
    prepare_account_risk_scores_for_persistence,
)
from tests.test_scoring_composite import components


def scoring_result():
    return compute_account_risk_scores(components(), score_date=date(2026, 5, 7))


def test_default_persistence_config_is_valid() -> None:
    assert AccountRiskScorePersistenceConfig().batch_size == 1000


def test_invalid_persistence_config_raises() -> None:
    with pytest.raises(ScoringPersistenceError):
        AccountRiskScorePersistenceConfig(score_name="")
    with pytest.raises(ScoringPersistenceError):
        AccountRiskScorePersistenceConfig(batch_size=0)


def test_prepared_scores_include_database_columns_and_json() -> None:
    prepared = prepare_account_risk_scores_for_persistence(scoring_result())
    assert {"weights", "metadata", "scored_at"}.issubset(prepared.columns)
    assert len(prepared) == 2


def test_upsert_sql_is_deterministic_and_uses_conflict() -> None:
    sql = build_account_risk_score_upsert_sql()
    assert sql == build_account_risk_score_upsert_sql()
    assert "INSERT INTO mart.account_risk_scores" in sql
    assert ":account_id" in sql
    assert "ON CONFLICT (account_id, score_date, score_name, score_version)" in sql
    assert "created_at = EXCLUDED.created_at" not in sql


def test_input_score_frame_not_mutated() -> None:
    result = scoring_result()
    before = result.scores.copy(deep=True)
    prepare_account_risk_scores_for_persistence(result)
    pd.testing.assert_frame_equal(result.scores, before)
