"""Configuration for supervised AML baseline models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from graph_aml.models.supervised_exceptions import SupervisedModelConfigurationError


@dataclass(frozen=True)
class SupervisedDatasetConfig:
    level: str = "case"
    dataset_version: str = "supervised_readiness_v1"
    label_column: str = "case_label"
    id_column: str = "case_id"
    timestamp_column: str = "label_timestamp"
    min_rows: int = 10
    min_positive_labels: int = 1
    min_negative_labels: int = 1
    allow_single_class_training: bool = False


@dataclass(frozen=True)
class SupervisedSplitConfig:
    strategy: str = "time"
    validation_fraction: float = 0.25
    min_validation_rows: int = 5


@dataclass(frozen=True)
class SupervisedPreprocessingConfig:
    numeric_imputation: str = "median"
    standardise_numeric: bool = True
    drop_constant_features: bool = True
    drop_high_missing_features: bool = True
    high_missing_threshold: float = 0.95


@dataclass(frozen=True)
class LogisticRegressionConfig:
    enabled: bool = True
    penalty: str = "l2"
    C: float = 1.0
    class_weight: str | None = "balanced"
    max_iter: int = 1000


@dataclass(frozen=True)
class RandomForestConfig:
    enabled: bool = True
    n_estimators: int = 200
    max_depth: int | None = None
    min_samples_leaf: int = 1
    class_weight: str | None = "balanced"
    n_jobs: int = -1


@dataclass(frozen=True)
class SupervisedEvaluationConfig:
    top_k_values: tuple[int, ...] = (10, 25, 50, 100)
    threshold_grid: tuple[float, ...] = (
        0.10,
        0.20,
        0.30,
        0.40,
        0.50,
        0.60,
        0.70,
        0.80,
        0.90,
    )
    primary_metric: str = "precision_at_k"
    primary_top_k: int = 25


@dataclass(frozen=True)
class SupervisedPersistenceConfig:
    persist_scores: bool = True
    write_model_artifact: bool = True
    write_mlflow: bool = True
    artefact_output_dir: str = "reports/model_validation"


@dataclass(frozen=True)
class SupervisedModelConfig:
    model_family: str = "logistic_regression"
    model_name: str = "supervised_aml_baseline"
    model_version: str = "supervised_aml_baseline_v1"
    random_seed: int = 42
    dataset: SupervisedDatasetConfig = field(default_factory=SupervisedDatasetConfig)
    split: SupervisedSplitConfig = field(default_factory=SupervisedSplitConfig)
    preprocessing: SupervisedPreprocessingConfig = field(
        default_factory=SupervisedPreprocessingConfig
    )
    logistic_regression: LogisticRegressionConfig = field(
        default_factory=LogisticRegressionConfig
    )
    random_forest: RandomForestConfig = field(default_factory=RandomForestConfig)
    evaluation: SupervisedEvaluationConfig = field(default_factory=SupervisedEvaluationConfig)
    persistence: SupervisedPersistenceConfig = field(default_factory=SupervisedPersistenceConfig)


def _require_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise SupervisedModelConfigurationError(f"{name} must be boolean")
    return value


def _require_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SupervisedModelConfigurationError(f"{name} must be an integer")
    return int(value)


def _require_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SupervisedModelConfigurationError(f"{name} must be numeric")
    return float(value)


def _tuple_ints(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, list | tuple):
        raise SupervisedModelConfigurationError(f"{name} must be a list")
    values = tuple(int(item) for item in value)
    if any(item <= 0 for item in values) or len(values) != len(set(values)):
        raise SupervisedModelConfigurationError(f"{name} must contain unique positives")
    return values


def _tuple_floats(value: object, name: str) -> tuple[float, ...]:
    if not isinstance(value, list | tuple):
        raise SupervisedModelConfigurationError(f"{name} must be a list")
    values = tuple(float(item) for item in value)
    if any(item < 0 or item > 1 for item in values):
        raise SupervisedModelConfigurationError(f"{name} values must be in [0, 1]")
    return values


def validate_supervised_model_config(config: SupervisedModelConfig) -> None:
    """Validate supervised model configuration without connecting to services."""

    if config.model_family not in {"logistic_regression", "random_forest"}:
        raise SupervisedModelConfigurationError("invalid model_family")
    if not config.model_name.strip() or not config.model_version.strip():
        raise SupervisedModelConfigurationError("model name and version must be non-empty")
    if config.dataset.level not in {"case", "account"}:
        raise SupervisedModelConfigurationError("dataset level must be case or account")
    for field_name in ("dataset_version", "label_column", "id_column", "timestamp_column"):
        if not str(getattr(config.dataset, field_name)).strip():
            raise SupervisedModelConfigurationError(f"dataset.{field_name} must be non-empty")
    for field_name in ("min_rows", "min_positive_labels", "min_negative_labels"):
        value = _require_int(getattr(config.dataset, field_name), f"dataset.{field_name}")
        if value < 0:
            raise SupervisedModelConfigurationError("minimum thresholds must be non-negative")
    _require_bool(config.dataset.allow_single_class_training, "dataset.allow_single_class_training")
    if config.split.strategy not in {"time", "stratified_random"}:
        raise SupervisedModelConfigurationError("invalid split strategy")
    if not 0 < float(config.split.validation_fraction) <= 0.5:
        raise SupervisedModelConfigurationError("validation_fraction must be in (0, 0.5]")
    if _require_int(config.split.min_validation_rows, "split.min_validation_rows") < 0:
        raise SupervisedModelConfigurationError("min_validation_rows must be non-negative")
    if config.preprocessing.numeric_imputation not in {"median", "mean", "zero"}:
        raise SupervisedModelConfigurationError("invalid numeric_imputation")
    _require_bool(config.preprocessing.standardise_numeric, "preprocessing.standardise_numeric")
    _require_bool(config.preprocessing.drop_constant_features, "preprocessing.drop_constant")
    _require_bool(config.preprocessing.drop_high_missing_features, "preprocessing.drop_missing")
    if not 0 < float(config.preprocessing.high_missing_threshold) <= 1:
        raise SupervisedModelConfigurationError("high_missing_threshold must be in (0, 1]")
    _require_bool(config.logistic_regression.enabled, "logistic_regression.enabled")
    if config.logistic_regression.penalty not in {"l1", "l2", "elasticnet", "none"}:
        raise SupervisedModelConfigurationError("invalid logistic penalty")
    if float(config.logistic_regression.C) <= 0:
        raise SupervisedModelConfigurationError("logistic C must be positive")
    if int(config.logistic_regression.max_iter) <= 0:
        raise SupervisedModelConfigurationError("max_iter must be positive")
    _require_bool(config.random_forest.enabled, "random_forest.enabled")
    if int(config.random_forest.n_estimators) <= 0:
        raise SupervisedModelConfigurationError("n_estimators must be positive")
    if config.random_forest.max_depth is not None and int(config.random_forest.max_depth) <= 0:
        raise SupervisedModelConfigurationError("max_depth must be positive")
    if int(config.random_forest.min_samples_leaf) <= 0:
        raise SupervisedModelConfigurationError("min_samples_leaf must be positive")
    _tuple_ints(config.evaluation.top_k_values, "evaluation.top_k_values")
    _tuple_floats(config.evaluation.threshold_grid, "evaluation.threshold_grid")
    if config.evaluation.primary_top_k <= 0:
        raise SupervisedModelConfigurationError("primary_top_k must be positive")
    _require_bool(config.persistence.persist_scores, "persistence.persist_scores")
    _require_bool(config.persistence.write_model_artifact, "persistence.write_model_artifact")
    _require_bool(config.persistence.write_mlflow, "persistence.write_mlflow")
    if not config.persistence.artefact_output_dir.strip():
        raise SupervisedModelConfigurationError("artefact_output_dir must be non-empty")


def supervised_model_config_from_mapping(
    payload: dict[str, object] | None,
) -> SupervisedModelConfig:
    """Build supervised model config from a mapping."""

    if payload is None:
        config = SupervisedModelConfig()
        validate_supervised_model_config(config)
        return config
    section = payload.get("supervised", payload) if isinstance(payload, dict) else payload
    if not isinstance(section, dict):
        raise SupervisedModelConfigurationError("supervised config must be a mapping")
    defaults = SupervisedModelConfig()
    dataset = section.get("dataset", {}) or {}
    split = section.get("split", {}) or {}
    preprocessing = section.get("preprocessing", {}) or {}
    logistic = section.get("logistic_regression", {}) or {}
    forest = section.get("random_forest", {}) or {}
    evaluation = section.get("evaluation", {}) or {}
    persistence = section.get("persistence", {}) or {}
    for name, value in (
        ("dataset", dataset),
        ("split", split),
        ("preprocessing", preprocessing),
        ("logistic_regression", logistic),
        ("random_forest", forest),
        ("evaluation", evaluation),
        ("persistence", persistence),
    ):
        if not isinstance(value, dict):
            raise SupervisedModelConfigurationError(f"{name} must be a mapping")
    config = SupervisedModelConfig(
        model_family=str(section.get("model_family", defaults.model_family)),
        model_name=str(section.get("model_name", defaults.model_name)),
        model_version=str(section.get("model_version", defaults.model_version)),
        random_seed=_require_int(section.get("random_seed", defaults.random_seed), "random_seed"),
        dataset=SupervisedDatasetConfig(
            level=str(dataset.get("level", defaults.dataset.level)),
            dataset_version=str(dataset.get("dataset_version", defaults.dataset.dataset_version)),
            label_column=str(dataset.get("label_column", defaults.dataset.label_column)),
            id_column=str(dataset.get("id_column", defaults.dataset.id_column)),
            timestamp_column=str(
                dataset.get("timestamp_column", defaults.dataset.timestamp_column)
            ),
            min_rows=_require_int(dataset.get("min_rows", defaults.dataset.min_rows), "min_rows"),
            min_positive_labels=_require_int(
                dataset.get("min_positive_labels", defaults.dataset.min_positive_labels),
                "min_positive_labels",
            ),
            min_negative_labels=_require_int(
                dataset.get("min_negative_labels", defaults.dataset.min_negative_labels),
                "min_negative_labels",
            ),
            allow_single_class_training=_require_bool(
                dataset.get(
                    "allow_single_class_training",
                    defaults.dataset.allow_single_class_training,
                ),
                "allow_single_class_training",
            ),
        ),
        split=SupervisedSplitConfig(
            strategy=str(split.get("strategy", defaults.split.strategy)),
            validation_fraction=_require_float(
                split.get("validation_fraction", defaults.split.validation_fraction),
                "validation_fraction",
            ),
            min_validation_rows=_require_int(
                split.get("min_validation_rows", defaults.split.min_validation_rows),
                "min_validation_rows",
            ),
        ),
        preprocessing=SupervisedPreprocessingConfig(
            numeric_imputation=str(
                preprocessing.get("numeric_imputation", defaults.preprocessing.numeric_imputation)
            ),
            standardise_numeric=_require_bool(
                preprocessing.get(
                    "standardise_numeric",
                    defaults.preprocessing.standardise_numeric,
                ),
                "standardise_numeric",
            ),
            drop_constant_features=_require_bool(
                preprocessing.get(
                    "drop_constant_features",
                    defaults.preprocessing.drop_constant_features,
                ),
                "drop_constant_features",
            ),
            drop_high_missing_features=_require_bool(
                preprocessing.get(
                    "drop_high_missing_features",
                    defaults.preprocessing.drop_high_missing_features,
                ),
                "drop_high_missing_features",
            ),
            high_missing_threshold=_require_float(
                preprocessing.get(
                    "high_missing_threshold",
                    defaults.preprocessing.high_missing_threshold,
                ),
                "high_missing_threshold",
            ),
        ),
        logistic_regression=LogisticRegressionConfig(
            enabled=_require_bool(logistic.get("enabled", True), "logistic.enabled"),
            penalty=str(logistic.get("penalty", defaults.logistic_regression.penalty)),
            C=_require_float(logistic.get("C", defaults.logistic_regression.C), "logistic.C"),
            class_weight=logistic.get("class_weight", defaults.logistic_regression.class_weight),
            max_iter=_require_int(
                logistic.get("max_iter", defaults.logistic_regression.max_iter),
                "logistic.max_iter",
            ),
        ),
        random_forest=RandomForestConfig(
            enabled=_require_bool(forest.get("enabled", True), "forest.enabled"),
            n_estimators=_require_int(
                forest.get("n_estimators", defaults.random_forest.n_estimators),
                "forest.n_estimators",
            ),
            max_depth=forest.get("max_depth", defaults.random_forest.max_depth),
            min_samples_leaf=_require_int(
                forest.get("min_samples_leaf", defaults.random_forest.min_samples_leaf),
                "forest.min_samples_leaf",
            ),
            class_weight=forest.get("class_weight", defaults.random_forest.class_weight),
            n_jobs=_require_int(forest.get("n_jobs", defaults.random_forest.n_jobs), "n_jobs"),
        ),
        evaluation=SupervisedEvaluationConfig(
            top_k_values=_tuple_ints(
                evaluation.get("top_k_values", defaults.evaluation.top_k_values),
                "top_k_values",
            ),
            threshold_grid=_tuple_floats(
                evaluation.get("threshold_grid", defaults.evaluation.threshold_grid),
                "threshold_grid",
            ),
            primary_metric=str(
                evaluation.get("primary_metric", defaults.evaluation.primary_metric)
            ),
            primary_top_k=_require_int(
                evaluation.get("primary_top_k", defaults.evaluation.primary_top_k),
                "primary_top_k",
            ),
        ),
        persistence=SupervisedPersistenceConfig(
            persist_scores=_require_bool(
                persistence.get("persist_scores", defaults.persistence.persist_scores),
                "persist_scores",
            ),
            write_model_artifact=_require_bool(
                persistence.get(
                    "write_model_artifact",
                    defaults.persistence.write_model_artifact,
                ),
                "write_model_artifact",
            ),
            write_mlflow=_require_bool(
                persistence.get("write_mlflow", defaults.persistence.write_mlflow),
                "write_mlflow",
            ),
            artefact_output_dir=str(
                persistence.get("artefact_output_dir", defaults.persistence.artefact_output_dir)
            ),
        ),
    )
    validate_supervised_model_config(config)
    return config


def load_supervised_model_config(
    config_path: Path | str = "config/model.yaml",
) -> SupervisedModelConfig:
    """Load supervised model config from YAML."""

    path = Path(config_path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        payload = {}
    except Exception as exc:
        raise SupervisedModelConfigurationError(f"failed to load model config: {exc}") from exc
    return supervised_model_config_from_mapping(payload)
