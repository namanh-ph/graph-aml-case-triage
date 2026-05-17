"""Training workflow for supervised AML baseline models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import Engine

from graph_aml.models.supervised_config import SupervisedModelConfig
from graph_aml.models.supervised_exceptions import (
    SupervisedFeatureError,
    SupervisedTrainingError,
)
from graph_aml.models.supervised_features import (
    SupervisedFeatureMatrix,
    build_supervised_feature_matrix,
    split_supervised_feature_matrix,
    validate_supervised_training_data,
)
from graph_aml.models.supervised_inputs import read_supervised_training_dataset
from graph_aml.models.supervised_scoring import (
    compute_binary_classification_metrics,
    compute_precision_recall_at_k,
    compute_threshold_metrics,
    score_supervised_dataset,
)

if TYPE_CHECKING:
    from graph_aml.models.supervised_persistence import (
        SupervisedModelPersistenceConfig,
        SupervisedModelPersistenceResult,
    )


@dataclass(frozen=True)
class SupervisedTrainingResult:
    model_name: str
    model_version: str
    model_family: str
    estimator: object
    preprocessing_pipeline: object
    feature_names: tuple[str, ...]
    train_metrics: dict[str, object] = field(default_factory=dict)
    validation_metrics: dict[str, object] = field(default_factory=dict)
    threshold_metrics: pd.DataFrame = field(default_factory=pd.DataFrame)
    top_k_metrics: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata: dict[str, object] = field(default_factory=dict)


def _config(config: SupervisedModelConfig | None) -> SupervisedModelConfig:
    return config or SupervisedModelConfig()


def build_supervised_preprocessing_pipeline(
    config: SupervisedModelConfig | None = None,
) -> object:
    """Build the numeric preprocessing pipeline."""

    resolved = _config(config)
    strategy = resolved.preprocessing.numeric_imputation
    imputer_strategy = "constant" if strategy == "zero" else strategy
    steps: list[tuple[str, object]] = [
        ("imputer", SimpleImputer(strategy=imputer_strategy, fill_value=0.0)),
    ]
    if resolved.preprocessing.standardise_numeric:
        steps.append(("scaler", StandardScaler()))
    return Pipeline(steps)


def build_supervised_estimator(
    config: SupervisedModelConfig | None = None,
) -> object:
    """Build the configured supervised estimator."""

    resolved = _config(config)
    if resolved.model_family == "random_forest":
        return RandomForestClassifier(
            n_estimators=resolved.random_forest.n_estimators,
            max_depth=resolved.random_forest.max_depth,
            min_samples_leaf=resolved.random_forest.min_samples_leaf,
            class_weight=resolved.random_forest.class_weight,
            n_jobs=resolved.random_forest.n_jobs,
            random_state=resolved.random_seed,
        )
    return LogisticRegression(
        penalty=resolved.logistic_regression.penalty,
        C=resolved.logistic_regression.C,
        class_weight=resolved.logistic_regression.class_weight,
        max_iter=resolved.logistic_regression.max_iter,
        solver="liblinear" if resolved.logistic_regression.penalty == "l1" else "lbfgs",
        random_state=resolved.random_seed,
    )


def _drop_unusable_features(
    train: SupervisedFeatureMatrix,
    validation: SupervisedFeatureMatrix,
    config: SupervisedModelConfig,
) -> tuple[SupervisedFeatureMatrix, SupervisedFeatureMatrix]:
    features = train.features.copy(deep=True)
    keep = list(features.columns)
    if config.preprocessing.drop_high_missing_features:
        keep = [
            column
            for column in keep
            if float(features[column].isna().mean()) <= config.preprocessing.high_missing_threshold
        ]
    if config.preprocessing.drop_constant_features:
        keep = [column for column in keep if features[column].nunique(dropna=True) > 1]
    if not keep:
        raise SupervisedFeatureError("all supervised features were dropped")

    def subset(matrix: SupervisedFeatureMatrix) -> SupervisedFeatureMatrix:
        return SupervisedFeatureMatrix(
            entity_ids=matrix.entity_ids,
            labels=matrix.labels,
            features=matrix.features.loc[:, keep].copy(deep=True),
            timestamps=matrix.timestamps,
            feature_names=tuple(str(column) for column in keep),
            metadata=dict(matrix.metadata),
        )

    return subset(train), subset(validation)


def _scores_for(estimator: object, pipeline: object, features: pd.DataFrame) -> pd.Series:
    fitted_pipeline = cast(Any, pipeline)
    fitted_estimator = cast(Any, estimator)
    transformed = fitted_pipeline.transform(features)
    if hasattr(fitted_estimator, "predict_proba"):
        probabilities = fitted_estimator.predict_proba(transformed)
        if probabilities.shape[1] == 1:
            value = (
                float(fitted_estimator.classes_[0])
                if hasattr(fitted_estimator, "classes_")
                else 0.0
            )
            return pd.Series([value] * len(features))
        return pd.Series(probabilities[:, 1])
    return pd.Series(fitted_estimator.predict(transformed)).astype(float)


def train_supervised_model(
    split_data: dict[str, object],
    config: SupervisedModelConfig | None = None,
) -> SupervisedTrainingResult:
    """Train the configured supervised model and compute validation metrics."""

    resolved = _config(config)
    try:
        train = split_data["train"]
        validation = split_data["validation"]
        if not isinstance(train, SupervisedFeatureMatrix) or not isinstance(
            validation,
            SupervisedFeatureMatrix,
        ):
            raise SupervisedTrainingError("split_data must contain feature matrices")
        train, validation = _drop_unusable_features(train, validation, resolved)
        pipeline = build_supervised_preprocessing_pipeline(resolved)
        x_train = cast(Any, pipeline).fit_transform(train.features)
        y_train = train.labels.astype(int)
        if y_train.nunique() < 2 and resolved.dataset.allow_single_class_training:
            estimator = DummyClassifier(strategy="most_frequent")
        else:
            estimator = build_supervised_estimator(resolved)
        estimator.fit(x_train, y_train)
        train_scores = _scores_for(estimator, pipeline, train.features)
        validation_scores = _scores_for(estimator, pipeline, validation.features)
        train_metrics = compute_binary_classification_metrics(train.labels, train_scores)
        validation_metrics = compute_binary_classification_metrics(
            validation.labels,
            validation_scores,
        )
        threshold_metrics = compute_threshold_metrics(
            validation.labels,
            validation_scores,
            resolved.evaluation.threshold_grid,
        )
        top_k_metrics = compute_precision_recall_at_k(
            validation.labels,
            validation_scores,
            resolved.evaluation.top_k_values,
        )
        return SupervisedTrainingResult(
            model_name=resolved.model_name,
            model_version=resolved.model_version,
            model_family=resolved.model_family,
            estimator=estimator,
            preprocessing_pipeline=pipeline,
            feature_names=train.feature_names,
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
            threshold_metrics=threshold_metrics,
            top_k_metrics=top_k_metrics,
            metadata={
                "dataset_version": resolved.dataset.dataset_version,
                "entity_level": resolved.dataset.level,
                "train_row_count": int(len(train.features)),
                "validation_row_count": int(len(validation.features)),
            },
        )
    except SupervisedTrainingError:
        raise
    except Exception as exc:
        raise SupervisedTrainingError(f"supervised model training failed: {exc}") from exc


def train_and_persist_supervised_model(
    engine: Engine,
    model_config: SupervisedModelConfig | None = None,
    persistence_config: SupervisedModelPersistenceConfig | None = None,
    limit: int | None = None,
    write_artefacts: bool = True,
) -> tuple[SupervisedTrainingResult, pd.DataFrame, SupervisedModelPersistenceResult]:
    """Read labels, train, score, write artefacts, and persist configured outputs."""

    from graph_aml.models.supervised_artefacts import generate_supervised_model_artefacts
    from graph_aml.models.supervised_persistence import (
        SupervisedModelPersistenceConfig,
        log_supervised_model_to_mlflow,
        persist_supervised_model_outputs,
    )
    from graph_aml.models.supervised_validation import validate_supervised_training_result

    resolved = _config(model_config)
    dataset = read_supervised_training_dataset(engine, resolved, limit=limit)
    matrix = build_supervised_feature_matrix(dataset, resolved)
    validate_supervised_training_data(matrix, resolved)
    split_data = split_supervised_feature_matrix(matrix, resolved)
    result = train_supervised_model(split_data, resolved)
    validate_supervised_training_result(result)
    scores = score_supervised_dataset(result, matrix, resolved)
    artefact_paths: dict[str, str] = {}
    if write_artefacts:
        paths = generate_supervised_model_artefacts(
            result,
            scores,
            resolved.persistence.artefact_output_dir,
        )
        artefact_paths = {key: str(path) for key, path in paths.items()}
    if resolved.persistence.write_mlflow:
        mlflow_run_id = log_supervised_model_to_mlflow(result, scores, artefact_paths, resolved)
        if mlflow_run_id:
            artefact_paths["mlflow_run_id"] = mlflow_run_id
    persistence = persistence_config or SupervisedModelPersistenceConfig(
        model_name=resolved.model_name,
        model_version=resolved.model_version,
        dataset_version=resolved.dataset.dataset_version,
        write_scores=resolved.persistence.persist_scores,
    )
    persisted = persist_supervised_model_outputs(
        engine,
        result,
        scores,
        persistence,
        resolved,
        artefact_paths,
    )
    return result, scores, persisted
