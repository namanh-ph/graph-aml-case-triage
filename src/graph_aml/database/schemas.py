"""PostgreSQL schema metadata and SQL artefact readers."""

from pathlib import Path

RAW_SCHEMA = "raw"
STAGING_SCHEMA = "staging"
MART_SCHEMA = "mart"
AML_SCHEMA = "aml"
GOVERNANCE_SCHEMA = "governance"

POSTGRES_SCHEMAS = (
    RAW_SCHEMA,
    STAGING_SCHEMA,
    MART_SCHEMA,
    AML_SCHEMA,
    GOVERNANCE_SCHEMA,
)

SCHEMA_DESCRIPTIONS = {
    "raw": "Unmodified source data loaded from reference or external AML datasets.",
    "staging": "Cleaned, standardised, and relationally consistent operational tables.",
    "mart": "Feature tables and analytics-ready outputs for rules, graph features, and models.",
    "aml": "AML alerts, cases, case links, typology outputs, and investigation workflow records.",
    "governance": (
        "Audit events, model runs, validation reports, lineage, and reproducibility artefacts."
    ),
}

CREATE_SCHEMAS_SQL = "001_create_schemas.sql"
DROP_SCHEMAS_SQL = "002_drop_schemas.sql"


def get_postgres_schemas() -> tuple[str, ...]:
    """Return PostgreSQL schemas in canonical creation order."""

    return POSTGRES_SCHEMAS


def get_schema_descriptions() -> dict[str, str]:
    """Return a copy of PostgreSQL schema descriptions."""

    return dict(SCHEMA_DESCRIPTIONS)


def validate_schema_name(schema_name: str) -> bool:
    """Return whether a schema name is canonical for this project."""

    return schema_name in POSTGRES_SCHEMAS


def get_schema_sql_dir() -> Path:
    """Return the directory containing packaged schema SQL files."""

    return Path(__file__).resolve().parent / "sql"


def _read_schema_sql(filename: str) -> str:
    path = get_schema_sql_dir() / filename
    if not path.is_file():
        raise FileNotFoundError(f"Schema SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def read_create_schemas_sql() -> str:
    """Return idempotent PostgreSQL schema creation SQL."""

    return _read_schema_sql(CREATE_SCHEMAS_SQL)


def read_drop_schemas_sql() -> str:
    """Return explicit destructive PostgreSQL schema drop SQL."""

    return _read_schema_sql(DROP_SCHEMAS_SQL)
