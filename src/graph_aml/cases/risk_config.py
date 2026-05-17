"""Configuration loading and validation for case-level risk scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from graph_aml.cases.exceptions import CaseRiskConfigurationError


@dataclass(frozen=True)
class CaseRiskAlertConfig:
    use_max_alert_score: bool = True
    use_mean_alert_score: bool = True
    max_alert_weight: float = 0.70
    mean_alert_weight: float = 0.30
    severity_scores: dict[str, float] = field(
        default_factory=lambda: {
            "low": 25.0,
            "medium": 50.0,
            "high": 75.0,
            "critical": 100.0,
        }
    )


@dataclass(frozen=True)
class CaseRiskGraphConfig:
    pagerank_weight: float = 0.25
    degree_weight: float = 0.20
    cycle_weight: float = 0.20
    community_size_weight: float = 0.15
    alert_proximity_weight: float = 0.20


@dataclass(frozen=True)
class CaseRiskAnomalyConfig:
    use_max_anomaly_score: bool = True
    use_mean_anomaly_score: bool = True
    max_anomaly_weight: float = 0.75
    mean_anomaly_weight: float = 0.25


@dataclass(frozen=True)
class CaseRiskEvidenceConfig:
    transaction_value_percentile_weight: float = 0.50
    evidence_count_percentile_weight: float = 0.25
    related_account_count_percentile_weight: float = 0.25


@dataclass(frozen=True)
class CaseRiskThresholdConfig:
    min_case_priority_score: float = 0.0
    min_component_coverage: float = 0.50
    max_cases_total: int = 1000


@dataclass(frozen=True)
class CaseRiskScoringConfig:
    score_name: str = "composite_case_risk"
    score_version: str = "composite_case_risk_v1"
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "alert_risk_score": 0.25,
            "account_risk_score": 0.25,
            "graph_risk_score": 0.15,
            "anomaly_risk_score": 0.15,
            "typology_diversity_score": 0.10,
            "evidence_value_score": 0.10,
        }
    )
    risk_bands: dict[str, float] = field(
        default_factory=lambda: {
            "low": 0.0,
            "medium": 50.0,
            "high": 75.0,
            "critical": 90.0,
        }
    )
    alert: CaseRiskAlertConfig = field(default_factory=CaseRiskAlertConfig)
    graph: CaseRiskGraphConfig = field(default_factory=CaseRiskGraphConfig)
    anomaly: CaseRiskAnomalyConfig = field(default_factory=CaseRiskAnomalyConfig)
    evidence: CaseRiskEvidenceConfig = field(default_factory=CaseRiskEvidenceConfig)
    thresholds: CaseRiskThresholdConfig = field(default_factory=CaseRiskThresholdConfig)
    case_version: str | None = None
    account_risk_score_version: str | None = None
    graph_feature_version: str | None = None
    graph_build_id: str | None = None
    anomaly_model_version: str | None = None
    anomaly_model_run_id: str | None = None
    artefact_output_dir: str = "reports/model_validation"

    def __post_init__(self) -> None:
        validate_case_risk_scoring_config(self)


def _validate_weight_map(
    values: dict[str, float],
    required: set[str],
    label: str,
    *,
    require_exact_keys: bool = True,
) -> None:
    keys = set(values)
    if require_exact_keys and keys != required:
        raise CaseRiskConfigurationError(f"{label} must contain exactly {sorted(required)}")
    if not require_exact_keys and required.difference(keys):
        raise CaseRiskConfigurationError(f"{label} missing required keys")
    total = 0.0
    for key, value in values.items():
        if value < 0:
            raise CaseRiskConfigurationError(f"{label}.{key} must be non-negative")
        total += float(value)
    if abs(total - 1.0) > 1e-9:
        raise CaseRiskConfigurationError(f"{label} must sum to 1.0, got {total}")


def _validate_band_thresholds(risk_bands: dict[str, float]) -> None:
    required = ("low", "medium", "high", "critical")
    if set(risk_bands) != set(required):
        raise CaseRiskConfigurationError("risk_bands must contain low, medium, high, critical")
    values = [float(risk_bands[key]) for key in required]
    if any(value < 0 or value > 100 for value in values):
        raise CaseRiskConfigurationError("risk band thresholds must be in [0, 100]")
    if values != sorted(values):
        raise CaseRiskConfigurationError("risk band thresholds must be ordered")


def validate_case_risk_scoring_config(config: CaseRiskScoringConfig) -> None:
    """Validate case risk scoring configuration."""

    if not isinstance(config, CaseRiskScoringConfig):
        raise CaseRiskConfigurationError("config must be CaseRiskScoringConfig")
    if not config.score_name.strip():
        raise CaseRiskConfigurationError("score_name must be non-empty")
    if not config.score_version.strip():
        raise CaseRiskConfigurationError("score_version must be non-empty")
    _validate_weight_map(
        config.weights,
        {
            "alert_risk_score",
            "account_risk_score",
            "graph_risk_score",
            "anomaly_risk_score",
            "typology_diversity_score",
            "evidence_value_score",
        },
        "weights",
    )
    _validate_band_thresholds(config.risk_bands)
    if {"low", "medium", "high", "critical"}.difference(config.alert.severity_scores):
        raise CaseRiskConfigurationError("alert severity scores must contain all severities")
    for key, value in config.alert.severity_scores.items():
        if value < 0 or value > 100:
            raise CaseRiskConfigurationError(f"alert severity score {key} must be in [0, 100]")
    if not isinstance(config.alert.use_max_alert_score, bool) or not isinstance(
        config.alert.use_mean_alert_score, bool
    ):
        raise CaseRiskConfigurationError("alert method toggles must be boolean")
    if config.alert.use_max_alert_score and config.alert.use_mean_alert_score:
        _validate_weight_map(
            {
                "max_alert_weight": config.alert.max_alert_weight,
                "mean_alert_weight": config.alert.mean_alert_weight,
            },
            {"max_alert_weight", "mean_alert_weight"},
            "alert weights",
        )
    graph_weights = {
        "pagerank_weight": config.graph.pagerank_weight,
        "degree_weight": config.graph.degree_weight,
        "cycle_weight": config.graph.cycle_weight,
        "community_size_weight": config.graph.community_size_weight,
        "alert_proximity_weight": config.graph.alert_proximity_weight,
    }
    _validate_weight_map(graph_weights, set(graph_weights), "graph weights")
    if not isinstance(config.anomaly.use_max_anomaly_score, bool) or not isinstance(
        config.anomaly.use_mean_anomaly_score, bool
    ):
        raise CaseRiskConfigurationError("anomaly method toggles must be boolean")
    if config.anomaly.use_max_anomaly_score and config.anomaly.use_mean_anomaly_score:
        _validate_weight_map(
            {
                "max_anomaly_weight": config.anomaly.max_anomaly_weight,
                "mean_anomaly_weight": config.anomaly.mean_anomaly_weight,
            },
            {"max_anomaly_weight", "mean_anomaly_weight"},
            "anomaly weights",
        )
    evidence_weights = {
        "transaction_value_percentile_weight": config.evidence.transaction_value_percentile_weight,
        "evidence_count_percentile_weight": config.evidence.evidence_count_percentile_weight,
        "related_account_count_percentile_weight": (
            config.evidence.related_account_count_percentile_weight
        ),
    }
    _validate_weight_map(evidence_weights, set(evidence_weights), "evidence weights")
    if (
        config.thresholds.min_case_priority_score < 0
        or config.thresholds.min_case_priority_score > 100
    ):
        raise CaseRiskConfigurationError("min_case_priority_score must be in [0, 100]")
    if config.thresholds.min_component_coverage < 0 or config.thresholds.min_component_coverage > 1:
        raise CaseRiskConfigurationError("min_component_coverage must be in [0, 1]")
    if config.thresholds.max_cases_total <= 0:
        raise CaseRiskConfigurationError("max_cases_total must be positive")


def case_risk_scoring_config_from_mapping(
    payload: dict[str, object] | None,
) -> CaseRiskScoringConfig:
    """Build case risk scoring config from mapping."""

    if payload is None:
        return CaseRiskScoringConfig()
    data = dict(payload)
    data.pop("enabled", None)
    try:
        for key, klass in (
            ("alert", CaseRiskAlertConfig),
            ("graph", CaseRiskGraphConfig),
            ("anomaly", CaseRiskAnomalyConfig),
            ("evidence", CaseRiskEvidenceConfig),
            ("thresholds", CaseRiskThresholdConfig),
        ):
            if isinstance(data.get(key), dict):
                data[key] = klass(**data[key])  # type: ignore[arg-type]
        allowed = set(CaseRiskScoringConfig.__dataclass_fields__)
        values = {key: value for key, value in data.items() if key in allowed}
        return CaseRiskScoringConfig(**values)  # type: ignore[arg-type]
    except CaseRiskConfigurationError:
        raise
    except Exception as exc:
        raise CaseRiskConfigurationError(f"invalid case risk config: {exc}") from exc


def load_case_risk_scoring_config(
    config_path: Path | str = "config/scoring.yaml",
) -> CaseRiskScoringConfig:
    """Load case risk scoring config from scoring YAML."""

    path = Path(config_path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise CaseRiskConfigurationError(f"Failed to load case risk config: {exc}") from exc
    case_risk = payload.get("case_risk") if isinstance(payload, dict) else None
    if case_risk is not None and not isinstance(case_risk, dict):
        raise CaseRiskConfigurationError("case_risk config must be a mapping")
    return case_risk_scoring_config_from_mapping(case_risk)
