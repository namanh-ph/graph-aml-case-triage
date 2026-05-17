"""Static tests for account risk score database DDL."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATE_SQL = ROOT / "src" / "graph_aml" / "database" / "sql" / "003_create_core_tables.sql"


def ddl() -> str:
    return CREATE_SQL.read_text(encoding="utf-8")


def test_account_risk_scores_table_exists() -> None:
    assert "CREATE TABLE IF NOT EXISTS mart.account_risk_scores" in ddl()


def test_account_risk_scores_contains_key_component_and_metadata_columns() -> None:
    sql = ddl()
    for column in (
        "account_id",
        "score_date",
        "score_name",
        "score_version",
        "account_risk_score",
        "risk_band",
        "risk_rank",
        "rule_risk_score",
        "graph_risk_score",
        "anomaly_risk_score",
        "customer_risk_score",
        "jurisdiction_risk_score",
        "weights JSONB",
        "metadata JSONB",
        "created_at",
        "updated_at",
    ):
        assert column in sql


def test_account_risk_scores_primary_key_and_indexes_exist() -> None:
    sql = ddl()
    assert "PRIMARY KEY (account_id, score_date, score_name, score_version)" in sql
    assert "idx_account_risk_scores_account_id" in sql
    assert "idx_account_risk_scores_risk_score" in sql
    assert "idx_account_risk_scores_risk_band" in sql


def test_account_risk_scores_ddl_is_non_destructive() -> None:
    section = ddl().split("CREATE TABLE IF NOT EXISTS mart.account_risk_scores", maxsplit=1)[1]
    section = section.split("CREATE TABLE IF NOT EXISTS aml.alerts", maxsplit=1)[0]
    assert "DROP TABLE" not in section
    assert "TRUNCATE" not in section
