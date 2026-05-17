"""Persistence utilities for analyst labels and supervised-readiness datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.labels.dataset import (
    ACCOUNT_SUPERVISED_DATASET_COLUMNS,
    CASE_SUPERVISED_DATASET_COLUMNS,
    LabelDatasetBuildResult,
)
from graph_aml.labels.exceptions import LabelPersistenceError
from graph_aml.labels.mapping import ACCOUNT_LABEL_COLUMNS, CASE_LABEL_COLUMNS


@dataclass(frozen=True)
class LabelPersistenceConfig:
    label_version: str = "analyst_feedback_v1"
    dataset_version: str = "supervised_readiness_v1"
    batch_size: int = 1000
    write_audit: bool = True


@dataclass(frozen=True)
class LabelPersistenceResult:
    case_labels_persisted: int = 0
    account_labels_persisted: int = 0
    case_dataset_rows_persisted: int = 0
    account_dataset_rows_persisted: int = 0
    label_version: str | None = None
    dataset_version: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def validate_label_persistence_config(config: LabelPersistenceConfig) -> None:
    if not config.label_version.strip():
        raise LabelPersistenceError("label_version must be non-empty")
    if not config.dataset_version.strip():
        raise LabelPersistenceError("dataset_version must be non-empty")
    if config.batch_size <= 0:
        raise LabelPersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise LabelPersistenceError("write_audit must be boolean")


def _jsonify(value: object) -> object:
    if isinstance(value, dict | list | tuple):
        return json.dumps(value, sort_keys=True, default=str)
    return value


def _prepare(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    prepared = frame.copy(deep=True) if isinstance(frame, pd.DataFrame) else pd.DataFrame()
    for column in columns:
        if column not in prepared.columns:
            prepared[column] = None
    return prepared.loc[:, list(columns)].copy()


def prepare_label_frames_for_persistence(
    result: LabelDatasetBuildResult,
    config: LabelPersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> dict[str, pd.DataFrame]:
    resolved = config or LabelPersistenceConfig()
    validate_label_persistence_config(resolved)
    metadata = extra_metadata or {}
    frames = {
        "case_labels": _prepare(result.case_labels, CASE_LABEL_COLUMNS),
        "account_labels": _prepare(result.account_labels, ACCOUNT_LABEL_COLUMNS),
        "case_dataset": _prepare(result.case_dataset, CASE_SUPERVISED_DATASET_COLUMNS),
        "account_dataset": _prepare(result.account_dataset, ACCOUNT_SUPERVISED_DATASET_COLUMNS),
    }
    for name, frame in frames.items():
        if name.endswith("labels"):
            frame["label_version"] = resolved.label_version
        else:
            frame["dataset_version"] = resolved.dataset_version
        if "metadata" in frame.columns:
            frame["metadata"] = frame["metadata"].map(lambda value: _jsonify(value or metadata))
    return frames


def build_case_label_upsert_sql() -> str:
    return """
        INSERT INTO aml.case_labels (
            case_id, label_version, case_label, label_name, source_status, source_action_type,
            analyst_id, decision_reason, comment, label_timestamp, case_created_at,
            case_updated_at, metadata
        ) VALUES (
            :case_id, :label_version, :case_label, :label_name, :source_status,
            :source_action_type, :analyst_id, :decision_reason, :comment, :label_timestamp,
            :case_created_at, :case_updated_at, CAST(:metadata AS jsonb)
        )
        ON CONFLICT (case_id, label_version) DO UPDATE SET
            case_label = EXCLUDED.case_label,
            label_name = EXCLUDED.label_name,
            source_status = EXCLUDED.source_status,
            source_action_type = EXCLUDED.source_action_type,
            analyst_id = EXCLUDED.analyst_id,
            decision_reason = EXCLUDED.decision_reason,
            comment = EXCLUDED.comment,
            label_timestamp = EXCLUDED.label_timestamp,
            case_created_at = EXCLUDED.case_created_at,
            case_updated_at = EXCLUDED.case_updated_at,
            metadata = EXCLUDED.metadata,
            updated_at = CURRENT_TIMESTAMP
    """


def build_account_label_upsert_sql() -> str:
    return """
        INSERT INTO aml.account_labels (
            account_id, label_version, account_label, label_name, source_case_ids,
            source_case_labels, label_timestamp, metadata
        ) VALUES (
            :account_id, :label_version, :account_label, :label_name,
            CAST(:source_case_ids AS jsonb), CAST(:source_case_labels AS jsonb),
            :label_timestamp, CAST(:metadata AS jsonb)
        )
        ON CONFLICT (account_id, label_version) DO UPDATE SET
            account_label = EXCLUDED.account_label,
            label_name = EXCLUDED.label_name,
            source_case_ids = EXCLUDED.source_case_ids,
            source_case_labels = EXCLUDED.source_case_labels,
            label_timestamp = EXCLUDED.label_timestamp,
            metadata = EXCLUDED.metadata,
            updated_at = CURRENT_TIMESTAMP
    """


def build_case_supervised_dataset_upsert_sql() -> str:
    return """
        INSERT INTO mart.case_supervised_dataset (
            case_id, dataset_version, case_label, label_name, label_timestamp,
            case_risk_score, risk_band, alert_count, typology_count, related_account_count,
            evidence_transaction_count, total_transaction_value, component_coverage
        ) VALUES (
            :case_id, :dataset_version, :case_label, :label_name, :label_timestamp,
            :case_risk_score, :risk_band, :alert_count, :typology_count,
            :related_account_count, :evidence_transaction_count, :total_transaction_value,
            :component_coverage
        )
        ON CONFLICT (case_id, dataset_version) DO UPDATE SET
            case_label = EXCLUDED.case_label,
            label_name = EXCLUDED.label_name,
            label_timestamp = EXCLUDED.label_timestamp,
            case_risk_score = EXCLUDED.case_risk_score,
            risk_band = EXCLUDED.risk_band,
            alert_count = EXCLUDED.alert_count,
            typology_count = EXCLUDED.typology_count,
            related_account_count = EXCLUDED.related_account_count,
            evidence_transaction_count = EXCLUDED.evidence_transaction_count,
            total_transaction_value = EXCLUDED.total_transaction_value,
            component_coverage = EXCLUDED.component_coverage,
            updated_at = CURRENT_TIMESTAMP
    """


def build_account_supervised_dataset_upsert_sql() -> str:
    return """
        INSERT INTO mart.account_supervised_dataset (
            account_id, dataset_version, account_label, label_name, label_timestamp,
            account_risk_score, risk_band, anomaly_score, graph_risk_score, rule_risk_score,
            customer_risk_score, jurisdiction_risk_score, degree_centrality, pagerank_score,
            betweenness_centrality, cycle_count, community_size
        ) VALUES (
            :account_id, :dataset_version, :account_label, :label_name, :label_timestamp,
            :account_risk_score, :risk_band, :anomaly_score, :graph_risk_score,
            :rule_risk_score, :customer_risk_score, :jurisdiction_risk_score,
            :degree_centrality, :pagerank_score, :betweenness_centrality, :cycle_count,
            :community_size
        )
        ON CONFLICT (account_id, dataset_version) DO UPDATE SET
            account_label = EXCLUDED.account_label,
            label_name = EXCLUDED.label_name,
            label_timestamp = EXCLUDED.label_timestamp,
            account_risk_score = EXCLUDED.account_risk_score,
            risk_band = EXCLUDED.risk_band,
            anomaly_score = EXCLUDED.anomaly_score,
            graph_risk_score = EXCLUDED.graph_risk_score,
            rule_risk_score = EXCLUDED.rule_risk_score,
            customer_risk_score = EXCLUDED.customer_risk_score,
            jurisdiction_risk_score = EXCLUDED.jurisdiction_risk_score,
            degree_centrality = EXCLUDED.degree_centrality,
            pagerank_score = EXCLUDED.pagerank_score,
            betweenness_centrality = EXCLUDED.betweenness_centrality,
            cycle_count = EXCLUDED.cycle_count,
            community_size = EXCLUDED.community_size,
            updated_at = CURRENT_TIMESTAMP
    """


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    records = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
    return [{str(key): _jsonify(value) for key, value in record.items()} for record in records]


def upsert_label_frame(
    engine: Engine,
    frame: pd.DataFrame,
    sql: str,
    batch_size: int = 1000,
) -> int:
    if frame.empty:
        return 0
    try:
        records = _records(frame)
        count = 0
        with engine.begin() as connection:
            for start in range(0, len(records), batch_size):
                batch = records[start : start + batch_size]
                connection.execute(text(sql), batch)
                count += len(batch)
        return count
    except Exception as exc:
        raise LabelPersistenceError(f"failed to upsert label frame: {exc}") from exc


def persist_label_datasets(
    engine: Engine,
    result: LabelDatasetBuildResult,
    config: LabelPersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> LabelPersistenceResult:
    resolved = config or LabelPersistenceConfig()
    validate_label_persistence_config(resolved)
    frames = prepare_label_frames_for_persistence(result, resolved, extra_metadata)
    persisted = LabelPersistenceResult(
        case_labels_persisted=upsert_label_frame(
            engine,
            frames["case_labels"],
            build_case_label_upsert_sql(),
            resolved.batch_size,
        ),
        account_labels_persisted=upsert_label_frame(
            engine,
            frames["account_labels"],
            build_account_label_upsert_sql(),
            resolved.batch_size,
        ),
        case_dataset_rows_persisted=upsert_label_frame(
            engine,
            frames["case_dataset"],
            build_case_supervised_dataset_upsert_sql(),
            resolved.batch_size,
        ),
        account_dataset_rows_persisted=upsert_label_frame(
            engine,
            frames["account_dataset"],
            build_account_supervised_dataset_upsert_sql(),
            resolved.batch_size,
        ),
        label_version=resolved.label_version,
        dataset_version=resolved.dataset_version,
        persisted=True,
        metadata=extra_metadata or {},
        summary=result.summary,
    )
    if resolved.write_audit:
        write_label_generation_audit_event(engine, persisted)
    return persisted


def write_label_generation_audit_event(
    engine: Engine,
    result: LabelPersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    sql = """
        INSERT INTO governance.audit_events (
            event_timestamp, event_type, component, run_id, action, status, details, created_by
        ) VALUES (
            :event_timestamp, :event_type, :component, :run_id, :action, :status,
            CAST(:details AS jsonb), :created_by
        )
    """
    details = {
        "case_labels_persisted": result.case_labels_persisted,
        "account_labels_persisted": result.account_labels_persisted,
        "case_dataset_rows_persisted": result.case_dataset_rows_persisted,
        "account_dataset_rows_persisted": result.account_dataset_rows_persisted,
        "label_version": result.label_version,
        "dataset_version": result.dataset_version,
        "summary": result.summary,
        "metadata": result.metadata,
    }
    try:
        with engine.begin() as connection:
            connection.execute(
                text(sql),
                {
                    "event_timestamp": datetime.now(UTC),
                    "event_type": "analyst_label_generation",
                    "component": "labels",
                    "run_id": run_id,
                    "action": "persist_analyst_feedback_labels",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise LabelPersistenceError(f"failed to write label audit event: {exc}") from exc
