"""Static tests for anomaly score database table DDL."""

from graph_aml.database.tables import read_create_tables_sql


def test_account_anomaly_scores_table_ddl_exists() -> None:
    sql = read_create_tables_sql()
    assert "CREATE TABLE IF NOT EXISTS mart.account_anomaly_scores" in sql


def test_account_anomaly_scores_contains_required_columns() -> None:
    sql = read_create_tables_sql()
    for column in [
        "account_id TEXT NOT NULL",
        "score_date DATE NOT NULL",
        "model_name TEXT NOT NULL",
        "model_version TEXT NOT NULL",
        "model_run_id TEXT NOT NULL",
        "feature_date DATE",
        "graph_feature_version TEXT",
        "graph_build_id TEXT",
        "anomaly_score DOUBLE PRECISION NOT NULL",
        "anomaly_score_raw DOUBLE PRECISION NOT NULL",
        "anomaly_rank INTEGER NOT NULL",
        "is_anomaly BOOLEAN NOT NULL",
        "risk_band TEXT NOT NULL",
        "feature_names JSONB",
        "model_parameters JSONB",
        "preprocessing_metadata JSONB",
        "created_at TIMESTAMPTZ",
        "updated_at TIMESTAMPTZ",
    ]:
        assert column in sql


def test_account_anomaly_scores_has_primary_key_and_indexes() -> None:
    sql = read_create_tables_sql()
    assert "PRIMARY KEY (account_id, score_date, model_name, model_version, model_run_id)" in sql
    for index_name in [
        "idx_account_anomaly_scores_account_id",
        "idx_account_anomaly_scores_score_date",
        "idx_account_anomaly_scores_model_version",
        "idx_account_anomaly_scores_model_run_id",
        "idx_account_anomaly_scores_anomaly_score",
        "idx_account_anomaly_scores_risk_band",
    ]:
        assert index_name in sql


def test_account_anomaly_scores_ddl_is_non_destructive() -> None:
    section = read_create_tables_sql().split("mart.account_anomaly_scores", maxsplit=1)[1]
    assert "DROP TABLE" not in section.split("CREATE TABLE IF NOT EXISTS aml.alerts", maxsplit=1)[0]
