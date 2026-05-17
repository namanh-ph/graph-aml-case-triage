from __future__ import annotations

import pandas as pd

from graph_aml.labels import (
    ACCOUNT_LABEL_COLUMNS,
    AnalystLabelConfig,
    LabelPropagationConfig,
    build_account_labels,
)


def _case_labels() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": ["C1", "C2"],
            "label_version": ["v1", "v1"],
            "case_label": [0, 1],
            "label_name": ["false_positive", "suspicious"],
            "label_timestamp": [
                pd.Timestamp("2026-01-02", tz="UTC"),
                pd.Timestamp("2026-01-03", tz="UTC"),
            ],
        }
    )


def _cases() -> pd.DataFrame:
    return pd.DataFrame({"case_id": ["C1", "C2"], "primary_account_id": ["A1", "A1"]})


def _entities() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": ["C1", "C2"],
            "entity_type": ["account", "account"],
            "entity_id": ["A2", "A3"],
            "relationship": ["related", "related"],
        }
    )


def test_primary_account_labels_are_propagated() -> None:
    labels = build_account_labels(_case_labels(), _cases(), pd.DataFrame())
    assert "A1" in set(labels["account_id"])


def test_related_account_labels_are_propagated_when_enabled() -> None:
    labels = build_account_labels(_case_labels(), _cases(), _entities())
    assert {"A2", "A3"} <= set(labels["account_id"])


def test_max_case_label_strategy_prefers_suspicious() -> None:
    label = build_account_labels(_case_labels(), _cases(), _entities())
    assert int(label[label["account_id"] == "A1"].iloc[0]["account_label"]) == 1


def test_latest_case_label_strategy_uses_latest_timestamp() -> None:
    config = AnalystLabelConfig(
        propagation=LabelPropagationConfig(account_label_strategy="latest_case_label")
    )
    label = build_account_labels(_case_labels(), _cases(), _entities(), config)
    assert int(label[label["account_id"] == "A1"].iloc[0]["account_label"]) == 1


def test_any_suspicious_strategy_flags_suspicious() -> None:
    config = AnalystLabelConfig(
        propagation=LabelPropagationConfig(account_label_strategy="any_suspicious")
    )
    label = build_account_labels(_case_labels(), _cases(), _entities(), config)
    assert int(label[label["account_id"] == "A1"].iloc[0]["account_label"]) == 1


def test_source_case_ids_are_retained() -> None:
    label = build_account_labels(_case_labels(), _cases(), _entities())
    assert "C1" in label[label["account_id"] == "A1"].iloc[0]["source_case_ids"]


def test_source_case_labels_are_retained() -> None:
    label = build_account_labels(_case_labels(), _cases(), _entities())
    assert 1 in label[label["account_id"] == "A1"].iloc[0]["source_case_labels"]


def test_account_label_output_columns_equal_constant() -> None:
    columns = tuple(build_account_labels(_case_labels(), _cases(), _entities()).columns)
    assert columns == ACCOUNT_LABEL_COLUMNS


def test_input_dataframes_are_not_mutated() -> None:
    labels = _case_labels()
    cases = _cases()
    entities = _entities()
    expected = (labels.copy(deep=True), cases.copy(deep=True), entities.copy(deep=True))
    build_account_labels(labels, cases, entities)
    pd.testing.assert_frame_equal(labels, expected[0])
    pd.testing.assert_frame_equal(cases, expected[1])
    pd.testing.assert_frame_equal(entities, expected[2])
