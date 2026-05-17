"""Static tests for mart.graph_features DDL."""

from graph_aml.database.tables import read_create_tables_sql


def test_graph_features_table_ddl_exists() -> None:
    assert "CREATE TABLE IF NOT EXISTS mart.graph_features" in read_create_tables_sql()


def test_graph_features_table_contains_primary_key_columns() -> None:
    sql = read_create_tables_sql()

    for column in ("account_id", "feature_date", "feature_version", "graph_build_id"):
        assert column in sql


def test_graph_features_table_contains_graph_analytics_feature_columns() -> None:
    sql = read_create_tables_sql()

    for column in (
        "degree DOUBLE PRECISION",
        "pagerank_score DOUBLE PRECISION",
        "betweenness_centrality DOUBLE PRECISION",
        "community_id INTEGER",
        "cycle_count INTEGER",
        "fan_in_count INTEGER",
        "fan_out_count INTEGER",
        "high_risk_alert_count INTEGER",
        "total_sent_amount DOUBLE PRECISION",
    ):
        assert column in sql


def test_graph_features_table_contains_metadata_and_timestamps() -> None:
    sql = read_create_tables_sql()

    for column in (
        "graph_database TEXT",
        "computed_at TIMESTAMPTZ NOT NULL",
        "metadata JSONB NOT NULL",
        "created_at TIMESTAMPTZ NOT NULL",
        "updated_at TIMESTAMPTZ NOT NULL",
    ):
        assert column in sql


def test_graph_features_table_has_composite_primary_key_and_indexes() -> None:
    sql = read_create_tables_sql()

    assert "PRIMARY KEY (account_id, feature_date, feature_version, graph_build_id)" in sql
    for index_name in (
        "idx_graph_features_account_id",
        "idx_graph_features_feature_date",
        "idx_graph_features_feature_version",
        "idx_graph_features_graph_build_id",
        "idx_graph_features_pagerank_score",
        "idx_graph_features_high_risk_alert_count",
    ):
        assert index_name in sql


def test_graph_features_ddl_is_non_destructive() -> None:
    graph_section = (
        read_create_tables_sql()
        .split(
            "CREATE TABLE IF NOT EXISTS mart.graph_features",
            maxsplit=1,
        )[1]
        .split("CREATE TABLE IF NOT EXISTS aml.alerts", maxsplit=1)[0]
    )

    assert "DROP TABLE" not in graph_section
    assert "DELETE FROM" not in graph_section
