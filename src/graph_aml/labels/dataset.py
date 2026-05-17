"""Supervised-readiness dataset construction for analyst labels."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy import Engine

from graph_aml.labels.config import AnalystLabelConfig
from graph_aml.labels.exceptions import LabelDatasetError, LabelError
from graph_aml.labels.inputs import read_label_inputs
from graph_aml.labels.mapping import build_account_labels, build_case_labels

CASE_SUPERVISED_DATASET_COLUMNS = (
    "case_id",
    "dataset_version",
    "case_label",
    "label_name",
    "label_timestamp",
    "case_risk_score",
    "risk_band",
    "alert_count",
    "typology_count",
    "related_account_count",
    "evidence_transaction_count",
    "total_transaction_value",
    "component_coverage",
)

ACCOUNT_SUPERVISED_DATASET_COLUMNS = (
    "account_id",
    "dataset_version",
    "account_label",
    "label_name",
    "label_timestamp",
    "account_risk_score",
    "risk_band",
    "anomaly_score",
    "graph_risk_score",
    "rule_risk_score",
    "customer_risk_score",
    "jurisdiction_risk_score",
    "degree_centrality",
    "pagerank_score",
    "betweenness_centrality",
    "cycle_count",
    "community_size",
)


@dataclass(frozen=True)
class LabelDatasetBuildResult:
    case_labels: pd.DataFrame
    account_labels: pd.DataFrame
    case_dataset: pd.DataFrame
    account_dataset: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def _config(config: AnalystLabelConfig | None) -> AnalystLabelConfig:
    return config or AnalystLabelConfig()


def _empty(columns: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _latest_by(
    frame: pd.DataFrame,
    key: str,
    sort_candidates: tuple[str, ...],
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    if key not in frame.columns:
        raise LabelDatasetError(f"frame missing key column {key}")
    working = frame.copy(deep=True)
    sort_cols = [key]
    ascending = [True]
    for column in sort_candidates:
        if column in working.columns:
            sort_cols.append(column)
            ascending.append(False)
            working[column] = pd.to_datetime(working[column], errors="coerce")
    working = working.sort_values(sort_cols, ascending=ascending, kind="mergesort")
    return working.drop_duplicates(key, keep="first")


def _enforce_feature_timestamp(
    merged: pd.DataFrame,
    timestamp_column: str,
    feature_column: str,
    config: AnalystLabelConfig,
) -> None:
    if not config.leakage_controls.enforce_feature_timestamp_before_label:
        return
    if feature_column not in merged.columns:
        return
    label_ts = pd.to_datetime(merged[timestamp_column], errors="coerce", utc=True)
    feature_ts = pd.to_datetime(merged[feature_column], errors="coerce", utc=True)
    bad = feature_ts.notna() & label_ts.notna() & (feature_ts > label_ts)
    if bool(bad.any()):
        raise LabelDatasetError(f"{feature_column} is after label timestamp")


def build_case_supervised_dataset(
    case_labels: pd.DataFrame,
    case_risk_scores: pd.DataFrame,
    config: AnalystLabelConfig | None = None,
) -> pd.DataFrame:
    """Join case labels to the latest case risk score features."""

    resolved = _config(config)
    if not isinstance(case_labels, pd.DataFrame) or not isinstance(case_risk_scores, pd.DataFrame):
        raise LabelDatasetError("case labels and case risk scores must be DataFrames")
    if case_labels.empty:
        return _empty(CASE_SUPERVISED_DATASET_COLUMNS)
    latest_scores = _latest_by(case_risk_scores, "case_id", ("scored_at", "score_date"))
    merged = case_labels.merge(latest_scores, on="case_id", how="left", suffixes=("", "_score"))
    _enforce_feature_timestamp(merged, "label_timestamp", "scored_at", resolved)
    rows = pd.DataFrame(
        {
            "case_id": merged["case_id"],
            "dataset_version": resolved.dataset_version,
            "case_label": merged["case_label"],
            "label_name": merged["label_name"],
            "label_timestamp": merged["label_timestamp"],
            "case_risk_score": merged.get("case_risk_score"),
            "risk_band": merged.get("risk_band"),
            "alert_count": merged.get("alert_count"),
            "typology_count": merged.get("typology_count"),
            "related_account_count": merged.get("related_account_count"),
            "evidence_transaction_count": merged.get("evidence_transaction_count"),
            "total_transaction_value": merged.get("total_transaction_value"),
            "component_coverage": merged.get("component_coverage"),
        }
    )
    return (
        rows.reindex(columns=CASE_SUPERVISED_DATASET_COLUMNS)
        .sort_values("case_id")
        .reset_index(drop=True)
    )


def build_account_supervised_dataset(
    account_labels: pd.DataFrame,
    account_features: pd.DataFrame,
    account_risk_scores: pd.DataFrame,
    graph_features: pd.DataFrame,
    anomaly_scores: pd.DataFrame,
    config: AnalystLabelConfig | None = None,
) -> pd.DataFrame:
    """Join account labels to latest account, graph, anomaly, and behaviour features."""

    resolved = _config(config)
    if not isinstance(account_labels, pd.DataFrame):
        raise LabelDatasetError("account_labels must be a DataFrame")
    if account_labels.empty:
        return _empty(ACCOUNT_SUPERVISED_DATASET_COLUMNS)
    latest_account_features = _latest_by(account_features, "account_id", ("feature_date",))
    latest_risk = _latest_by(account_risk_scores, "account_id", ("scored_at", "score_date"))
    latest_graph = _latest_by(graph_features, "account_id", ("computed_at", "feature_date"))
    latest_anomaly = _latest_by(anomaly_scores, "account_id", ("scored_at", "score_date"))
    merged = account_labels.copy(deep=True)
    for frame, suffix in (
        (latest_account_features, "_feature"),
        (latest_risk, "_risk"),
        (latest_graph, "_graph"),
        (latest_anomaly, "_anomaly"),
    ):
        if not frame.empty:
            merged = merged.merge(frame, on="account_id", how="left", suffixes=("", suffix))
    for feature_column in ("feature_date", "scored_at", "computed_at", "score_date"):
        if feature_column in merged.columns:
            _enforce_feature_timestamp(merged, "label_timestamp", feature_column, resolved)
    rows = pd.DataFrame(
        {
            "account_id": merged["account_id"],
            "dataset_version": resolved.dataset_version,
            "account_label": merged["account_label"],
            "label_name": merged["label_name"],
            "label_timestamp": merged["label_timestamp"],
            "account_risk_score": merged.get("account_risk_score"),
            "risk_band": merged.get("risk_band"),
            "anomaly_score": merged.get("anomaly_score"),
            "graph_risk_score": merged.get("graph_risk_score"),
            "rule_risk_score": merged.get("rule_risk_score"),
            "customer_risk_score": merged.get("customer_risk_score"),
            "jurisdiction_risk_score": merged.get("jurisdiction_risk_score"),
            "degree_centrality": merged.get("degree_centrality"),
            "pagerank_score": merged.get("pagerank_score"),
            "betweenness_centrality": merged.get("betweenness_centrality"),
            "cycle_count": merged.get("cycle_count"),
            "community_size": merged.get("community_size"),
        }
    )
    return (
        rows.reindex(columns=ACCOUNT_SUPERVISED_DATASET_COLUMNS)
        .sort_values("account_id")
        .reset_index(drop=True)
    )


def build_label_datasets_from_inputs(
    inputs: dict[str, pd.DataFrame],
    config: AnalystLabelConfig | None = None,
) -> LabelDatasetBuildResult:
    """Build case/account labels and supervised-readiness datasets from input frames."""

    resolved = _config(config)
    try:
        cases = inputs["cases"]
        lifecycle_events = inputs["lifecycle_events"]
        case_entities = inputs["case_entities"]
        case_risk_scores = inputs["case_risk_scores"]
        account_features = inputs["account_features"]
        account_risk_scores = inputs["account_risk_scores"]
        graph_features = inputs["graph_features"]
        anomaly_scores = inputs["anomaly_scores"]
    except KeyError as exc:
        raise LabelDatasetError(f"missing label input frame: {exc}") from exc
    case_labels = (
        build_case_labels(cases, lifecycle_events, resolved)
        if resolved.propagation.build_case_labels
        else pd.DataFrame()
    )
    account_labels = (
        build_account_labels(case_labels, cases, case_entities, resolved)
        if resolved.propagation.build_account_labels
        else pd.DataFrame()
    )
    case_dataset = build_case_supervised_dataset(case_labels, case_risk_scores, resolved)
    account_dataset = build_account_supervised_dataset(
        account_labels,
        account_features,
        account_risk_scores,
        graph_features,
        anomaly_scores,
        resolved,
    )
    return LabelDatasetBuildResult(
        case_labels=case_labels,
        account_labels=account_labels,
        case_dataset=case_dataset,
        account_dataset=account_dataset,
        summary={
            "case_label_count": int(len(case_labels)),
            "account_label_count": int(len(account_labels)),
            "case_dataset_count": int(len(case_dataset)),
            "account_dataset_count": int(len(account_dataset)),
        },
        metadata={
            "label_version": resolved.label_version,
            "dataset_version": resolved.dataset_version,
        },
    )


def build_and_persist_label_datasets(
    engine: Engine,
    label_config: AnalystLabelConfig | None = None,
    persistence_config: object | None = None,
    limit: int | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> tuple[LabelDatasetBuildResult, object]:
    """Read, build, validate, and persist analyst label datasets."""

    try:
        from graph_aml.labels.persistence import LabelPersistenceConfig, persist_label_datasets
        from graph_aml.labels.validation import validate_label_dataset_result

        resolved = label_config or AnalystLabelConfig()
        inputs = read_label_inputs(engine, resolved, limit=limit)
        result = build_label_datasets_from_inputs(inputs, resolved)
        validate_label_dataset_result(result, resolved)
        persist_config = (
            persistence_config
            if isinstance(persistence_config, LabelPersistenceConfig)
            else LabelPersistenceConfig(
                label_version=resolved.label_version,
                dataset_version=resolved.dataset_version,
            )
        )
        persisted = persist_label_datasets(engine, result, persist_config, extra_metadata)
        return result, persisted
    except LabelError:
        raise
    except Exception as exc:
        raise LabelDatasetError(f"failed to build and persist label datasets: {exc}") from exc
