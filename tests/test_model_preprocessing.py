"""Tests for model preprocessing helpers."""

import numpy as np
import pandas as pd
import pytest

from graph_aml.models import (
    IsolationForestModelConfig,
    ModelFeatureInputError,
    fit_transform_model_features,
    transform_model_features,
)


def feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": ["A1", "A2", "A3"],
            "f1": [1.0, None, 3.0],
            "f2": [10.0, 20.0, 30.0],
        }
    )


def test_fit_transform_returns_ids_names_and_numeric_matrix() -> None:
    result = fit_transform_model_features(feature_frame())
    assert result.account_ids == ("A1", "A2", "A3")
    assert result.feature_names == ("f1", "f2")
    assert isinstance(result.matrix, np.ndarray)


@pytest.mark.parametrize("strategy", ["median", "mean", "zero"])
def test_imputation_strategies_work(strategy: str) -> None:
    result = fit_transform_model_features(
        feature_frame(),
        IsolationForestModelConfig(imputation_strategy=strategy),
    )
    assert np.isfinite(result.matrix).all()
    assert set(result.imputation_values) == {"f1", "f2"}


@pytest.mark.parametrize("strategy", ["standard", "robust", "none"])
def test_scaling_strategies_work(strategy: str) -> None:
    result = fit_transform_model_features(
        feature_frame(),
        IsolationForestModelConfig(scaling_strategy=strategy),
    )
    assert np.isfinite(result.matrix).all()
    assert "scale" in result.scaling_values["f1"]


def test_transform_reuses_fitted_values() -> None:
    fitted = fit_transform_model_features(feature_frame())
    transformed = transform_model_features(feature_frame(), fitted)
    assert transformed.feature_names == fitted.feature_names
    assert np.isfinite(transformed.matrix).all()


def test_missing_account_ids_raise() -> None:
    frame = feature_frame()
    frame.loc[0, "account_id"] = None
    with pytest.raises(ModelFeatureInputError):
        fit_transform_model_features(frame)


def test_input_dataframe_is_not_mutated() -> None:
    frame = feature_frame()
    original = frame.copy(deep=True)
    fit_transform_model_features(frame)
    pd.testing.assert_frame_equal(frame, original)
