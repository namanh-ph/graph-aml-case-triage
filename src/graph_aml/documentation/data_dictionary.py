"""Data dictionary models, catalogue, serialisation, and writers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from graph_aml.config import load_app_config
from graph_aml.database.schemas import get_schema_descriptions
from graph_aml.database.tables import get_qualified_table_names, get_table_descriptions
from graph_aml.documentation.exceptions import DataDictionaryError, DocumentationWriteError

DATA_DICTIONARY_VERSION = "1.0"

LIFECYCLE_STAGE_BY_SCHEMA = {
    "raw": "Raw source capture",
    "staging": "Cleaned and standardised relational data",
    "mart": "Analytics-ready feature data",
    "aml": "AML alert, case, and investigation workflow data",
    "governance": "Audit, model run, validation, and lineage artefacts",
}


@dataclass(frozen=True)
class ColumnDefinition:
    column_name: str
    data_type: str
    nullable: bool
    primary_key: bool = False
    foreign_key: str | None = None
    description: str = ""
    business_meaning: str = ""
    validation_rules: tuple[str, ...] = ()
    example_value: str | None = None
    lineage_source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TableDefinition:
    schema_name: str
    table_name: str
    qualified_name: str
    description: str
    lifecycle_stage: str
    primary_key: tuple[str, ...]
    foreign_keys: tuple[str, ...] = ()
    columns: tuple[ColumnDefinition, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DataDictionary:
    project_name: str
    generated_at: str
    version: str
    tables: tuple[TableDefinition, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


ColumnSpec = tuple[str, str, bool, bool, str | None, tuple[str, ...], str | None, str | None]


def _spec(
    name: str,
    data_type: str,
    nullable: bool,
    *,
    primary_key: bool = False,
    foreign_key: str | None = None,
    validation_rules: tuple[str, ...] = (),
    example: str | None = None,
    lineage_source: str | None = None,
) -> ColumnSpec:
    return (
        name,
        data_type,
        nullable,
        primary_key,
        foreign_key,
        validation_rules,
        example,
        lineage_source,
    )


COMMON_RAW_COLUMNS: tuple[ColumnSpec, ...] = (
    _spec("raw_record_id", "BIGSERIAL", False, primary_key=True, example="1"),
    _spec("source_system", "TEXT", True, example="reference"),
    _spec("source_file", "TEXT", True, example="transactions.csv"),
    _spec("ingested_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    _spec(
        "raw_payload",
        "JSONB",
        False,
        validation_rules=("Must contain the original source record as a JSON object.",),
        example='{"transaction_id": "TXN_001"}',
    ),
    _spec("record_hash", "TEXT", True, example="sha256:..."),
)


COLUMN_CATALOGUE: dict[str, tuple[ColumnSpec, ...]] = {
    "raw.customers_raw": COMMON_RAW_COLUMNS,
    "raw.accounts_raw": COMMON_RAW_COLUMNS,
    "raw.counterparties_raw": COMMON_RAW_COLUMNS,
    "raw.countries_raw": COMMON_RAW_COLUMNS,
    "raw.devices_raw": COMMON_RAW_COLUMNS,
    "raw.transactions_raw": (
        *COMMON_RAW_COLUMNS,
        _spec("transaction_id", "TEXT", True, example="TXN_001", lineage_source="raw_payload"),
        _spec("sender_account_id", "TEXT", True, example="ACC_001", lineage_source="raw_payload"),
        _spec("receiver_account_id", "TEXT", True, example="ACC_002", lineage_source="raw_payload"),
        _spec(
            "transaction_timestamp",
            "TIMESTAMPTZ",
            True,
            example="2025-01-01T12:00:00Z",
            lineage_source="raw_payload",
        ),
        _spec("amount", "NUMERIC(18, 2)", True, example="125.50", lineage_source="raw_payload"),
        _spec("currency", "TEXT", True, example="USD", lineage_source="raw_payload"),
    ),
    "staging.countries": (
        _spec(
            "country_code",
            "TEXT",
            False,
            primary_key=True,
            example="AU",
            lineage_source="raw.countries_raw.raw_payload",
        ),
        _spec(
            "country_name",
            "TEXT",
            False,
            example="Australia",
            lineage_source="raw.countries_raw.raw_payload",
        ),
        _spec(
            "region", "TEXT", True, example="APAC", lineage_source="raw.countries_raw.raw_payload"
        ),
        _spec(
            "is_high_risk",
            "BOOLEAN",
            False,
            validation_rules=("Defaults to false.",),
            example="false",
            lineage_source="raw.countries_raw.raw_payload",
        ),
        _spec(
            "risk_score",
            "NUMERIC(5, 2)",
            False,
            validation_rules=("Must be between 0 and 100.",),
            example="25.00",
            lineage_source="raw.countries_raw.raw_payload",
        ),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "staging.customers": (
        _spec(
            "customer_id",
            "TEXT",
            False,
            primary_key=True,
            example="CUST_001",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec(
            "customer_type",
            "TEXT",
            False,
            validation_rules=("Lowercase standardised type.",),
            example="individual",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec(
            "customer_segment",
            "TEXT",
            True,
            example="retail",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec(
            "jurisdiction",
            "TEXT",
            True,
            foreign_key="staging.countries(country_code)",
            example="AU",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec(
            "occupation",
            "TEXT",
            True,
            example="engineer",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec(
            "industry_code",
            "TEXT",
            True,
            example="5411",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec(
            "customer_risk_rating",
            "TEXT",
            True,
            validation_rules=("Defaults to low when missing.",),
            example="medium",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec(
            "customer_risk_score",
            "NUMERIC(5, 2)",
            False,
            validation_rules=("Must be between 0 and 100.",),
            example="42.00",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec(
            "onboarded_at",
            "TIMESTAMPTZ",
            True,
            validation_rules=("Parsed as timestamp when supplied.",),
            example="2024-12-01T00:00:00Z",
            lineage_source="raw.customers_raw.raw_payload",
        ),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "staging.accounts": (
        _spec(
            "account_id",
            "TEXT",
            False,
            primary_key=True,
            example="ACC_001",
            lineage_source="raw.accounts_raw.raw_payload",
        ),
        _spec(
            "customer_id",
            "TEXT",
            False,
            foreign_key="staging.customers(customer_id)",
            example="CUST_001",
            lineage_source="raw.accounts_raw.raw_payload",
        ),
        _spec(
            "account_type",
            "TEXT",
            False,
            example="current",
            lineage_source="raw.accounts_raw.raw_payload",
        ),
        _spec(
            "account_status",
            "TEXT",
            False,
            validation_rules=("Defaults to active when missing.",),
            example="active",
            lineage_source="raw.accounts_raw.raw_payload",
        ),
        _spec(
            "currency",
            "TEXT",
            False,
            validation_rules=("Uppercase ISO-like currency code.",),
            example="USD",
            lineage_source="raw.accounts_raw.raw_payload",
        ),
        _spec(
            "opened_at",
            "TIMESTAMPTZ",
            True,
            validation_rules=("Parsed as timestamp when supplied.",),
            example="2024-01-01T00:00:00Z",
            lineage_source="raw.accounts_raw.raw_payload",
        ),
        _spec(
            "closed_at",
            "TIMESTAMPTZ",
            True,
            example="2025-01-01T00:00:00Z",
            lineage_source="raw.accounts_raw.raw_payload",
        ),
        _spec(
            "home_country",
            "TEXT",
            True,
            foreign_key="staging.countries(country_code)",
            example="AU",
            lineage_source="raw.accounts_raw.raw_payload",
        ),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "staging.counterparties": (
        _spec(
            "counterparty_id",
            "TEXT",
            False,
            primary_key=True,
            example="CP_001",
            lineage_source="raw.counterparties_raw.raw_payload",
        ),
        _spec(
            "counterparty_type",
            "TEXT",
            False,
            example="merchant",
            lineage_source="raw.counterparties_raw.raw_payload",
        ),
        _spec(
            "counterparty_name",
            "TEXT",
            True,
            example="Example Merchant",
            lineage_source="raw.counterparties_raw.raw_payload",
        ),
        _spec(
            "country_code",
            "TEXT",
            True,
            foreign_key="staging.countries(country_code)",
            example="NZ",
            lineage_source="raw.counterparties_raw.raw_payload",
        ),
        _spec(
            "institution_name",
            "TEXT",
            True,
            example="Example Bank",
            lineage_source="raw.counterparties_raw.raw_payload",
        ),
        _spec(
            "external_account_ref",
            "TEXT",
            True,
            example="EXT-001",
            lineage_source="raw.counterparties_raw.raw_payload",
        ),
        _spec(
            "risk_score",
            "NUMERIC(5, 2)",
            False,
            validation_rules=("Must be between 0 and 100.",),
            example="35.00",
            lineage_source="raw.counterparties_raw.raw_payload",
        ),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "staging.devices": (
        _spec(
            "device_id",
            "TEXT",
            False,
            primary_key=True,
            example="DEV_001",
            lineage_source="raw.devices_raw.raw_payload",
        ),
        _spec(
            "device_type",
            "TEXT",
            True,
            example="mobile",
            lineage_source="raw.devices_raw.raw_payload",
        ),
        _spec(
            "ip_address",
            "TEXT",
            True,
            example="203.0.113.10",
            lineage_source="raw.devices_raw.raw_payload",
        ),
        _spec(
            "ip_cluster",
            "TEXT",
            True,
            example="203.0.113.0/24",
            lineage_source="raw.devices_raw.raw_payload",
        ),
        _spec(
            "phone_hash",
            "TEXT",
            True,
            example="hash-phone",
            lineage_source="raw.devices_raw.raw_payload",
        ),
        _spec(
            "browser_fingerprint",
            "TEXT",
            True,
            example="browser-hash",
            lineage_source="raw.devices_raw.raw_payload",
        ),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "staging.transactions": (
        _spec(
            "transaction_id",
            "TEXT",
            False,
            primary_key=True,
            example="TXN_001",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "sender_account_id",
            "TEXT",
            False,
            foreign_key="staging.accounts(account_id)",
            example="ACC_001",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "receiver_account_id",
            "TEXT",
            True,
            foreign_key="staging.accounts(account_id)",
            example="ACC_002",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "counterparty_id",
            "TEXT",
            True,
            foreign_key="staging.counterparties(counterparty_id)",
            example="CP_001",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "device_id",
            "TEXT",
            True,
            foreign_key="staging.devices(device_id)",
            example="DEV_001",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "transaction_timestamp",
            "TIMESTAMPTZ",
            False,
            validation_rules=("Parsed timestamp; must be populated.",),
            example="2025-01-01T12:00:00Z",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "amount",
            "NUMERIC(18, 2)",
            False,
            validation_rules=("Must be greater than 0.",),
            example="125.50",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "currency",
            "TEXT",
            False,
            validation_rules=("Uppercase currency code; defaults to USD.",),
            example="USD",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "transaction_type",
            "TEXT",
            False,
            example="transfer",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "channel",
            "TEXT",
            True,
            example="online",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "origin_country",
            "TEXT",
            True,
            foreign_key="staging.countries(country_code)",
            example="AU",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "destination_country",
            "TEXT",
            True,
            foreign_key="staging.countries(country_code)",
            example="NZ",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "is_cross_border",
            "BOOLEAN",
            False,
            validation_rules=("Recalculated as origin_country != destination_country.",),
            example="true",
            lineage_source="derived from staging.transactions origin and destination",
        ),
        _spec(
            "is_labelled_suspicious",
            "BOOLEAN",
            True,
            validation_rules=("Labelled scenario label when supplied.",),
            example="false",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "typology_label",
            "TEXT",
            True,
            example="structuring",
            lineage_source="raw.transactions_raw.raw_payload",
        ),
        _spec(
            "source_file",
            "TEXT",
            True,
            example="transactions.csv",
            lineage_source="raw.transactions_raw.source_file or raw_payload",
        ),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "mart.features_account_daily": (
        _spec("feature_id", "BIGSERIAL", False, primary_key=True, example="1"),
        _spec(
            "account_id",
            "TEXT",
            False,
            foreign_key="staging.accounts(account_id)",
            example="ACC_001",
        ),
        _spec("feature_date", "DATE", False, example="2025-01-01"),
        _spec(
            "feature_version",
            "TEXT",
            False,
            validation_rules=("Unique with account_id and feature_date.",),
            example="features_v1",
        ),
        _spec("txn_count_1d", "INTEGER", False, example="3"),
        _spec("txn_count_7d", "INTEGER", False, example="12"),
        _spec("total_sent_7d", "NUMERIC(18, 2)", False, example="1500.00"),
        _spec("total_received_7d", "NUMERIC(18, 2)", False, example="900.00"),
        _spec("avg_txn_amount_30d", "NUMERIC(18, 2)", False, example="125.00"),
        _spec("max_txn_amount_30d", "NUMERIC(18, 2)", False, example="999.00"),
        _spec("unique_counterparties_7d", "INTEGER", False, example="5"),
        _spec("in_out_ratio_7d", "NUMERIC(18, 6)", True, example="1.250000"),
        _spec("retained_balance_proxy", "NUMERIC(18, 2)", True, example="600.00"),
        _spec("below_threshold_count_24h", "INTEGER", False, example="4"),
        _spec("dormant_days_before_activity", "INTEGER", True, example="120"),
        _spec("cross_border_ratio_30d", "NUMERIC(10, 6)", True, example="0.150000"),
        _spec("high_risk_country_exposure", "NUMERIC(10, 6)", True, example="0.050000"),
        _spec("counterparty_entropy", "NUMERIC(10, 6)", True, example="1.500000"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "mart.graph_features": (
        _spec("graph_feature_id", "BIGSERIAL", False, primary_key=True, example="1"),
        _spec(
            "account_id",
            "TEXT",
            False,
            foreign_key="staging.accounts(account_id)",
            example="ACC_001",
        ),
        _spec(
            "graph_build_version",
            "TEXT",
            False,
            validation_rules=("Unique with account_id and feature_date.",),
            example="graph_v1",
        ),
        _spec("feature_date", "DATE", False, example="2025-01-01"),
        _spec("degree_centrality", "NUMERIC(18, 10)", True, example="0.1200000000"),
        _spec("in_degree", "INTEGER", True, example="5"),
        _spec("out_degree", "INTEGER", True, example="4"),
        _spec("pagerank_score", "NUMERIC(18, 10)", True, example="0.0012000000"),
        _spec("betweenness_centrality", "NUMERIC(18, 10)", True, example="0.0300000000"),
        _spec("clustering_coefficient", "NUMERIC(18, 10)", True, example="0.5000000000"),
        _spec("community_id", "TEXT", True, example="COMM_001"),
        _spec("community_size", "INTEGER", True, example="10"),
        _spec("cycle_count", "INTEGER", False, example="1"),
        _spec("shortest_path_to_flagged", "INTEGER", True, example="2"),
        _spec("shared_device_count", "INTEGER", False, example="3"),
        _spec("fan_in_count", "INTEGER", False, example="4"),
        _spec("fan_out_count", "INTEGER", False, example="5"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "mart.account_anomaly_scores": (
        _spec(
            "account_id",
            "TEXT",
            False,
            primary_key=True,
            foreign_key="staging.accounts(account_id)",
            example="ACC_001",
        ),
        _spec("score_date", "DATE", False, primary_key=True, example="2025-01-01"),
        _spec(
            "model_name",
            "TEXT",
            False,
            primary_key=True,
            example="account_isolation_forest",
        ),
        _spec(
            "model_version",
            "TEXT",
            False,
            primary_key=True,
            example="isolation_forest_v1",
        ),
        _spec(
            "model_run_id",
            "TEXT",
            False,
            primary_key=True,
            example="account_isolation_forest_isolation_forest_v1_2025_01_01",
        ),
        _spec("feature_date", "DATE", True, example="2025-01-01"),
        _spec("account_feature_version", "TEXT", True, example="features_v1"),
        _spec("graph_feature_version", "TEXT", True, example="graph_features_v1"),
        _spec("graph_build_id", "TEXT", True, example="graph_features_v1_2025_01_01_neo4j"),
        _spec(
            "anomaly_score",
            "DOUBLE PRECISION",
            False,
            validation_rules=("Must be between 0 and 100.",),
            example="97.5",
        ),
        _spec("anomaly_score_raw", "DOUBLE PRECISION", False, example="-0.142"),
        _spec("anomaly_rank", "INTEGER", False, example="1"),
        _spec("is_anomaly", "BOOLEAN", False, example="true"),
        _spec(
            "risk_band",
            "TEXT",
            False,
            validation_rules=("Must be low, medium, or high.",),
            example="high",
        ),
        _spec("feature_names", "JSONB", False, example='["txn_count_7d","pagerank_score"]'),
        _spec("model_parameters", "JSONB", False, example='{"n_estimators":200}'),
        _spec("preprocessing_metadata", "JSONB", False, example='{"imputation_values":{}}'),
        _spec("metrics", "JSONB", False, example='{"feature_count":21}'),
        _spec("metadata", "JSONB", False, example='{"score_summary":{}}'),
        _spec("scored_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "mart.account_risk_scores": (
        _spec(
            "account_id",
            "TEXT",
            False,
            primary_key=True,
            foreign_key="staging.accounts(account_id)",
            example="ACC_001",
        ),
        _spec("score_date", "DATE", False, primary_key=True, example="2025-01-01"),
        _spec(
            "score_name",
            "TEXT",
            False,
            primary_key=True,
            example="composite_account_risk",
        ),
        _spec(
            "score_version",
            "TEXT",
            False,
            primary_key=True,
            example="composite_account_risk_v1",
        ),
        _spec(
            "account_risk_score",
            "DOUBLE PRECISION",
            False,
            validation_rules=("Must be between 0 and 100.",),
            example="88.5",
        ),
        _spec(
            "risk_band",
            "TEXT",
            False,
            validation_rules=("Must be low, medium, high, or critical.",),
            example="high",
        ),
        _spec("risk_rank", "INTEGER", False, example="1"),
        _spec("rule_risk_score", "DOUBLE PRECISION", False, example="85.0"),
        _spec("graph_risk_score", "DOUBLE PRECISION", False, example="70.0"),
        _spec("anomaly_risk_score", "DOUBLE PRECISION", False, example="95.0"),
        _spec("customer_risk_score", "DOUBLE PRECISION", False, example="50.0"),
        _spec("jurisdiction_risk_score", "DOUBLE PRECISION", False, example="30.0"),
        _spec("component_coverage", "DOUBLE PRECISION", False, example="0.8"),
        _spec("alert_count", "INTEGER", False, example="2"),
        _spec("high_severity_alert_count", "INTEGER", False, example="1"),
        _spec("critical_severity_alert_count", "INTEGER", False, example="0"),
        _spec("max_rule_alert_score", "DOUBLE PRECISION", False, example="85.0"),
        _spec("mean_rule_alert_score", "DOUBLE PRECISION", False, example="72.5"),
        _spec("max_anomaly_score", "DOUBLE PRECISION", False, example="95.0"),
        _spec("graph_percentile_score", "DOUBLE PRECISION", False, example="75.0"),
        _spec("weights", "JSONB", False, example='{"rule_risk_score":0.35}'),
        _spec("metadata", "JSONB", False, example='{"score_summary":{}}'),
        _spec("scored_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.case_risk_scores": (
        _spec(
            "case_id",
            "TEXT",
            False,
            primary_key=True,
            foreign_key="aml.cases(case_id)",
            example="CASE_001",
        ),
        _spec("score_date", "DATE", False, primary_key=True, example="2025-01-01"),
        _spec("score_name", "TEXT", False, primary_key=True, example="composite_case_risk"),
        _spec("score_version", "TEXT", False, primary_key=True, example="composite_case_risk_v1"),
        _spec(
            "case_risk_score",
            "DOUBLE PRECISION",
            False,
            validation_rules=("Must be between 0 and 100.",),
            example="91.5",
        ),
        _spec(
            "risk_band",
            "TEXT",
            False,
            validation_rules=("Must be low, medium, high, or critical.",),
            example="critical",
        ),
        _spec("risk_rank", "INTEGER", False, example="1"),
        _spec("alert_risk_score", "DOUBLE PRECISION", False, example="85.0"),
        _spec("account_risk_score", "DOUBLE PRECISION", False, example="88.0"),
        _spec("graph_risk_score", "DOUBLE PRECISION", False, example="72.0"),
        _spec("anomaly_risk_score", "DOUBLE PRECISION", False, example="94.0"),
        _spec("typology_diversity_score", "DOUBLE PRECISION", False, example="50.0"),
        _spec("evidence_value_score", "DOUBLE PRECISION", False, example="80.0"),
        _spec("component_coverage", "DOUBLE PRECISION", False, example="0.83"),
        _spec("alert_count", "INTEGER", False, example="3"),
        _spec("typology_count", "INTEGER", False, example="2"),
        _spec("related_account_count", "INTEGER", False, example="2"),
        _spec("evidence_transaction_count", "INTEGER", False, example="5"),
        _spec("total_transaction_value", "DOUBLE PRECISION", False, example="25000.0"),
        _spec("max_alert_score", "DOUBLE PRECISION", False, example="90.0"),
        _spec("max_account_risk_score", "DOUBLE PRECISION", False, example="88.0"),
        _spec("max_anomaly_score", "DOUBLE PRECISION", False, example="94.0"),
        _spec("weights", "JSONB", False, example='{"alert_risk_score":0.25}'),
        _spec("metadata", "JSONB", False, example='{"score_summary":{}}'),
        _spec("scored_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.case_evidence_packs": (
        _spec(
            "case_id",
            "TEXT",
            False,
            primary_key=True,
            foreign_key="aml.cases(case_id)",
            example="CASE_001",
        ),
        _spec("evidence_version", "TEXT", False, primary_key=True, example="case_evidence_v1"),
        _spec("case_summary", "JSONB", False, example='{"case_id":"CASE_001"}'),
        _spec("typology_evidence", "JSONB", False, example='{"typologies":["structuring"]}'),
        _spec("alert_evidence", "JSONB", False, example='{"alert_count":2}'),
        _spec("transaction_evidence", "JSONB", False, example='{"total_value":1000}'),
        _spec("account_evidence", "JSONB", False, example='{"accounts":[]}'),
        _spec("graph_evidence", "JSONB", False, example='{"accounts":[]}'),
        _spec("risk_driver_evidence", "JSONB", False, example='{"risk_drivers":[]}'),
        _spec("chronology", "JSONB", False, example='[]'),
        _spec("recommended_review_focus", "JSONB", False, example='["Review alerts"]'),
        _spec("evidence_quality", "JSONB", False, example='{"has_alerts":true}'),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.case_explanations": (
        _spec(
            "case_id",
            "TEXT",
            False,
            primary_key=True,
            foreign_key="aml.cases(case_id)",
            example="CASE_001",
        ),
        _spec(
            "explanation_version",
            "TEXT",
            False,
            primary_key=True,
            example="deterministic_explanation_v1",
        ),
        _spec("explanation_text", "TEXT", False, example="Case CASE_001 has high risk."),
        _spec("explanation_bullets", "JSONB", False, example='["Review high-value transactions"]'),
        _spec("risk_driver_summary", "TEXT", True, example="Top risk drivers: alert risk."),
        _spec("typology_summary", "TEXT", True, example="Triggered typologies: structuring."),
        _spec("transaction_summary", "TEXT", True, example="Evidence includes 2 transactions."),
        _spec("graph_summary", "TEXT", True, example="Graph context covers 1 account."),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.case_lifecycle_events": (
        _spec("action_id", "TEXT", False, primary_key=True, example="CASE_ACTION_ABC"),
        _spec("case_id", "TEXT", False, foreign_key="aml.cases(case_id)", example="CASE_001"),
        _spec("action_type", "TEXT", False, example="status_change"),
        _spec("analyst_id", "TEXT", False, example="analyst_001"),
        _spec("from_status", "TEXT", True, example="New"),
        _spec("to_status", "TEXT", True, example="In review"),
        _spec("assigned_to", "TEXT", True, example="analyst_001"),
        _spec("queue", "TEXT", True, example="AML Review"),
        _spec("decision_reason", "TEXT", True, example="Start review"),
        _spec("comment", "TEXT", True, example="Reviewed initial evidence"),
        _spec("metadata", "JSONB", False, example='{"lifecycle_version":"case_lifecycle_v1"}'),
        _spec("action_timestamp", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.case_assignments": (
        _spec("case_id", "TEXT", False, primary_key=True, example="CASE_001"),
        _spec("assigned_to", "TEXT", True, example="analyst_001"),
        _spec("queue", "TEXT", True, example="AML Review"),
        _spec("assigned_by", "TEXT", True, example="lead_analyst"),
        _spec("assigned_at", "TIMESTAMPTZ", True, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.alerts": (
        _spec("alert_id", "TEXT", False, primary_key=True, example="ALERT_001"),
        _spec(
            "account_id",
            "TEXT",
            False,
            foreign_key="staging.accounts(account_id)",
            example="ACC_001",
        ),
        _spec(
            "customer_id",
            "TEXT",
            True,
            foreign_key="staging.customers(customer_id)",
            example="CUST_001",
        ),
        _spec("rule_name", "TEXT", False, example="Structuring"),
        _spec("typology", "TEXT", False, example="structuring"),
        _spec(
            "severity",
            "TEXT",
            False,
            validation_rules=("Must be low, medium, high, or critical.",),
            example="high",
        ),
        _spec(
            "risk_score_rule",
            "NUMERIC(5, 2)",
            False,
            validation_rules=("Must be between 0 and 100.",),
            example="85.00",
        ),
        _spec("reason_code", "TEXT", False, example="STRUCTURING_BELOW_THRESHOLD"),
        _spec("evidence_ids", "TEXT[]", False, example="{TXN_001,TXN_002}"),
        _spec("detection_window_start", "TIMESTAMPTZ", True, example="2025-01-01T00:00:00Z"),
        _spec("detection_window_end", "TIMESTAMPTZ", True, example="2025-01-02T00:00:00Z"),
        _spec("model_run_id", "TEXT", True, example="MODEL_RUN_001"),
        _spec("alert_status", "TEXT", False, example="New"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.cases": (
        _spec("case_id", "TEXT", False, primary_key=True, example="CASE_001"),
        _spec(
            "primary_account_id",
            "TEXT",
            True,
            foreign_key="staging.accounts(account_id)",
            example="ACC_001",
        ),
        _spec(
            "primary_customer_id",
            "TEXT",
            True,
            foreign_key="staging.customers(customer_id)",
            example="CUST_001",
        ),
        _spec("typologies", "TEXT[]", False, example="{structuring,fan_in}"),
        _spec("total_transaction_value", "NUMERIC(18, 2)", False, example="12500.00"),
        _spec("rule_typology_score", "NUMERIC(5, 2)", False, example="80.00"),
        _spec("graph_risk_score", "NUMERIC(5, 2)", False, example="70.00"),
        _spec("anomaly_score", "NUMERIC(5, 2)", False, example="65.00"),
        _spec("customer_risk_score", "NUMERIC(5, 2)", False, example="55.00"),
        _spec("jurisdiction_risk_score", "NUMERIC(5, 2)", False, example="40.00"),
        _spec(
            "case_risk_score",
            "NUMERIC(5, 2)",
            False,
            validation_rules=("Must be between 0 and 100.",),
            example="82.00",
        ),
        _spec("case_risk_band", "TEXT", True, example="high"),
        _spec("case_risk_rank", "INTEGER", True, example="1"),
        _spec(
            "severity",
            "TEXT",
            False,
            validation_rules=("Must be low, medium, high, or critical.",),
            example="high",
        ),
        _spec(
            "status",
            "TEXT",
            False,
            validation_rules=("Must be a recognised case workflow status.",),
            example="New",
        ),
        _spec("explanation", "TEXT", True, example="Multiple typology signals on account."),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("updated_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.case_alerts": (
        _spec(
            "case_id",
            "TEXT",
            False,
            primary_key=True,
            foreign_key="aml.cases(case_id)",
            example="CASE_001",
        ),
        _spec(
            "alert_id",
            "TEXT",
            False,
            primary_key=True,
            foreign_key="aml.alerts(alert_id)",
            example="ALERT_001",
        ),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "aml.case_entities": (
        _spec("case_entity_id", "BIGSERIAL", False, primary_key=True, example="1"),
        _spec("case_id", "TEXT", False, foreign_key="aml.cases(case_id)", example="CASE_001"),
        _spec("entity_type", "TEXT", False, example="account"),
        _spec("entity_id", "TEXT", False, example="ACC_001"),
        _spec("relationship_type", "TEXT", True, example="primary_subject"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "governance.audit_events": (
        _spec("audit_event_id", "BIGSERIAL", False, primary_key=True, example="1"),
        _spec("event_timestamp", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
        _spec("event_type", "TEXT", False, example="raw_ingestion"),
        _spec("component", "TEXT", False, example="ingestion"),
        _spec("run_id", "TEXT", True, example="RUN_001"),
        _spec("pipeline_stage", "TEXT", True, example="raw_load"),
        _spec("entity_type", "TEXT", True, example="dataset"),
        _spec("entity_id", "TEXT", True, example="synthetic_scenario_seed_42_scenario_42"),
        _spec("action", "TEXT", False, example="load_persisted_dataset_to_raw"),
        _spec("status", "TEXT", True, example="completed"),
        _spec("details", "JSONB", False, example='{"row_counts": {"transactions": 100}}'),
        _spec("created_by", "TEXT", False, example="system"),
    ),
    "governance.model_runs": (
        _spec("model_run_id", "TEXT", False, primary_key=True, example="MODEL_RUN_001"),
        _spec("experiment_name", "TEXT", False, example="aml_risk_scoring"),
        _spec("model_name", "TEXT", False, example="isolation_forest"),
        _spec("model_version", "TEXT", True, example="v1"),
        _spec("model_type", "TEXT", False, example="anomaly_detection"),
        _spec("feature_version", "TEXT", True, example="features_v1"),
        _spec("training_start", "TIMESTAMPTZ", True, example="2025-01-01T10:00:00Z"),
        _spec("training_end", "TIMESTAMPTZ", True, example="2025-01-01T11:00:00Z"),
        _spec("parameters", "JSONB", False, example='{"n_estimators": 100}'),
        _spec("metrics", "JSONB", False, example='{"precision_at_k": 0.8}'),
        _spec("artefact_uri", "TEXT", True, example="runs:/MODEL_RUN_001/model"),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
    "governance.validation_reports": (
        _spec("validation_report_id", "TEXT", False, primary_key=True, example="VR_001"),
        _spec("report_name", "TEXT", False, example="model_validation_report"),
        _spec("report_version", "TEXT", False, example="v1"),
        _spec(
            "model_run_id",
            "TEXT",
            True,
            foreign_key="governance.model_runs(model_run_id)",
            example="MODEL_RUN_001",
        ),
        _spec("report_path", "TEXT", False, example="reports/model_validation/report.md"),
        _spec("report_type", "TEXT", False, example="model_validation"),
        _spec("summary", "JSONB", False, example='{"passed": true}'),
        _spec("created_at", "TIMESTAMPTZ", False, example="2025-01-01T12:00:00Z"),
    ),
}

DESCRIPTION_OVERRIDES = {
    "raw_payload": "Original source record captured as JSONB.",
    "record_hash": "Deterministic hash of the raw payload.",
    "reason_code": "Explanation code for why a rule or model created an alert.",
    "evidence_ids": "Supporting transaction or entity identifiers for an alert.",
    "case_risk_score": "Final composite case risk score used for prioritisation.",
    "status": "Workflow status for human review and disposition.",
    "details": "Structured JSON details for audit and governance events.",
    "parameters": "Model training or scoring parameters captured as JSONB.",
    "metrics": "Model performance and validation metrics captured as JSONB.",
    "report_path": "Path to the generated validation or governance report artefact.",
}

BUSINESS_MEANING_OVERRIDES = {
    "raw_payload": "Stores the original source record as JSONB for lineage and replay.",
    "record_hash": (
        "Supports lineage, reproducibility, integrity checks, and later deduplication."
    ),
    "transaction_id": "Source transaction identifier used to trace payment activity.",
    "sender_account_id": "Standardised account that initiated the transaction.",
    "receiver_account_id": (
        "Standardised internal account that received the transaction when present."
    ),
    "transaction_timestamp": "Parsed event time used for temporal rules and feature windows.",
    "amount": "Positive monetary transaction amount used by rules, features, and scoring.",
    "country_code": "Normalised country code used for jurisdiction and cross-border analysis.",
    "currency": "Normalised currency code for transaction and account consistency.",
    "is_cross_border": (
        "Flag recalculated from origin and destination countries for cross-border typologies."
    ),
    "is_labelled_suspicious": (
        "Labelled scenario label used for validation, rules, and later model evaluation."
    ),
    "typology_label": "Suspicious activity typology label from labelled scenario injection.",
    "reason_code": "Human-readable reason supporting alert transparency and review.",
    "evidence_ids": "Links an alert to supporting transactions or entities.",
    "case_risk_score": "Supports investigation prioritisation and queue ordering.",
    "status": "Tracks the human investigation lifecycle.",
    "audit_event_id": "Unique audit record for traceability.",
    "event_type": "Classifies runtime, validation, staging, rule, model, or analyst events.",
    "details": (
        "Carries structured audit details for ingestion, validation, staging, models, cases, "
        "and analyst actions."
    ),
    "model_run_id": "Model lineage identifier shared across runs, alerts, and reports.",
    "parameters": "Records model lineage and reproducible training configuration.",
    "metrics": "Stores model risk and validation metrics.",
    "artefact_uri": "Location of the persisted model or model artefact.",
    "validation_report_id": "Unique validation report artefact identifier.",
    "summary": "Structured summary of validation findings and report outcomes.",
}


def _humanise(column_name: str) -> str:
    return column_name.replace("_", " ")


def _description(column_name: str) -> str:
    if column_name in DESCRIPTION_OVERRIDES:
        return DESCRIPTION_OVERRIDES[column_name]
    return f"{_humanise(column_name).capitalize()} column for this project table."


def _business_meaning(column_name: str, qualified_name: str) -> str:
    if column_name in BUSINESS_MEANING_OVERRIDES:
        return BUSINESS_MEANING_OVERRIDES[column_name]
    return f"Captures {_humanise(column_name)} for {qualified_name}."


def _column_from_spec(qualified_name: str, spec: ColumnSpec) -> ColumnDefinition:
    (
        column_name,
        data_type,
        nullable,
        primary_key,
        foreign_key,
        validation_rules,
        example,
        lineage_source,
    ) = spec
    return ColumnDefinition(
        column_name=column_name,
        data_type=data_type,
        nullable=nullable,
        primary_key=primary_key,
        foreign_key=foreign_key,
        description=_description(column_name),
        business_meaning=_business_meaning(column_name, qualified_name),
        validation_rules=validation_rules,
        example_value=example,
        lineage_source=lineage_source,
    )


def _table_definition(qualified_name: str, description: str) -> TableDefinition:
    try:
        schema_name, table_name = qualified_name.split(".", maxsplit=1)
    except ValueError as exc:
        raise DataDictionaryError(f"Invalid qualified table name: {qualified_name}") from exc
    specs = COLUMN_CATALOGUE.get(qualified_name)
    if not specs:
        raise DataDictionaryError(f"Missing column catalogue for {qualified_name}")
    if schema_name not in LIFECYCLE_STAGE_BY_SCHEMA:
        raise DataDictionaryError(f"Missing lifecycle stage for schema {schema_name}")
    columns = tuple(_column_from_spec(qualified_name, spec) for spec in specs)
    primary_key = tuple(column.column_name for column in columns if column.primary_key)
    foreign_keys = tuple(
        f"{column.column_name} -> {column.foreign_key}"
        for column in columns
        if column.foreign_key is not None
    )
    return TableDefinition(
        schema_name=schema_name,
        table_name=table_name,
        qualified_name=qualified_name,
        description=description,
        lifecycle_stage=LIFECYCLE_STAGE_BY_SCHEMA[schema_name],
        primary_key=primary_key,
        foreign_keys=foreign_keys,
        columns=columns,
    )


def build_data_dictionary() -> DataDictionary:
    """Build the project data dictionary without connecting to PostgreSQL."""

    try:
        config = load_app_config()
        project_name = config.project.project.name
        project_version = config.project.project.version
    except Exception as exc:
        raise DataDictionaryError(f"Could not load project metadata: {exc}") from exc

    table_descriptions = get_table_descriptions()
    schema_descriptions = get_schema_descriptions()
    qualified_tables = get_qualified_table_names()
    missing_catalogue = sorted(set(qualified_tables).difference(COLUMN_CATALOGUE))
    missing_descriptions = sorted(set(qualified_tables).difference(table_descriptions))
    if missing_catalogue:
        raise DataDictionaryError(f"Missing column definitions for: {missing_catalogue}")
    if missing_descriptions:
        raise DataDictionaryError(f"Missing table descriptions for: {missing_descriptions}")

    tables = tuple(
        _table_definition(qualified_name, table_descriptions[qualified_name])
        for qualified_name in qualified_tables
    )
    if any(not table.columns for table in tables):
        empty_tables = [table.qualified_name for table in tables if not table.columns]
        raise DataDictionaryError(f"Tables without columns: {empty_tables}")

    return DataDictionary(
        project_name=project_name,
        generated_at=datetime.now(UTC).isoformat(),
        version=DATA_DICTIONARY_VERSION,
        tables=tables,
        metadata={
            "project_version": project_version,
            "schema_descriptions": schema_descriptions,
            "source": "database metadata and curated column catalogue",
        },
    )


def data_dictionary_to_dict(data_dictionary: DataDictionary) -> dict[str, Any]:
    """Serialise a data dictionary to a JSON-compatible dictionary."""

    return asdict(data_dictionary)


def data_dictionary_to_dataframe(data_dictionary: DataDictionary) -> pd.DataFrame:
    """Return one data dictionary row per column."""

    rows: list[dict[str, object]] = []
    for table in data_dictionary.tables:
        for column in table.columns:
            rows.append(
                {
                    "schema_name": table.schema_name,
                    "table_name": table.table_name,
                    "qualified_name": table.qualified_name,
                    "column_name": column.column_name,
                    "data_type": column.data_type,
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "foreign_key": column.foreign_key,
                    "description": column.description,
                    "business_meaning": column.business_meaning,
                    "validation_rules": "; ".join(column.validation_rules),
                    "example_value": column.example_value,
                    "lineage_source": column.lineage_source,
                    "lifecycle_stage": table.lifecycle_stage,
                }
            )
    return pd.DataFrame(rows)


def _ensure_parent(path: Path | str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def write_data_dictionary_markdown(
    data_dictionary: DataDictionary,
    output_path: Path | str = "reports/model_validation/feature_dictionary.md",
) -> Path:
    """Write the data dictionary as Markdown."""

    from graph_aml.documentation.markdown import render_data_dictionary_markdown

    try:
        path = _ensure_parent(output_path)
        path.write_text(render_data_dictionary_markdown(data_dictionary), encoding="utf-8")
        return path
    except Exception as exc:
        raise DocumentationWriteError(f"Could not write Markdown data dictionary: {exc}") from exc


def write_data_dictionary_json(
    data_dictionary: DataDictionary,
    output_path: Path | str = "reports/model_validation/data_dictionary.json",
) -> Path:
    """Write the data dictionary as deterministic JSON."""

    try:
        path = _ensure_parent(output_path)
        payload = data_dictionary_to_dict(data_dictionary)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise DocumentationWriteError(f"Could not write JSON data dictionary: {exc}") from exc


def write_data_dictionary_csv(
    data_dictionary: DataDictionary,
    output_path: Path | str = "reports/model_validation/data_dictionary.csv",
) -> Path:
    """Write the data dictionary as one-row-per-column CSV."""

    try:
        path = _ensure_parent(output_path)
        data_dictionary_to_dataframe(data_dictionary).to_csv(path, index=False)
        return path
    except Exception as exc:
        raise DocumentationWriteError(f"Could not write CSV data dictionary: {exc}") from exc


def generate_data_dictionary_artefacts(
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Build and write Markdown, JSON, and CSV data dictionary artefacts."""

    base_dir = Path(output_dir)
    data_dictionary = build_data_dictionary()
    return {
        "markdown": write_data_dictionary_markdown(
            data_dictionary,
            base_dir / "feature_dictionary.md",
        ),
        "json": write_data_dictionary_json(
            data_dictionary,
            base_dir / "data_dictionary.json",
        ),
        "csv": write_data_dictionary_csv(
            data_dictionary,
            base_dir / "data_dictionary.csv",
        ),
    }
