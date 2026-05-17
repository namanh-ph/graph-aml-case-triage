"""Feature matrix construction for supervised AML models."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from sklearn.model_selection import train_test_split

from graph_aml.models.supervised_config import SupervisedModelConfig
from graph_aml.models.supervised_exceptions import SupervisedFeatureError


@dataclass(frozen=True)
class SupervisedFeatureMatrix:
    entity_ids: pd.Series
    labels: pd.Series
    features: pd.DataFrame
    timestamps: pd.Series
    feature_names: tuple[str, ...]
    metadata: dict[str, object] = field(default_factory=dict)


def _config(config: SupervisedModelConfig | None) -> SupervisedModelConfig:
    return config or SupervisedModelConfig()


def infer_supervised_feature_columns(
    dataset: pd.DataFrame,
    config: SupervisedModelConfig | None = None,
) -> tuple[str, ...]:
    """Infer numeric modelling columns from a supervised-readiness dataset."""

    resolved = _config(config)
    if not isinstance(dataset, pd.DataFrame):
        raise SupervisedFeatureError("dataset must be a DataFrame")
    excluded = {
        resolved.dataset.id_column,
        resolved.dataset.label_column,
        "label_name",
        resolved.dataset.timestamp_column,
        "dataset_version",
        "metadata",
        "created_at",
        "updated_at",
    }
    columns: list[str] = []
    for column in dataset.columns:
        if column in excluded:
            continue
        series = pd.to_numeric(dataset[column], errors="coerce")
        if series.notna().any():
            columns.append(str(column))
    return tuple(columns)


def build_supervised_feature_matrix(
    dataset: pd.DataFrame,
    config: SupervisedModelConfig | None = None,
) -> SupervisedFeatureMatrix:
    """Build an immutable supervised feature matrix wrapper."""

    resolved = _config(config)
    if not isinstance(dataset, pd.DataFrame):
        raise SupervisedFeatureError("dataset must be a DataFrame")
    required = {
        resolved.dataset.id_column,
        resolved.dataset.label_column,
        resolved.dataset.timestamp_column,
    }
    missing = required.difference(dataset.columns)
    if missing:
        raise SupervisedFeatureError(f"dataset missing required columns: {sorted(missing)}")
    feature_names = infer_supervised_feature_columns(dataset, resolved)
    if not feature_names:
        raise SupervisedFeatureError("no numeric features are available")
    frame = dataset.copy(deep=True)
    features = frame.loc[:, list(feature_names)].apply(pd.to_numeric, errors="coerce")
    labels = pd.to_numeric(frame[resolved.dataset.label_column], errors="coerce")
    return SupervisedFeatureMatrix(
        entity_ids=frame[resolved.dataset.id_column].astype(str).reset_index(drop=True),
        labels=labels.astype("Int64").reset_index(drop=True),
        features=features.reset_index(drop=True),
        timestamps=frame[resolved.dataset.timestamp_column].reset_index(drop=True),
        feature_names=feature_names,
        metadata={
            "dataset_version": resolved.dataset.dataset_version,
            "entity_level": resolved.dataset.level,
            "label_column": resolved.dataset.label_column,
        },
    )


def validate_supervised_training_data(
    matrix: SupervisedFeatureMatrix,
    config: SupervisedModelConfig | None = None,
) -> None:
    """Validate row, class, and feature requirements."""

    resolved = _config(config)
    row_count = len(matrix.features)
    if row_count < resolved.dataset.min_rows:
        raise SupervisedFeatureError("not enough labelled rows for supervised training")
    labels = pd.to_numeric(matrix.labels, errors="coerce")
    valid = set(labels.dropna().astype(int).unique().tolist())
    if not valid.issubset({0, 1}):
        raise SupervisedFeatureError("labels must be binary 0/1")
    positives = int((labels == 1).sum())
    negatives = int((labels == 0).sum())
    if positives < resolved.dataset.min_positive_labels:
        raise SupervisedFeatureError("positive label count below threshold")
    if negatives < resolved.dataset.min_negative_labels:
        raise SupervisedFeatureError("negative label count below threshold")
    if not resolved.dataset.allow_single_class_training and (positives == 0 or negatives == 0):
        raise SupervisedFeatureError("single-class supervised training is disabled")
    if matrix.features.empty or len(matrix.feature_names) == 0:
        raise SupervisedFeatureError("feature matrix is empty")


def _subset(matrix: SupervisedFeatureMatrix, indices: list[int]) -> SupervisedFeatureMatrix:
    return SupervisedFeatureMatrix(
        entity_ids=matrix.entity_ids.take(indices).reset_index(drop=True),
        labels=matrix.labels.take(indices).reset_index(drop=True),
        features=matrix.features.iloc[indices].reset_index(drop=True),
        timestamps=matrix.timestamps.take(indices).reset_index(drop=True),
        feature_names=matrix.feature_names,
        metadata=dict(matrix.metadata),
    )


def split_supervised_feature_matrix(
    matrix: SupervisedFeatureMatrix,
    config: SupervisedModelConfig | None = None,
) -> dict[str, object]:
    """Split supervised features into train and validation partitions."""

    resolved = _config(config)
    validate_supervised_training_data(matrix, resolved)
    row_count = len(matrix.features)
    validation_rows = max(
        resolved.split.min_validation_rows,
        int(round(row_count * resolved.split.validation_fraction)),
    )
    validation_rows = min(max(1, validation_rows), row_count - 1)
    if resolved.split.strategy == "time":
        order = (
            pd.DataFrame({"timestamp": pd.to_datetime(matrix.timestamps, errors="coerce")})
            .sort_values("timestamp", kind="mergesort")
            .index.tolist()
        )
        train_idx = order[:-validation_rows]
        validation_idx = order[-validation_rows:]
    else:
        indices = list(range(row_count))
        try:
            train_idx, validation_idx = train_test_split(
                indices,
                test_size=validation_rows,
                random_state=resolved.random_seed,
                stratify=matrix.labels.astype(int),
            )
        except ValueError:
            train_idx, validation_idx = train_test_split(
                indices,
                test_size=validation_rows,
                random_state=resolved.random_seed,
                shuffle=True,
            )
    return {
        "train": _subset(matrix, list(train_idx)),
        "validation": _subset(matrix, list(validation_idx)),
        "train_row_count": int(len(train_idx)),
        "validation_row_count": int(len(validation_idx)),
        "strategy": resolved.split.strategy,
    }
