"""Feature preprocessing utilities for account anomaly models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import numpy as np
import pandas as pd

from graph_aml.models.config import IsolationForestModelConfig
from graph_aml.models.exceptions import ModelFeatureInputError


@dataclass(frozen=True)
class ModelPreprocessingResult:
    """Reusable preprocessing state and transformed feature matrix."""

    account_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    matrix: object
    imputation_values: dict[str, float] = field(default_factory=dict)
    scaling_values: dict[str, dict[str, float]] = field(default_factory=dict)


def _validate_feature_frame(feature_frame: pd.DataFrame) -> tuple[str, ...]:
    if not isinstance(feature_frame, pd.DataFrame):
        raise ModelFeatureInputError("feature_frame must be a DataFrame")
    if "account_id" not in feature_frame.columns:
        raise ModelFeatureInputError("feature_frame must include account_id")
    if feature_frame["account_id"].isna().any():
        raise ModelFeatureInputError("account_id values must be non-null")
    feature_names = tuple(column for column in feature_frame.columns if column != "account_id")
    if not feature_names:
        raise ModelFeatureInputError("feature_frame must include at least one feature column")
    return feature_names


def _numeric_matrix(frame: pd.DataFrame, feature_names: tuple[str, ...]) -> pd.DataFrame:
    output = frame.loc[:, feature_names].copy()
    for column in feature_names:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    output = output.replace([np.inf, -np.inf], np.nan)
    return output


def _fit_imputation(
    numeric: pd.DataFrame,
    config: IsolationForestModelConfig,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for column in numeric.columns:
        series = numeric[column]
        if config.imputation_strategy == "zero":
            value = 0.0
        elif config.imputation_strategy == "mean":
            value = float(series.mean(skipna=True))
        else:
            value = float(series.median(skipna=True))
        if np.isnan(value):
            value = 0.0
        values[str(column)] = value
    return values


def _apply_imputation(
    numeric: pd.DataFrame,
    imputation_values: dict[str, float],
) -> pd.DataFrame:
    output = numeric.copy()
    for column in output.columns:
        output[column] = output[column].fillna(imputation_values[str(column)])
    if output.isna().any().any():
        raise ModelFeatureInputError("missing numeric values remain after imputation")
    return output.astype("float64")


def _fit_scaling(
    numeric: pd.DataFrame,
    config: IsolationForestModelConfig,
) -> dict[str, dict[str, float]]:
    values: dict[str, dict[str, float]] = {}
    for column in numeric.columns:
        series = numeric[column].astype("float64")
        if config.scaling_strategy == "none":
            center = 0.0
            scale = 1.0
        elif config.scaling_strategy == "robust":
            center = float(series.median())
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            scale = q3 - q1
        else:
            center = float(series.mean())
            scale = float(series.std(ddof=0))
        if not np.isfinite(scale) or scale == 0:
            scale = 1.0
        if not np.isfinite(center):
            center = 0.0
        values[str(column)] = {
            "center": center,
            "scale": scale,
        }
    return values


def _apply_scaling(
    numeric: pd.DataFrame,
    scaling_values: dict[str, dict[str, float]],
) -> np.ndarray:
    output = numeric.copy()
    for column in output.columns:
        values = scaling_values[str(column)]
        output[column] = (output[column] - values["center"]) / values["scale"]
    matrix = cast(np.ndarray, output.to_numpy(dtype=float))
    if not np.isfinite(matrix).all():
        raise ModelFeatureInputError("invalid numeric values remain after preprocessing")
    return matrix


def fit_transform_model_features(
    feature_frame: pd.DataFrame,
    config: IsolationForestModelConfig | None = None,
) -> ModelPreprocessingResult:
    """Fit imputation and scaling state, then return a numeric model matrix."""

    resolved = IsolationForestModelConfig() if config is None else config
    feature_names = _validate_feature_frame(feature_frame)
    frame = feature_frame.copy()
    account_ids = tuple(str(value) for value in frame["account_id"])
    numeric = _numeric_matrix(frame, feature_names)
    imputation_values = _fit_imputation(numeric, resolved)
    imputed = _apply_imputation(numeric, imputation_values)
    scaling_values = _fit_scaling(imputed, resolved)
    matrix = _apply_scaling(imputed, scaling_values)
    return ModelPreprocessingResult(
        account_ids=account_ids,
        feature_names=feature_names,
        matrix=matrix,
        imputation_values=imputation_values,
        scaling_values=scaling_values,
    )


def transform_model_features(
    feature_frame: pd.DataFrame,
    preprocessing: ModelPreprocessingResult,
    config: IsolationForestModelConfig | None = None,
) -> ModelPreprocessingResult:
    """Apply previously fitted preprocessing state to a feature frame."""

    _ = IsolationForestModelConfig() if config is None else config
    _validate_feature_frame(feature_frame)
    missing = set(preprocessing.feature_names).difference(feature_frame.columns)
    if missing:
        raise ModelFeatureInputError(f"feature_frame is missing fitted features: {sorted(missing)}")
    frame = feature_frame.copy()
    account_ids = tuple(str(value) for value in frame["account_id"])
    numeric = _numeric_matrix(frame, preprocessing.feature_names)
    imputed = _apply_imputation(numeric, preprocessing.imputation_values)
    matrix = _apply_scaling(imputed, preprocessing.scaling_values)
    return ModelPreprocessingResult(
        account_ids=account_ids,
        feature_names=preprocessing.feature_names,
        matrix=matrix,
        imputation_values=dict(preprocessing.imputation_values),
        scaling_values={key: dict(value) for key, value in preprocessing.scaling_values.items()},
    )
