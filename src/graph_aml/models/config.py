"""Typed configuration for Isolation Forest anomaly scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

import yaml

from graph_aml.models.exceptions import ModelConfigurationError


@dataclass(frozen=True)
class IsolationForestModelConfig:
    """Configuration for account-level Isolation Forest scoring."""

    model_name: str = "account_isolation_forest"
    model_version: str = "isolation_forest_v1"
    random_state: int = 42
    n_estimators: int = 200
    contamination: float | str = 0.05
    max_samples: int | float | str = "auto"
    max_features: int | float = 1.0
    bootstrap: bool = False
    n_jobs: int | None = -1
    score_percentile_high: float = 95.0
    score_percentile_medium: float = 80.0
    feature_date: date | None = None
    account_feature_version: str | None = None
    graph_feature_version: str | None = None
    graph_build_id: str | None = None
    use_graph_features: bool = True
    use_behavioural_features: bool = True
    use_jurisdiction_features: bool = True
    imputation_strategy: str = "median"
    scaling_strategy: str = "standard"
    min_training_rows: int = 20
    mlflow_enabled: bool = True
    mlflow_experiment_name: str = "graph_aml_anomaly_scoring"
    artefact_output_dir: str = "reports/model_validation"

    def __post_init__(self) -> None:
        validate_isolation_forest_config(self)


def _parse_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ModelConfigurationError(f"Invalid feature_date: {value}") from exc


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    raise ModelConfigurationError(f"Expected boolean value, got {value!r}")


def _coerce_optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(cast(int | str, value))


def _config_kwargs(payload: dict[str, object] | None) -> dict[str, object]:
    values = {} if payload is None else dict(payload)
    kwargs: dict[str, object] = {}
    fields = IsolationForestModelConfig.__dataclass_fields__
    for key, value in values.items():
        if key not in fields:
            continue
        if key == "feature_date":
            kwargs[key] = _parse_date(value)
        elif key in {
            "account_feature_version",
            "graph_feature_version",
            "graph_build_id",
        }:
            kwargs[key] = _string_or_none(value)
        elif key in {
            "use_graph_features",
            "use_behavioural_features",
            "use_jurisdiction_features",
            "mlflow_enabled",
            "bootstrap",
        }:
            kwargs[key] = _bool_value(value)
        elif key in {"random_state", "n_estimators", "min_training_rows"}:
            kwargs[key] = int(cast(int | str, value))
        elif key == "n_jobs":
            kwargs[key] = _coerce_optional_int(value)
        elif key in {
            "score_percentile_high",
            "score_percentile_medium",
            "max_features",
        }:
            kwargs[key] = float(cast(float | int | str, value))
        else:
            kwargs[key] = value
    return kwargs


def validate_isolation_forest_config(config: IsolationForestModelConfig) -> None:
    """Validate Isolation Forest configuration values."""

    if not isinstance(config, IsolationForestModelConfig):
        raise ModelConfigurationError("config must be IsolationForestModelConfig")
    if not config.model_name.strip():
        raise ModelConfigurationError("model_name must be non-empty")
    if not config.model_version.strip():
        raise ModelConfigurationError("model_version must be non-empty")
    if not isinstance(config.random_state, int):
        raise ModelConfigurationError("random_state must be an integer")
    if config.n_estimators <= 0:
        raise ModelConfigurationError("n_estimators must be positive")
    if config.contamination != "auto":
        contamination = float(config.contamination)
        if contamination <= 0 or contamination > 0.5:
            raise ModelConfigurationError("contamination must be 'auto' or in (0, 0.5]")
    if config.max_samples != "auto":
        if isinstance(config.max_samples, int):
            if config.max_samples <= 0:
                raise ModelConfigurationError("max_samples integer must be positive")
        else:
            max_samples = float(config.max_samples)
            if max_samples <= 0 or max_samples > 1:
                raise ModelConfigurationError("max_samples float must be in (0, 1]")
    if isinstance(config.max_features, int):
        if config.max_features <= 0:
            raise ModelConfigurationError("max_features integer must be positive")
    else:
        max_features = float(config.max_features)
        if max_features <= 0 or max_features > 1:
            raise ModelConfigurationError("max_features float must be in (0, 1]")
    if not (0 <= config.score_percentile_medium < config.score_percentile_high <= 100):
        raise ModelConfigurationError("score percentiles must satisfy 0 <= medium < high <= 100")
    if not (
        config.use_graph_features
        or config.use_behavioural_features
        or config.use_jurisdiction_features
    ):
        raise ModelConfigurationError("at least one feature group must be enabled")
    if config.imputation_strategy not in {"median", "mean", "zero"}:
        raise ModelConfigurationError("imputation_strategy must be median, mean, or zero")
    if config.scaling_strategy not in {"standard", "robust", "none"}:
        raise ModelConfigurationError("scaling_strategy must be standard, robust, or none")
    if config.min_training_rows <= 0:
        raise ModelConfigurationError("min_training_rows must be positive")
    if not isinstance(config.mlflow_enabled, bool):
        raise ModelConfigurationError("mlflow_enabled must be boolean")


def isolation_forest_config_from_mapping(
    payload: dict[str, object] | None,
) -> IsolationForestModelConfig:
    """Build an Isolation Forest config from a mapping."""

    try:
        return IsolationForestModelConfig(**cast(Any, _config_kwargs(payload)))
    except ModelConfigurationError:
        raise
    except Exception as exc:
        raise ModelConfigurationError(f"Failed to build Isolation Forest config: {exc}") from exc


def load_isolation_forest_config(
    config_path: Path | str = "config/model.yaml",
) -> IsolationForestModelConfig:
    """Load Isolation Forest configuration from YAML."""

    path = Path(config_path)
    try:
        if not path.is_file():
            return IsolationForestModelConfig()
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        section = cast(dict[str, object], payload.get("isolation_forest", {}))
        return isolation_forest_config_from_mapping(section)
    except ModelConfigurationError:
        raise
    except Exception as exc:
        raise ModelConfigurationError(
            f"Failed to load Isolation Forest config from {path}: {exc}"
        ) from exc
