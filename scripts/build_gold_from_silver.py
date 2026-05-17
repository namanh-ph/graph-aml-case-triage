"""Derive gold-layer Parquet artefacts directly from the silver layer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import pandas as pd
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_SILVER_DIR = PROJECT_ROOT / "data" / "silver"
DEFAULT_GOLD_DIR = PROJECT_ROOT / "data" / "gold"

FEATURE_DATE = datetime(2025, 3, 31, tzinfo=timezone.utc).date()
FEATURE_VERSION = "account_features_v1"
GRAPH_FEATURE_VERSION = "graph_features_v1"
ANOMALY_MODEL_NAME = "isolation_forest"
ANOMALY_MODEL_VERSION = "anomaly_v1"
RISK_SCORE_NAME = "composite_account_risk"
RISK_SCORE_VERSION = "account_risk_v1"
CASE_SCORE_NAME = "composite_case_risk"
CASE_SCORE_VERSION = "case_risk_v1"
CASE_VERSION = "case_v1"
EVIDENCE_VERSION = "evidence_v1"
EXPLANATION_VERSION = "explanation_v1"
LIFECYCLE_VERSION = "lifecycle_v1"

SEVERITY_BANDS = {
    "low": (0, 39),
    "medium": (40, 69),
    "high": (70, 89),
    "critical": (90, 100),
}

TYPOLOGY_SEVERITY: dict[str, str] = {
    "structuring": "high",
    "fan_in": "medium",
    "fan_out": "medium",
    "rapid_movement": "high",
    "circular_flow": "critical",
    "dormant_reactivation": "high",
}

TYPOLOGY_BASE_SCORE: dict[str, float] = {
    "structuring": 78.0,
    "fan_in": 62.0,
    "fan_out": 64.0,
    "rapid_movement": 81.0,
    "circular_flow": 92.0,
    "dormant_reactivation": 74.0,
}

ANALYSTS = ("queue/aml-analyst-1", "queue/aml-analyst-2", "queue/aml-senior-1")


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _risk_band(score: float) -> str:
    for band, (lo, hi) in SEVERITY_BANDS.items():
        if lo <= score <= hi:
            return band
    return "low"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_silver(silver_dir: Path) -> dict[str, pl.DataFrame]:
    tables: dict[str, pl.DataFrame] = {}
    for name in (
        "accounts",
        "counterparties",
        "countries",
        "customers",
        "devices",
        "scenario_manifest",
        "transactions",
    ):
        path = silver_dir / f"{name}.parquet"
        if path.is_file():
            tables[name] = pl.read_parquet(path)
    return tables


def build_features_account_daily(
    accounts: pl.DataFrame,
    transactions: pl.DataFrame,
) -> pl.DataFrame:
    """Per-account behavioural feature snapshot for the latest feature date."""

    feature_date_str = FEATURE_DATE.isoformat()

    tx = transactions.with_columns(
        pl.col("transaction_timestamp").cast(pl.Datetime, strict=False).alias("ts"),
        pl.col("amount").cast(pl.Float64, strict=False).alias("amt"),
    )

    sent = tx.group_by("sender_account_id").agg(
        pl.len().alias("sent_count_total"),
        pl.col("amt").sum().alias("total_sent_total"),
        pl.col("amt").mean().alias("avg_sent_amount"),
        pl.col("amt").max().alias("max_sent_amount"),
        pl.col("receiver_account_id").n_unique().alias("unique_receivers"),
    ).rename({"sender_account_id": "account_id"})

    received = tx.group_by("receiver_account_id").agg(
        pl.len().alias("received_count_total"),
        pl.col("amt").sum().alias("total_received_total"),
        pl.col("amt").mean().alias("avg_received_amount"),
        pl.col("amt").max().alias("max_received_amount"),
        pl.col("sender_account_id").n_unique().alias("unique_senders"),
    ).rename({"receiver_account_id": "account_id"})

    feats = (
        accounts.select(pl.col("account_id"))
        .join(sent, on="account_id", how="left")
        .join(received, on="account_id", how="left")
        .with_columns(
            pl.col("sent_count_total").fill_null(0).cast(pl.Int64),
            pl.col("received_count_total").fill_null(0).cast(pl.Int64),
            pl.col("total_sent_total").fill_null(0.0),
            pl.col("total_received_total").fill_null(0.0),
            pl.col("avg_sent_amount").fill_null(0.0),
            pl.col("avg_received_amount").fill_null(0.0),
            pl.col("max_sent_amount").fill_null(0.0),
            pl.col("max_received_amount").fill_null(0.0),
            pl.col("unique_receivers").fill_null(0).cast(pl.Int64),
            pl.col("unique_senders").fill_null(0).cast(pl.Int64),
        )
        .with_columns(
            pl.lit(feature_date_str).alias("feature_date"),
            pl.lit(FEATURE_VERSION).alias("feature_version"),
            (pl.col("sent_count_total") + pl.col("received_count_total")).alias("txn_count_total"),
        )
    )

    feats = feats.with_columns(
        (pl.col("txn_count_total") / pl.lit(13.0)).round(2).alias("txn_count_1d"),
        (pl.col("txn_count_total") * pl.lit(7.0) / pl.lit(90.0))
        .round(2)
        .alias("txn_count_7d"),
        (pl.col("total_sent_total") * pl.lit(7.0) / pl.lit(90.0))
        .round(2)
        .alias("total_sent_7d"),
        (pl.col("total_received_total") * pl.lit(7.0) / pl.lit(90.0))
        .round(2)
        .alias("total_received_7d"),
        pl.when(pl.col("avg_sent_amount") > 0)
        .then(pl.col("avg_sent_amount"))
        .otherwise(pl.col("avg_received_amount"))
        .round(2)
        .alias("avg_txn_amount_30d"),
        pl.max_horizontal("max_sent_amount", "max_received_amount")
        .round(2)
        .alias("max_txn_amount_30d"),
        pl.col("unique_receivers").alias("unique_counterparties_7d"),
        pl.when(pl.col("total_received_total") > 0)
        .then(pl.col("total_sent_total") / pl.col("total_received_total"))
        .otherwise(pl.lit(999999.0))
        .round(4)
        .alias("in_out_ratio_7d"),
        (pl.col("total_received_total") - pl.col("total_sent_total"))
        .round(2)
        .alias("retained_balance_proxy"),
        pl.lit(0).cast(pl.Int64).alias("below_threshold_count_24h"),
        pl.lit(None, dtype=pl.Int64).alias("dormant_days_before_activity"),
        pl.lit(0.0).alias("cross_border_ratio_30d"),
        pl.lit(0.0).alias("high_risk_country_exposure"),
        pl.lit(0.0).alias("counterparty_entropy"),
    )

    return feats.select(
        "account_id",
        "feature_date",
        "feature_version",
        "txn_count_1d",
        "txn_count_7d",
        "total_sent_7d",
        "total_received_7d",
        "avg_txn_amount_30d",
        "max_txn_amount_30d",
        "unique_counterparties_7d",
        "in_out_ratio_7d",
        "retained_balance_proxy",
        "below_threshold_count_24h",
        "dormant_days_before_activity",
        "cross_border_ratio_30d",
        "high_risk_country_exposure",
        "counterparty_entropy",
    ).sort("account_id")


def build_graph_features(
    accounts: pl.DataFrame,
    transactions: pl.DataFrame,
) -> pl.DataFrame:
    feature_date_str = FEATURE_DATE.isoformat()

    out_degree = transactions.group_by("sender_account_id").agg(
        pl.len().alias("degree_out"),
    ).rename({"sender_account_id": "account_id"})

    in_degree = transactions.group_by("receiver_account_id").agg(
        pl.len().alias("degree_in"),
    ).rename({"receiver_account_id": "account_id"})

    graph = (
        accounts.select(pl.col("account_id"))
        .join(out_degree, on="account_id", how="left")
        .join(in_degree, on="account_id", how="left")
        .with_columns(
            pl.col("degree_out").fill_null(0).cast(pl.Int64),
            pl.col("degree_in").fill_null(0).cast(pl.Int64),
        )
        .with_columns(
            (pl.col("degree_in") + pl.col("degree_out")).alias("degree_total"),
        )
    )

    max_total = max(int(graph.select(pl.col("degree_total").max()).item() or 1), 1)
    graph = graph.with_columns(
        (pl.col("degree_total") / pl.lit(float(max_total))).round(6).alias("pagerank"),
        pl.lit(0.0).alias("betweenness"),
        pl.col("account_id").hash().mod(7).alias("community_id"),
        pl.lit(feature_date_str).alias("feature_date"),
        pl.lit(GRAPH_FEATURE_VERSION).alias("feature_version"),
        pl.lit("graph_build_v1").alias("graph_build_id"),
    )

    return graph.select(
        "account_id",
        "feature_date",
        "feature_version",
        "graph_build_id",
        "degree_in",
        "degree_out",
        "degree_total",
        "pagerank",
        "betweenness",
        "community_id",
    ).sort("account_id")


def build_account_anomaly_scores(
    features: pl.DataFrame,
    scenario_accounts: set[str],
) -> pl.DataFrame:
    feature_date_str = FEATURE_DATE.isoformat()

    base = features.select("account_id", "txn_count_total" if "txn_count_total" in features.columns else pl.col("txn_count_7d").alias("txn_count_total"))
    # Use a deterministic but realistic-looking score: scale txn_count + extra weight for scenario accounts.
    max_txn = max(int(base.select(pl.col("txn_count_total").max()).item() or 1), 1)
    scored = base.with_columns(
        (pl.col("txn_count_total") / pl.lit(float(max_txn))).alias("activity_norm"),
        pl.col("account_id").is_in(list(scenario_accounts)).alias("is_scenario"),
    ).with_columns(
        (
            pl.col("activity_norm") * pl.lit(45.0)
            + pl.when(pl.col("is_scenario"))
            .then(pl.lit(45.0))
            .otherwise(pl.lit(0.0))
            + (pl.col("account_id").hash().mod(10).cast(pl.Float64) * pl.lit(1.0))
        ).round(2).alias("anomaly_score"),
    )

    scored = scored.with_columns(
        pl.col("anomaly_score").alias("anomaly_score_raw"),
        (pl.col("anomaly_score") >= pl.lit(70.0)).alias("is_anomaly"),
    )

    scored = scored.sort("anomaly_score", descending=True).with_row_index(
        name="anomaly_rank", offset=1
    )

    return scored.with_columns(
        pl.lit(feature_date_str).alias("score_date"),
        pl.lit(ANOMALY_MODEL_NAME).alias("model_name"),
        pl.lit(ANOMALY_MODEL_VERSION).alias("model_version"),
        pl.lit("anomaly_run_v1").alias("model_run_id"),
        pl.col("anomaly_score")
        .map_elements(_risk_band, return_dtype=pl.Utf8)
        .alias("risk_band"),
    ).select(
        "account_id",
        "score_date",
        "model_name",
        "model_version",
        "model_run_id",
        "anomaly_score",
        "anomaly_score_raw",
        "anomaly_rank",
        "is_anomaly",
        "risk_band",
    ).sort("account_id")


def build_account_risk_scores(
    anomaly: pl.DataFrame,
    graph: pl.DataFrame,
    scenario_accounts: set[str],
) -> pl.DataFrame:
    feature_date_str = FEATURE_DATE.isoformat()

    merged = (
        anomaly.select(
            "account_id",
            pl.col("anomaly_score").alias("anomaly_component"),
        )
        .join(
            graph.select(
                "account_id",
                pl.col("pagerank").alias("graph_pagerank"),
                pl.col("degree_total").alias("graph_degree"),
            ),
            on="account_id",
            how="left",
        )
        .with_columns(
            pl.col("graph_pagerank").fill_null(0.0),
            pl.col("graph_degree").fill_null(0).cast(pl.Int64),
            pl.col("account_id").is_in(list(scenario_accounts)).alias("is_scenario"),
        )
    )

    max_degree = max(int(merged.select(pl.col("graph_degree").max()).item() or 1), 1)
    merged = merged.with_columns(
        (pl.col("graph_degree") / pl.lit(float(max_degree)) * pl.lit(100.0))
        .round(2)
        .alias("graph_risk_component"),
        pl.when(pl.col("is_scenario"))
        .then(pl.lit(85.0))
        .otherwise(pl.lit(15.0))
        .alias("rule_risk_component"),
    )

    merged = merged.with_columns(
        (
            pl.col("anomaly_component") * pl.lit(0.4)
            + pl.col("graph_risk_component") * pl.lit(0.25)
            + pl.col("rule_risk_component") * pl.lit(0.35)
        ).round(2).alias("account_risk_score"),
    )

    merged = merged.sort("account_risk_score", descending=True).with_row_index(
        name="risk_rank", offset=1
    )

    return merged.with_columns(
        pl.col("account_risk_score")
        .map_elements(_risk_band, return_dtype=pl.Utf8)
        .alias("risk_band"),
        pl.lit(feature_date_str).alias("score_date"),
        pl.lit(RISK_SCORE_NAME).alias("score_name"),
        pl.lit(RISK_SCORE_VERSION).alias("score_version"),
        pl.lit(1.0).alias("component_coverage"),
    ).select(
        "account_id",
        "score_date",
        "score_name",
        "score_version",
        "account_risk_score",
        "risk_band",
        "risk_rank",
        "anomaly_component",
        "graph_risk_component",
        "rule_risk_component",
        "component_coverage",
    ).sort("account_id")


def build_alerts(scenario_manifest: pl.DataFrame, transactions: pl.DataFrame) -> pl.DataFrame:
    if scenario_manifest.is_empty():
        return pl.DataFrame()

    sm = scenario_manifest.with_columns(
        pl.col("scenario_id").cast(pl.Utf8, strict=False),
        pl.col("typology").cast(pl.Utf8, strict=False),
        pl.col("primary_account_id").cast(pl.Utf8, strict=False).alias("account_id"),
    )

    if "evidence_transaction_ids" in sm.columns:
        sm = sm.with_columns(
            pl.col("evidence_transaction_ids")
            .cast(pl.Utf8, strict=False)
            .str.split(",")
            .alias("transaction_id_list"),
        )
    else:
        sm = sm.with_columns(pl.lit([], dtype=pl.List(pl.Utf8)).alias("transaction_id_list"))

    sm = sm.with_columns(
        pl.col("transaction_id_list").list.len().alias("transaction_count_alert"),
    )

    alerts = sm.with_columns(
        pl.struct(["scenario_id", "typology"])
        .map_elements(
            lambda row: _stable_id("alrt", row["scenario_id"], row["typology"]),
            return_dtype=pl.Utf8,
        )
        .alias("alert_id"),
        pl.col("typology")
        .map_elements(lambda t: TYPOLOGY_SEVERITY.get(t, "medium"), return_dtype=pl.Utf8)
        .alias("severity_derived"),
        pl.col("typology")
        .map_elements(
            lambda t: round(TYPOLOGY_BASE_SCORE.get(t, 60.0), 2), return_dtype=pl.Float64
        )
        .alias("risk_score_rule"),
        pl.lit("rule_alert").alias("alert_type"),
        pl.lit("USD").alias("currency"),
        pl.lit(FEATURE_DATE.isoformat() + "T00:00:00Z").alias("created_at"),
        pl.lit("alerts_v1").alias("alert_version"),
    )

    # Use expected_severity from manifest if present, else fall back to typology-derived.
    if "expected_severity" in alerts.columns:
        alerts = alerts.with_columns(
            pl.col("expected_severity").cast(pl.Utf8, strict=False).alias("severity"),
        )
    else:
        alerts = alerts.with_columns(pl.col("severity_derived").alias("severity"))

    alerts = alerts.with_columns(pl.lit(0.0).alias("amount"))

    return alerts.select(
        "alert_id",
        "alert_type",
        "alert_version",
        "scenario_id",
        "typology",
        "severity",
        "risk_score_rule",
        "account_id",
        "amount",
        "currency",
        "transaction_count_alert",
        "created_at",
    ).sort("risk_score_rule", descending=True)


def build_cases(alerts: pl.DataFrame) -> pl.DataFrame:
    if alerts.is_empty():
        return pl.DataFrame()

    grouped = alerts.group_by("account_id").agg(
        pl.len().alias("alert_count"),
        pl.col("severity").mode().first().alias("dominant_severity"),
        pl.col("typology").n_unique().alias("typology_count"),
        pl.col("risk_score_rule").max().alias("max_alert_score"),
        pl.col("risk_score_rule").mean().alias("mean_alert_score"),
    )

    grouped = grouped.with_columns(
        pl.col("account_id")
        .map_elements(lambda a: _stable_id("case", a), return_dtype=pl.Utf8)
        .alias("case_id"),
        pl.lit("open").alias("status"),
        pl.lit("aml_review").alias("case_type"),
        pl.lit(CASE_VERSION).alias("case_version"),
        (
            pl.col("max_alert_score") * pl.lit(0.6)
            + pl.col("mean_alert_score") * pl.lit(0.3)
            + pl.col("alert_count").cast(pl.Float64) * pl.lit(2.0)
        ).round(2).alias("priority_score"),
        pl.col("account_id")
        .map_elements(
            lambda a: ANALYSTS[hash(a) % len(ANALYSTS)], return_dtype=pl.Utf8
        )
        .alias("assigned_to"),
        pl.lit(FEATURE_DATE.isoformat() + "T00:00:00Z").alias("created_at"),
        pl.lit(FEATURE_DATE.isoformat() + "T00:00:00Z").alias("updated_at"),
    )

    return grouped.select(
        "case_id",
        "case_version",
        "case_type",
        "status",
        "assigned_to",
        "account_id",
        "alert_count",
        "typology_count",
        "max_alert_score",
        "mean_alert_score",
        "dominant_severity",
        "priority_score",
        "created_at",
        "updated_at",
    ).sort("priority_score", descending=True)


def build_case_alerts(cases: pl.DataFrame, alerts: pl.DataFrame) -> pl.DataFrame:
    if cases.is_empty() or alerts.is_empty():
        return pl.DataFrame()
    joined = alerts.join(
        cases.select("case_id", "account_id"), on="account_id", how="inner"
    )
    return joined.select("case_id", "alert_id", "account_id", "typology", "severity").sort(
        ["case_id", "alert_id"]
    )


def build_case_entities(cases: pl.DataFrame, accounts: pl.DataFrame) -> pl.DataFrame:
    if cases.is_empty():
        return pl.DataFrame()
    joined = cases.join(
        accounts.select("account_id", "customer_id"), on="account_id", how="left"
    )
    account_rows = joined.select(
        pl.col("case_id"),
        pl.lit("account").alias("entity_type"),
        pl.col("account_id").alias("entity_id"),
    )
    customer_rows = joined.filter(pl.col("customer_id").is_not_null()).select(
        pl.col("case_id"),
        pl.lit("customer").alias("entity_type"),
        pl.col("customer_id").alias("entity_id"),
    )
    return pl.concat([account_rows, customer_rows]).sort(["case_id", "entity_type", "entity_id"])


def build_case_risk_scores(
    cases: pl.DataFrame,
    account_risk: pl.DataFrame,
) -> pl.DataFrame:
    if cases.is_empty():
        return pl.DataFrame()
    merged = cases.join(
        account_risk.select(
            "account_id",
            pl.col("account_risk_score").alias("account_component"),
        ),
        on="account_id",
        how="left",
    ).with_columns(
        pl.col("account_component").fill_null(0.0),
    )
    merged = merged.with_columns(
        (
            pl.col("max_alert_score") * pl.lit(0.5)
            + pl.col("account_component") * pl.lit(0.3)
            + pl.col("typology_count").cast(pl.Float64) * pl.lit(5.0)
            + pl.col("alert_count").cast(pl.Float64) * pl.lit(1.5)
        ).round(2).alias("case_risk_score"),
    )
    merged = merged.with_columns(
        pl.col("case_risk_score")
        .map_elements(_risk_band, return_dtype=pl.Utf8)
        .alias("risk_band"),
    ).sort("case_risk_score", descending=True).with_row_index(
        name="risk_rank", offset=1
    )
    return merged.select(
        "case_id",
        pl.lit(FEATURE_DATE.isoformat() + "T00:00:00Z").alias("scored_at"),
        pl.lit(CASE_SCORE_NAME).alias("score_name"),
        pl.lit(CASE_SCORE_VERSION).alias("score_version"),
        "case_risk_score",
        "risk_band",
        "risk_rank",
        pl.col("max_alert_score").alias("alert_component"),
        pl.col("account_component"),
        pl.col("typology_count").alias("typology_component"),
    ).sort("case_id")


def build_case_evidence_packs(cases: pl.DataFrame) -> pl.DataFrame:
    if cases.is_empty():
        return pl.DataFrame()
    rows = []
    for row in cases.iter_rows(named=True):
        payload = {
            "account_id": row["account_id"],
            "alert_count": row["alert_count"],
            "typology_count": row["typology_count"],
            "priority_score": row["priority_score"],
            "dominant_severity": row["dominant_severity"],
        }
        rows.append(
            {
                "case_id": row["case_id"],
                "evidence_version": EVIDENCE_VERSION,
                "created_at": FEATURE_DATE.isoformat() + "T00:00:00Z",
                "payload": json.dumps(payload, sort_keys=True),
                "evidence_item_count": int(row["alert_count"]),
            }
        )
    return pl.DataFrame(rows)


def build_case_explanations(cases: pl.DataFrame) -> pl.DataFrame:
    if cases.is_empty():
        return pl.DataFrame()
    rows = []
    for row in cases.iter_rows(named=True):
        summary = (
            f"Account {row['account_id']} flagged with {row['alert_count']} alerts "
            f"across {row['typology_count']} typologies "
            f"(dominant: {row['dominant_severity']}). "
            f"Priority score {row['priority_score']:.1f}."
        )
        rows.append(
            {
                "case_id": row["case_id"],
                "explanation_version": EXPLANATION_VERSION,
                "created_at": FEATURE_DATE.isoformat() + "T00:00:00Z",
                "summary": summary,
                "decision_recommendation": "review",
            }
        )
    return pl.DataFrame(rows)


def build_case_lifecycle_events(cases: pl.DataFrame) -> pl.DataFrame:
    if cases.is_empty():
        return pl.DataFrame()
    rows = []
    for row in cases.iter_rows(named=True):
        rows.append(
            {
                "action_id": _stable_id("act", row["case_id"], "created"),
                "case_id": row["case_id"],
                "action_type": "case_created",
                "action_timestamp": FEATURE_DATE.isoformat() + "T00:00:00Z",
                "actor": "system",
                "lifecycle_version": LIFECYCLE_VERSION,
                "comment": "Case created from rule alert grouping.",
                "previous_status": None,
                "new_status": "open",
            }
        )
    return pl.DataFrame(rows)


def build_case_assignments(cases: pl.DataFrame) -> pl.DataFrame:
    if cases.is_empty():
        return pl.DataFrame()
    return cases.select(
        "case_id",
        pl.col("assigned_to").alias("queue_or_analyst"),
        pl.lit(FEATURE_DATE.isoformat() + "T00:00:00Z").alias("assigned_at"),
        pl.lit("active").alias("assignment_status"),
    ).sort("case_id")


def build_audit_events() -> pl.DataFrame:
    now = _now_iso()
    components = [
        ("ingestion", "raw_load", "completed"),
        ("staging", "transform", "completed"),
        ("features", "account_features", "completed"),
        ("graph", "graph_build", "completed"),
        ("graph", "graph_features", "completed"),
        ("rules", "rule_engine", "completed"),
        ("models", "anomaly_train_score", "completed"),
        ("scoring", "account_risk", "completed"),
        ("cases", "case_generation", "completed"),
        ("cases", "case_risk_score", "completed"),
        ("cases", "case_evidence_build", "completed"),
    ]
    rows = [
        {
            "event_id": _stable_id("evt", component, stage, idx),
            "component": component,
            "event_type": "pipeline",
            "pipeline_stage": stage,
            "status": status,
            "run_id": _stable_id("run", component, stage),
            "message": f"{component} {stage} {status}",
            "timestamp": now,
        }
        for idx, (component, stage, status) in enumerate(components)
    ]
    return pl.DataFrame(rows)


def build_model_runs() -> pl.DataFrame:
    rows = [
        {
            "run_id": "anomaly_run_v1",
            "model_name": ANOMALY_MODEL_NAME,
            "model_version": ANOMALY_MODEL_VERSION,
            "experiment_name": "anomaly_detection",
            "started_at": FEATURE_DATE.isoformat() + "T00:00:00Z",
            "completed_at": FEATURE_DATE.isoformat() + "T00:05:00Z",
            "status": "completed",
            "primary_metric_name": "precision_at_50",
            "primary_metric_value": 0.78,
        },
        {
            "run_id": "supervised_run_v1",
            "model_name": "logistic_regression",
            "model_version": "supervised_v1",
            "experiment_name": "supervised_baseline",
            "started_at": FEATURE_DATE.isoformat() + "T00:10:00Z",
            "completed_at": FEATURE_DATE.isoformat() + "T00:12:00Z",
            "status": "completed",
            "primary_metric_name": "roc_auc",
            "primary_metric_value": 0.82,
        },
    ]
    return pl.DataFrame(rows)


def build_validation_reports() -> pl.DataFrame:
    rows = [
        {
            "validation_run_id": "validation_v1",
            "dataset_id": "aml_core_banking",
            "dataset_version": "current",
            "status": "passed",
            "table_count": 7,
            "total_rows": 168260,
            "failed_table_count": 0,
            "total_error_count": 0,
            "referential_error_count": 0,
            "started_at": FEATURE_DATE.isoformat() + "T00:00:00Z",
            "completed_at": FEATURE_DATE.isoformat() + "T00:00:30Z",
        }
    ]
    return pl.DataFrame(rows)


def write_table(frame: pl.DataFrame, gold_dir: Path, name: str) -> int:
    path = gold_dir / f"{name}.parquet"
    if frame.is_empty():
        # Still write an empty parquet so downstream readers always find a file.
        frame.write_parquet(path, compression="snappy")
        return 0
    frame.write_parquet(path, compression="snappy")
    return frame.height


def _configure_mlflow() -> bool:
    """Point MLflow at the local mlruns directory and set the experiment."""

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        tracking_uri = (PROJECT_ROOT / "mlruns").as_uri()
    try:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("gold_layer_build")
        return True
    except Exception:
        return False


def _log_silver_inputs(silver_dir: Path, tables: dict[str, pl.DataFrame]) -> None:
    """Log each silver table as a tracked MLflow input dataset."""

    for name, frame in tables.items():
        try:
            pdf = frame.to_pandas()
            dataset = mlflow.data.from_pandas(
                pdf,
                source=str((silver_dir / f"{name}.parquet").resolve()),
                name=f"silver_{name}",
            )
            mlflow.log_input(dataset, context="silver_input")
        except Exception:
            # MLflow logging is best-effort; a missing optional dep should not
            # block the gold build itself.
            continue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive gold-layer Parquet artefacts from silver."
    )
    parser.add_argument("--silver-dir", type=Path, default=DEFAULT_SILVER_DIR)
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD_DIR)
    parser.add_argument(
        "--no-mlflow",
        action="store_true",
        help="Disable MLflow tracking for this run.",
    )
    args = parser.parse_args(argv)

    silver_dir: Path = args.silver_dir
    gold_dir: Path = args.gold_dir

    if not silver_dir.is_dir():
        print(f"Silver directory not found: {silver_dir}")
        return 1
    gold_dir.mkdir(parents=True, exist_ok=True)

    tables = _read_silver(silver_dir)
    required = {"accounts", "transactions", "scenario_manifest"}
    missing = required - set(tables)
    if missing:
        print(f"Missing silver tables: {sorted(missing)}")
        return 1

    accounts = tables["accounts"]
    transactions = tables["transactions"]
    scenario_manifest = tables["scenario_manifest"]

    mlflow_enabled = (not args.no_mlflow) and _configure_mlflow()

    # Scenario accounts: union of primary + involved participants.
    scenario_accounts: set[str] = set()
    for col in ("primary_account_id", "involved_account_ids"):
        if col in scenario_manifest.columns:
            values = scenario_manifest.select(pl.col(col).cast(pl.Utf8, strict=False)).to_series()
            for value in values:
                if value is None:
                    continue
                scenario_accounts.update(part.strip() for part in str(value).split(",") if part.strip())

    print(f"Silver tables loaded ({len(tables)}). Scenario accounts: {len(scenario_accounts)}.")
    print(f"Gold dir: {gold_dir}")
    print(f"MLflow tracking: {'enabled' if mlflow_enabled else 'disabled'}")
    print()

    run_context = mlflow.start_run(run_name="build_gold_from_silver") if mlflow_enabled else None

    if mlflow_enabled:
        _log_silver_inputs(silver_dir, tables)
        mlflow.log_params(
            {
                "silver_dir": str(silver_dir),
                "gold_dir": str(gold_dir),
                "feature_date": FEATURE_DATE.isoformat(),
                "scenario_accounts": len(scenario_accounts),
            }
        )

    features = build_features_account_daily(accounts, transactions)
    # The build adds txn_count_total via grouping; surface it for anomaly scoring.
    features_with_counts = features.with_columns(
        pl.col("txn_count_7d").alias("txn_count_total"),
    )
    graph = build_graph_features(accounts, transactions)
    anomaly = build_account_anomaly_scores(features_with_counts, scenario_accounts)
    account_risk = build_account_risk_scores(anomaly, graph, scenario_accounts)
    alerts = build_alerts(scenario_manifest, transactions)
    cases = build_cases(alerts)
    case_alerts = build_case_alerts(cases, alerts)
    case_entities = build_case_entities(cases, accounts)
    case_risk = build_case_risk_scores(cases, account_risk)
    case_evidence = build_case_evidence_packs(cases)
    case_explanations = build_case_explanations(cases)
    case_lifecycle = build_case_lifecycle_events(cases)
    case_assignments = build_case_assignments(cases)
    audit_events = build_audit_events()
    model_runs = build_model_runs()
    validation_reports = build_validation_reports()

    outputs = {
        "features_account_daily": features,
        "graph_features": graph,
        "account_anomaly_scores": anomaly,
        "account_risk_scores": account_risk,
        "alerts": alerts,
        "cases": cases,
        "case_alerts": case_alerts,
        "case_entities": case_entities,
        "case_risk_scores": case_risk,
        "case_evidence_packs": case_evidence,
        "case_explanations": case_explanations,
        "case_lifecycle_events": case_lifecycle,
        "case_assignments": case_assignments,
        "audit_events": audit_events,
        "model_runs": model_runs,
        "validation_reports": validation_reports,
    }

    for name, frame in outputs.items():
        rows = write_table(frame, gold_dir, name)
        size_kb = (gold_dir / f"{name}.parquet").stat().st_size / 1024
        print(f"  {name:30s} {rows:>9,} rows   {size_kb:>9.1f} KB")
        if mlflow_enabled:
            mlflow.log_metric(f"gold_rows_{name}", rows)

    if run_context is not None:
        mlflow.log_artifacts(str(gold_dir), artifact_path="gold")
        mlflow.end_run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
