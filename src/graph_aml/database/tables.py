"""PostgreSQL table metadata and SQL artefact readers."""

from pathlib import Path

from graph_aml.database.schemas import (
    AML_SCHEMA,
    GOVERNANCE_SCHEMA,
    MART_SCHEMA,
    RAW_SCHEMA,
    STAGING_SCHEMA,
    validate_schema_name,
)

CUSTOMERS_RAW_TABLE = "customers_raw"
ACCOUNTS_RAW_TABLE = "accounts_raw"
TRANSACTIONS_RAW_TABLE = "transactions_raw"
COUNTERPARTIES_RAW_TABLE = "counterparties_raw"
COUNTRIES_RAW_TABLE = "countries_raw"
DEVICES_RAW_TABLE = "devices_raw"

CUSTOMERS_TABLE = "customers"
ACCOUNTS_TABLE = "accounts"
TRANSACTIONS_TABLE = "transactions"
COUNTERPARTIES_TABLE = "counterparties"
COUNTRIES_TABLE = "countries"
DEVICES_TABLE = "devices"

FEATURES_ACCOUNT_DAILY_TABLE = "features_account_daily"
GRAPH_FEATURES_TABLE = "graph_features"
ACCOUNT_ANOMALY_SCORES_TABLE = "account_anomaly_scores"
ACCOUNT_RISK_SCORES_TABLE = "account_risk_scores"

ALERTS_TABLE = "alerts"
CASES_TABLE = "cases"
CASE_ALERTS_TABLE = "case_alerts"
CASE_ENTITIES_TABLE = "case_entities"
CASE_RISK_SCORES_TABLE = "case_risk_scores"
CASE_EVIDENCE_PACKS_TABLE = "case_evidence_packs"
CASE_EXPLANATIONS_TABLE = "case_explanations"
CASE_LIFECYCLE_EVENTS_TABLE = "case_lifecycle_events"
CASE_ASSIGNMENTS_TABLE = "case_assignments"

AUDIT_EVENTS_TABLE = "audit_events"
MODEL_RUNS_TABLE = "model_runs"
VALIDATION_REPORTS_TABLE = "validation_reports"

RAW_TABLES = (
    CUSTOMERS_RAW_TABLE,
    ACCOUNTS_RAW_TABLE,
    TRANSACTIONS_RAW_TABLE,
    COUNTERPARTIES_RAW_TABLE,
    COUNTRIES_RAW_TABLE,
    DEVICES_RAW_TABLE,
)

STAGING_TABLES = (
    COUNTRIES_TABLE,
    CUSTOMERS_TABLE,
    ACCOUNTS_TABLE,
    COUNTERPARTIES_TABLE,
    DEVICES_TABLE,
    TRANSACTIONS_TABLE,
)

MART_TABLES = (
    FEATURES_ACCOUNT_DAILY_TABLE,
    GRAPH_FEATURES_TABLE,
    ACCOUNT_ANOMALY_SCORES_TABLE,
    ACCOUNT_RISK_SCORES_TABLE,
)

AML_TABLES = (
    ALERTS_TABLE,
    CASES_TABLE,
    CASE_ALERTS_TABLE,
    CASE_ENTITIES_TABLE,
    CASE_RISK_SCORES_TABLE,
    CASE_EVIDENCE_PACKS_TABLE,
    CASE_EXPLANATIONS_TABLE,
    CASE_LIFECYCLE_EVENTS_TABLE,
    CASE_ASSIGNMENTS_TABLE,
)

GOVERNANCE_TABLES = (
    AUDIT_EVENTS_TABLE,
    MODEL_RUNS_TABLE,
    VALIDATION_REPORTS_TABLE,
)

POSTGRES_TABLES_BY_SCHEMA = {
    RAW_SCHEMA: RAW_TABLES,
    STAGING_SCHEMA: STAGING_TABLES,
    MART_SCHEMA: MART_TABLES,
    AML_SCHEMA: AML_TABLES,
    GOVERNANCE_SCHEMA: GOVERNANCE_TABLES,
}

TABLE_DESCRIPTIONS = {
    "raw.customers_raw": "Source customer records stored as JSONB payloads before standardisation.",
    "raw.accounts_raw": "Source account records stored as JSONB payloads before standardisation.",
    "raw.transactions_raw": "Source transaction records with traceability columns and raw JSONB.",
    "raw.counterparties_raw": "Source counterparty records stored as JSONB payloads.",
    "raw.countries_raw": "Source country and jurisdiction reference records stored as JSONB.",
    "raw.devices_raw": "Source device and identifier records stored as JSONB payloads.",
    "staging.countries": "Standardised country and jurisdiction risk reference data.",
    "staging.customers": "Standardised customer profiles and customer risk attributes.",
    "staging.accounts": "Standardised account records linked to customers and jurisdictions.",
    "staging.counterparties": "Standardised external counterparties, merchants, and institutions.",
    "staging.devices": "Standardised device, IP, phone, and browser identifier records.",
    "staging.transactions": (
        "Standardised transaction records linked to accounts and evidence entities."
    ),
    "mart.features_account_daily": "Daily account-level behavioural features for rules and models.",
    "mart.graph_features": "Account-level graph analytics features from transaction networks.",
    "mart.account_anomaly_scores": (
        "Account-level Isolation Forest anomaly scores for risk prioritisation."
    ),
    "mart.account_risk_scores": (
        "Composite account-level AML risk scores for downstream case generation."
    ),
    "aml.alerts": "Rule-generated and model-generated AML alerts with evidence references.",
    "aml.cases": "Grouped AML investigation cases with composite risk scores and statuses.",
    "aml.case_alerts": "Bridge table linking alerts to generated investigation cases.",
    "aml.case_entities": "Entities linked to investigation cases with relationship metadata.",
    "aml.case_risk_scores": "Formal case-level composite AML risk scores for triage.",
    "aml.case_evidence_packs": "Structured case evidence packs for deterministic AML review.",
    "aml.case_explanations": "Template-based deterministic explanations for generated AML cases.",
    "aml.case_lifecycle_events": "Append-only analyst lifecycle events for AML cases.",
    "aml.case_assignments": "Current AML case assignment snapshot.",
    "governance.audit_events": "Runtime, pipeline, model, and analyst action audit events.",
    "governance.model_runs": "Model run metadata, parameters, metrics, and artefact references.",
    "governance.validation_reports": "Validation report metadata and links to model runs.",
}

CREATE_TABLES_SQL = "003_create_core_tables.sql"
DROP_TABLES_SQL = "004_drop_core_tables.sql"


def get_tables_for_schema(schema_name: str) -> tuple[str, ...]:
    """Return canonical table names for a PostgreSQL schema."""

    return POSTGRES_TABLES_BY_SCHEMA.get(schema_name, ())


def get_all_table_names() -> tuple[str, ...]:
    """Return all unqualified table names in schema order."""

    return tuple(
        table_name
        for table_names in POSTGRES_TABLES_BY_SCHEMA.values()
        for table_name in table_names
    )


def get_qualified_table_names() -> tuple[str, ...]:
    """Return all fully qualified table names in schema order."""

    return tuple(
        f"{schema_name}.{table_name}"
        for schema_name, table_names in POSTGRES_TABLES_BY_SCHEMA.items()
        for table_name in table_names
    )


def get_table_descriptions() -> dict[str, str]:
    """Return a copy of table descriptions keyed by qualified table name."""

    return dict(TABLE_DESCRIPTIONS)


def validate_table_name(schema_name: str, table_name: str) -> bool:
    """Return whether a table name is canonical for the requested schema."""

    return validate_schema_name(schema_name) and table_name in get_tables_for_schema(schema_name)


def get_table_sql_dir() -> Path:
    """Return the directory containing packaged table SQL files."""

    return Path(__file__).resolve().parent / "sql"


def _read_table_sql(filename: str) -> str:
    path = get_table_sql_dir() / filename
    if not path.is_file():
        raise FileNotFoundError(f"Table SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def read_create_tables_sql() -> str:
    """Return idempotent PostgreSQL core table creation SQL."""

    return _read_table_sql(CREATE_TABLES_SQL)


def read_drop_tables_sql() -> str:
    """Return explicit destructive PostgreSQL core table drop SQL."""

    return _read_table_sql(DROP_TABLES_SQL)
