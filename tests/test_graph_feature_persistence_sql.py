"""Tests for graph feature upsert SQL generation."""

from graph_aml.graph import build_graph_feature_upsert_sql


def test_graph_feature_upsert_sql_targets_mart_table() -> None:
    assert "INSERT INTO mart.graph_features" in build_graph_feature_upsert_sql()


def test_graph_feature_upsert_sql_uses_named_parameters() -> None:
    sql = build_graph_feature_upsert_sql()

    assert ":account_id" in sql
    assert ":pagerank_score" in sql
    assert "CAST(:metadata AS JSONB)" in sql


def test_graph_feature_upsert_sql_uses_primary_key_conflict_columns() -> None:
    sql = build_graph_feature_upsert_sql()

    assert "ON CONFLICT (account_id, feature_date, feature_version, graph_build_id)" in sql


def test_graph_feature_upsert_sql_updates_features_metadata_and_updated_at() -> None:
    sql = build_graph_feature_upsert_sql()

    assert "pagerank_score = EXCLUDED.pagerank_score" in sql
    assert "metadata = EXCLUDED.metadata" in sql
    assert "updated_at = CURRENT_TIMESTAMP" in sql


def test_graph_feature_upsert_sql_does_not_overwrite_created_at() -> None:
    update_clause = build_graph_feature_upsert_sql().split("DO UPDATE SET", maxsplit=1)[1]

    assert "created_at" not in update_clause


def test_graph_feature_upsert_sql_is_deterministic() -> None:
    assert build_graph_feature_upsert_sql() == build_graph_feature_upsert_sql()
