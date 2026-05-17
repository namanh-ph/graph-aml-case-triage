from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.labels import (
    ACCOUNT_SUPERVISED_DATASET_COLUMNS,
    CASE_SUPERVISED_DATASET_COLUMNS,
    LabelDatasetBuildResult,
    LabelDatasetError,
    build_account_supervised_dataset,
    build_case_supervised_dataset,
    build_label_datasets_from_inputs,
)


def _case_labels() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": ["C1"],
            "case_label": [1],
            "label_name": ["suspicious"],
            "label_timestamp": [pd.Timestamp("2026-01-05", tz="UTC")],
        }
    )


def _account_labels() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": ["A1"],
            "account_label": [1],
            "label_name": ["suspicious"],
            "label_timestamp": [pd.Timestamp("2026-01-05", tz="UTC")],
        }
    )


def _case_scores() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": ["C1", "C1"],
            "case_risk_score": [70.0, 90.0],
            "risk_band": ["high", "critical"],
            "alert_count": [1, 2],
            "typology_count": [1, 2],
            "related_account_count": [1, 2],
            "evidence_transaction_count": [3, 4],
            "total_transaction_value": [100.0, 200.0],
            "component_coverage": [0.8, 1.0],
            "scored_at": [
                pd.Timestamp("2026-01-03", tz="UTC"),
                pd.Timestamp("2026-01-04", tz="UTC"),
            ],
        }
    )


def _account_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features = pd.DataFrame({"account_id": ["A1"], "feature_date": [pd.Timestamp("2026-01-01")]})
    risk = pd.DataFrame(
        {
            "account_id": ["A1"],
            "account_risk_score": [80.0],
            "risk_band": ["high"],
            "rule_risk_score": [70.0],
            "customer_risk_score": [30.0],
            "jurisdiction_risk_score": [20.0],
            "scored_at": [pd.Timestamp("2026-01-03", tz="UTC")],
        }
    )
    graph = pd.DataFrame(
        {
            "account_id": ["A1"],
            "graph_risk_score": [75.0],
            "degree_centrality": [0.1],
            "pagerank_score": [0.2],
            "betweenness_centrality": [0.3],
            "cycle_count": [2],
            "community_size": [5],
            "computed_at": [pd.Timestamp("2026-01-03", tz="UTC")],
        }
    )
    anomaly = pd.DataFrame(
        {
            "account_id": ["A1"],
            "anomaly_score": [65.0],
            "score_date": [pd.Timestamp("2026-01-03")],
        }
    )
    return features, risk, graph, anomaly


def test_case_supervised_dataset_joins_case_labels_to_scores() -> None:
    dataset = build_case_supervised_dataset(_case_labels(), _case_scores())
    assert float(dataset.iloc[0]["case_risk_score"]) == 90.0


def test_account_supervised_dataset_joins_feature_rows() -> None:
    dataset = build_account_supervised_dataset(_account_labels(), *_account_frames())
    assert float(dataset.iloc[0]["account_risk_score"]) == 80.0
    assert float(dataset.iloc[0]["anomaly_score"]) == 65.0


def test_latest_score_rows_are_selected_deterministically() -> None:
    dataset = build_case_supervised_dataset(_case_labels(), _case_scores())
    assert dataset.iloc[0]["risk_band"] == "critical"


def test_case_dataset_columns_equal_constant() -> None:
    columns = tuple(build_case_supervised_dataset(_case_labels(), _case_scores()).columns)
    assert columns == CASE_SUPERVISED_DATASET_COLUMNS


def test_account_dataset_columns_equal_constant() -> None:
    columns = tuple(build_account_supervised_dataset(_account_labels(), *_account_frames()).columns)
    assert columns == ACCOUNT_SUPERVISED_DATASET_COLUMNS


def test_missing_features_are_preserved_as_missing_values() -> None:
    dataset = build_account_supervised_dataset(
        _account_labels(),
        pd.DataFrame(columns=["account_id"]),
        pd.DataFrame(columns=["account_id"]),
        pd.DataFrame(columns=["account_id"]),
        pd.DataFrame(columns=["account_id"]),
    )
    assert pd.isna(dataset.iloc[0]["account_risk_score"])


def test_feature_timestamp_leakage_checks_are_applied() -> None:
    features, risk, graph, anomaly = _account_frames()
    risk.loc[0, "scored_at"] = pd.Timestamp("2026-01-06", tz="UTC")
    with pytest.raises(LabelDatasetError):
        build_account_supervised_dataset(_account_labels(), features, risk, graph, anomaly)


def test_high_level_dataset_builder_returns_result() -> None:
    inputs = {
        "cases": pd.DataFrame(
            {
                "case_id": ["C1"],
                "primary_account_id": ["A1"],
                "created_at": [pd.Timestamp("2026-01-01", tz="UTC")],
                "updated_at": [pd.Timestamp("2026-01-02", tz="UTC")],
            }
        ),
        "lifecycle_events": pd.DataFrame(
            {
                "action_id": ["E1"],
                "case_id": ["C1"],
                "to_status": ["Closed suspicious"],
                "action_type": ["close_suspicious"],
                "analyst_id": ["u1"],
                "decision_reason": ["reason"],
                "comment": ["comment"],
                "action_timestamp": [pd.Timestamp("2026-01-05", tz="UTC")],
            }
        ),
        "case_entities": pd.DataFrame(columns=["case_id", "entity_type", "entity_id"]),
        "case_risk_scores": _case_scores(),
        "account_features": _account_frames()[0],
        "account_risk_scores": _account_frames()[1],
        "graph_features": _account_frames()[2],
        "anomaly_scores": _account_frames()[3],
    }
    assert isinstance(build_label_datasets_from_inputs(inputs), LabelDatasetBuildResult)


def test_input_dataframes_are_not_mutated() -> None:
    labels = _case_labels()
    scores = _case_scores()
    expected = (labels.copy(deep=True), scores.copy(deep=True))
    build_case_supervised_dataset(labels, scores)
    pd.testing.assert_frame_equal(labels, expected[0])
    pd.testing.assert_frame_equal(scores, expected[1])


def test_malformed_inputs_raise_label_dataset_error() -> None:
    with pytest.raises(LabelDatasetError):
        build_case_supervised_dataset("bad", pd.DataFrame())  # type: ignore[arg-type]
