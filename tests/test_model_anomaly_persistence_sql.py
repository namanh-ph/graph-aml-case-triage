"""Tests for anomaly score upsert SQL generation."""

from graph_aml.models import build_anomaly_score_upsert_sql


def test_anomaly_score_upsert_sql_contains_expected_clauses() -> None:
    sql = build_anomaly_score_upsert_sql()
    assert "INSERT INTO mart.account_anomaly_scores" in sql
    assert ":account_id" in sql
    assert "ON CONFLICT" in sql
    assert "account_id, score_date, model_name, model_version, model_run_id" in sql
    assert "anomaly_score = EXCLUDED.anomaly_score" in sql
    assert "metadata = EXCLUDED.metadata" in sql
    assert "updated_at = CURRENT_TIMESTAMP" in sql
    assert "created_at = EXCLUDED.created_at" not in sql


def test_anomaly_score_upsert_sql_is_deterministic() -> None:
    assert build_anomaly_score_upsert_sql() == build_anomaly_score_upsert_sql()
