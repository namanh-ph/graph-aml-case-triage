"""Static tests for deterministic smoke seed SQL files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "src" / "graph_aml" / "database" / "sql"
SEED_SQL = SQL_DIR / "005_seed_smoke_data.sql"
CLEANUP_SQL = SQL_DIR / "006_delete_smoke_seed_data.sql"

EXPECTED_TABLES = (
    "staging.countries",
    "staging.customers",
    "staging.accounts",
    "staging.counterparties",
    "staging.devices",
    "staging.transactions",
    "mart.features_account_daily",
    "mart.graph_features",
    "aml.alerts",
    "aml.cases",
    "aml.case_alerts",
    "aml.case_entities",
    "governance.audit_events",
    "governance.model_runs",
    "governance.validation_reports",
)

EXPECTED_IDS = (
    "CUST_SMOKE_001",
    "ACC_SMOKE_001",
    "TXN_SMOKE_001",
    "ALERT_SMOKE_001",
    "CASE_SMOKE_001",
    "MODEL_RUN_SMOKE_001",
    "REPORT_SMOKE_001",
)


def seed_sql() -> str:
    return SEED_SQL.read_text(encoding="utf-8")


def cleanup_sql() -> str:
    return CLEANUP_SQL.read_text(encoding="utf-8")


def test_seed_sql_file_exists() -> None:
    assert SEED_SQL.is_file()


def test_cleanup_sql_file_exists() -> None:
    assert CLEANUP_SQL.is_file()


def test_seed_sql_includes_expected_schema_qualified_tables() -> None:
    sql = seed_sql()

    for table_name in EXPECTED_TABLES:
        assert f"INSERT INTO {table_name}" in sql


def test_seed_sql_includes_deterministic_ids() -> None:
    sql = seed_sql()

    for deterministic_id in EXPECTED_IDS:
        assert deterministic_id in sql


def test_seed_sql_contains_on_conflict() -> None:
    assert "ON CONFLICT" in seed_sql()


def test_seed_sql_contains_jsonb_values() -> None:
    sql = seed_sql()

    assert "::jsonb" in sql
    assert '"n_estimators"' in sql
    assert '"records"' in sql
    assert '"purpose"' in sql


def test_cleanup_sql_deletes_in_dependency_safe_order() -> None:
    sql = cleanup_sql()
    expected_order = (
        "DELETE FROM governance.validation_reports",
        "DELETE FROM aml.case_alerts",
        "DELETE FROM aml.case_entities",
        "DELETE FROM aml.cases",
        "DELETE FROM aml.alerts",
        "DELETE FROM mart.account_risk_scores",
        "DELETE FROM mart.account_anomaly_scores",
        "DELETE FROM mart.graph_features",
        "DELETE FROM mart.features_account_daily",
        "DELETE FROM staging.transactions",
        "DELETE FROM staging.devices",
        "DELETE FROM staging.counterparties",
        "DELETE FROM staging.accounts",
        "DELETE FROM staging.customers",
        "DELETE FROM staging.countries",
        "DELETE FROM governance.model_runs",
        "DELETE FROM governance.audit_events",
    )

    positions = [sql.index(statement) for statement in expected_order]
    assert positions == sorted(positions)


def test_cleanup_sql_contains_warning_comment() -> None:
    assert "WARNING" in cleanup_sql()


def test_cleanup_sql_does_not_drop_truncate_or_include_credentials() -> None:
    sql = cleanup_sql().upper()

    assert "DROP" not in sql
    assert "TRUNCATE" not in sql
    assert "PASSWORD" not in sql
    assert "SECRET" not in sql


def test_sql_files_do_not_contain_environment_specific_secrets() -> None:
    combined_sql = f"{seed_sql()}\n{cleanup_sql()}".upper()

    assert "POSTGRES_PASSWORD" not in combined_sql
    assert "NEO4J_PASSWORD" not in combined_sql
    assert "CHANGE_ME" not in combined_sql
