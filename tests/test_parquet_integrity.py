"""Integrity tests for the bronze, silver, and gold parquet layers.

Ensures every layer is present, has expected schemas, satisfies non-null and
uniqueness constraints, and remains referentially consistent across tables.
"""

from __future__ import annotations

from pathlib import Path

import pandera.pandas as pa
import pytest
from pandera import Column, DataFrameSchema

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"

SILVER_TABLES = (
    "accounts",
    "counterparties",
    "countries",
    "customers",
    "devices",
    "scenario_manifest",
    "transactions",
)

GOLD_TABLES = (
    "alerts",
    "cases",
    "case_alerts",
    "case_entities",
    "case_risk_scores",
    "case_evidence_packs",
    "case_explanations",
    "case_lifecycle_events",
    "case_assignments",
    "features_account_daily",
    "graph_features",
    "account_anomaly_scores",
    "account_risk_scores",
    "audit_events",
    "model_runs",
    "validation_reports",
)


def _read(path: Path):
    pd = pytest.importorskip("pandas")
    return pd.read_parquet(path)


# --- presence -------------------------------------------------------------


@pytest.mark.parametrize("table", SILVER_TABLES)
def test_silver_parquet_present(table: str) -> None:
    path = SILVER_DIR / f"{table}.parquet"
    assert path.is_file(), f"missing silver parquet: {path}"


@pytest.mark.parametrize("table", GOLD_TABLES)
def test_gold_parquet_present(table: str) -> None:
    path = GOLD_DIR / f"{table}.parquet"
    assert path.is_file(), f"missing gold parquet: {path}"


@pytest.mark.parametrize("table", SILVER_TABLES)
def test_bronze_csv_present(table: str) -> None:
    path = BRONZE_DIR / f"{table}.csv"
    assert path.is_file(), f"missing bronze csv: {path}"


# --- row counts ------------------------------------------------------------


def test_silver_row_counts_within_expected_band() -> None:
    expectations = {
        "accounts": (1000, 50000),
        "counterparties": (200, 10000),
        "countries": (5, 50),
        "customers": (500, 30000),
        "devices": (1000, 20000),
        "scenario_manifest": (10, 500),
        "transactions": (50000, 1000000),
    }
    for table, (lo, hi) in expectations.items():
        frame = _read(SILVER_DIR / f"{table}.parquet")
        assert lo <= len(frame) <= hi, f"{table}: {len(frame)} rows outside [{lo}, {hi}]"


def test_gold_alerts_match_scenario_count() -> None:
    alerts = _read(GOLD_DIR / "alerts.parquet")
    scenarios = _read(SILVER_DIR / "scenario_manifest.parquet")
    assert len(alerts) == len(scenarios), (
        f"alerts ({len(alerts)}) should equal scenario count ({len(scenarios)})"
    )


def test_gold_cases_count_le_alerts_count() -> None:
    alerts = _read(GOLD_DIR / "alerts.parquet")
    cases = _read(GOLD_DIR / "cases.parquet")
    assert len(cases) <= len(alerts), "cases should aggregate alerts, never exceed them"


def test_gold_features_one_row_per_account() -> None:
    features = _read(GOLD_DIR / "features_account_daily.parquet")
    accounts = _read(SILVER_DIR / "accounts.parquet")
    assert len(features) == len(accounts), (
        f"features row count ({len(features)}) must equal account count ({len(accounts)})"
    )


# --- uniqueness ------------------------------------------------------------


def test_silver_accounts_have_unique_ids() -> None:
    frame = _read(SILVER_DIR / "accounts.parquet")
    assert frame["account_id"].is_unique


def test_silver_transactions_have_unique_ids() -> None:
    frame = _read(SILVER_DIR / "transactions.parquet")
    assert frame["transaction_id"].is_unique


def test_silver_customers_have_unique_ids() -> None:
    frame = _read(SILVER_DIR / "customers.parquet")
    assert frame["customer_id"].is_unique


def test_gold_alerts_have_unique_ids() -> None:
    frame = _read(GOLD_DIR / "alerts.parquet")
    assert frame["alert_id"].is_unique


def test_gold_cases_have_unique_ids() -> None:
    frame = _read(GOLD_DIR / "cases.parquet")
    assert frame["case_id"].is_unique


# --- referential integrity -------------------------------------------------


def test_transactions_reference_known_accounts() -> None:
    tx = _read(SILVER_DIR / "transactions.parquet")
    accounts = _read(SILVER_DIR / "accounts.parquet")
    account_ids = set(accounts["account_id"].astype(str))
    senders = set(tx["sender_account_id"].dropna().astype(str))
    orphans = senders - account_ids
    assert not orphans, f"{len(orphans)} sender accounts not present in accounts table"


def test_accounts_reference_known_customers() -> None:
    accounts = _read(SILVER_DIR / "accounts.parquet")
    customers = _read(SILVER_DIR / "customers.parquet")
    cust_ids = set(customers["customer_id"].astype(str))
    referenced = set(accounts["customer_id"].dropna().astype(str))
    orphans = referenced - cust_ids
    assert not orphans, f"{len(orphans)} customer references missing"


def test_gold_alerts_reference_known_accounts() -> None:
    alerts = _read(GOLD_DIR / "alerts.parquet")
    accounts = _read(SILVER_DIR / "accounts.parquet")
    account_ids = set(accounts["account_id"].astype(str))
    referenced = set(alerts["account_id"].dropna().astype(str))
    orphans = referenced - account_ids
    assert not orphans, f"{len(orphans)} alert account_ids not in accounts table"


def test_gold_cases_reference_known_accounts() -> None:
    cases = _read(GOLD_DIR / "cases.parquet")
    accounts = _read(SILVER_DIR / "accounts.parquet")
    account_ids = set(accounts["account_id"].astype(str))
    referenced = set(cases["account_id"].dropna().astype(str))
    orphans = referenced - account_ids
    assert not orphans, f"{len(orphans)} case account_ids not in accounts table"


def test_gold_case_alerts_reference_known_cases_and_alerts() -> None:
    case_alerts = _read(GOLD_DIR / "case_alerts.parquet")
    if case_alerts.empty:
        return
    cases = _read(GOLD_DIR / "cases.parquet")
    alerts = _read(GOLD_DIR / "alerts.parquet")
    case_ids = set(cases["case_id"].astype(str))
    alert_ids = set(alerts["alert_id"].astype(str))
    orphan_cases = set(case_alerts["case_id"].astype(str)) - case_ids
    orphan_alerts = set(case_alerts["alert_id"].astype(str)) - alert_ids
    assert not orphan_cases, f"case_alerts references {len(orphan_cases)} unknown case_ids"
    assert not orphan_alerts, f"case_alerts references {len(orphan_alerts)} unknown alert_ids"


# --- schema / value checks -----------------------------------------------


def test_silver_transactions_amounts_positive() -> None:
    schema = DataFrameSchema(
        {"amount": Column(float, checks=pa.Check.gt(0), nullable=False)},
        strict=False,
    )
    frame = _read(SILVER_DIR / "transactions.parquet")
    schema.validate(frame)


def test_gold_account_risk_scores_in_range() -> None:
    schema = DataFrameSchema(
        {
            "account_risk_score": Column(
                float, checks=pa.Check.in_range(0.0, 100.0), nullable=False
            ),
            "risk_band": Column(
                str,
                checks=pa.Check.isin(["low", "medium", "high", "critical"]),
                nullable=False,
            ),
        },
        strict=False,
    )
    frame = _read(GOLD_DIR / "account_risk_scores.parquet")
    schema.validate(frame)


def test_gold_alerts_severity_valid() -> None:
    schema = DataFrameSchema(
        {
            "severity": Column(
                str,
                checks=pa.Check.isin(["low", "medium", "high", "critical"]),
                nullable=False,
            ),
            "risk_score_rule": Column(
                float, checks=pa.Check.in_range(0.0, 100.0), nullable=False
            ),
        },
        strict=False,
    )
    frame = _read(GOLD_DIR / "alerts.parquet")
    schema.validate(frame)


def test_gold_cases_status_valid() -> None:
    schema = DataFrameSchema(
        {
            "status": Column(
                str,
                checks=pa.Check.isin(["open", "in_review", "escalated", "closed"]),
                nullable=False,
            ),
            "priority_score": Column(float, checks=pa.Check.ge(0.0), nullable=False),
        },
        strict=False,
    )
    frame = _read(GOLD_DIR / "cases.parquet")
    schema.validate(frame)
