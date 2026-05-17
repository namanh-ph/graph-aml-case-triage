"""Configuration loading and validation for account risk scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from graph_aml.scoring.exceptions import ScoringConfigurationError

MAIN_WEIGHT_KEYS = (
    "rule_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "customer_risk_score",
    "jurisdiction_risk_score",
)

GRAPH_COMPONENT_WEIGHT_KEYS = (
    "pagerank_percentile",
    "degree_percentile",
    "betweenness_percentile",
    "cycle_count_percentile",
    "high_risk_alert_count_percentile",
    "proximity_score",
)


@dataclass(frozen=True)
class AccountRiskScoringConfig:
    """Configurable weights and score mappings for account risk scoring."""

    score_name: str = "composite_account_risk"
    score_version: str = "composite_account_risk_v1"
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "rule_risk_score": 0.35,
            "graph_risk_score": 0.25,
            "anomaly_risk_score": 0.25,
            "customer_risk_score": 0.10,
            "jurisdiction_risk_score": 0.05,
        }
    )
    severity_scores: dict[str, float] = field(
        default_factory=lambda: {
            "low": 25.0,
            "medium": 50.0,
            "high": 75.0,
            "critical": 100.0,
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
    graph_component_weights: dict[str, float] = field(
        default_factory=lambda: {
            "pagerank_percentile": 0.25,
            "degree_percentile": 0.15,
            "betweenness_percentile": 0.15,
            "cycle_count_percentile": 0.15,
            "high_risk_alert_count_percentile": 0.20,
            "proximity_score": 0.10,
        }
    )
    customer_risk_scores: dict[str, float] = field(
        default_factory=lambda: {
            "low": 20.0,
            "medium": 50.0,
            "high": 80.0,
            "critical": 100.0,
            "unknown": 50.0,
        }
    )
    high_risk_country_score: float = 100.0
    standard_country_score: float = 30.0
    unknown_country_score: float = 50.0
    feature_date: date | None = None
    alert_lookback_days: int | None = None
    graph_feature_version: str | None = None
    graph_build_id: str | None = None
    anomaly_model_version: str | None = None
    anomaly_model_run_id: str | None = None
    include_inactive_accounts: bool = True
    min_component_coverage: float = 0.50
    artefact_output_dir: str = "reports/model_validation"

    def __post_init__(self) -> None:
        validate_account_risk_scoring_config(self)


def _validate_score_mapping(
    values: dict[str, float],
    required: tuple[str, ...],
    name: str,
    *,
    sum_to_one: bool = False,
) -> None:
    if set(values) != set(required):
        raise ScoringConfigurationError(f"{name} must contain exactly {sorted(required)}")
    numbers = [float(value) for value in values.values()]
    if any(value < 0 for value in numbers):
        raise ScoringConfigurationError(f"{name} values must be non-negative")
    if sum_to_one and abs(sum(numbers) - 1.0) > 1e-6:
        raise ScoringConfigurationError(f"{name} must sum to 1.0")


def _validate_scores_in_range(values: dict[str, float], name: str) -> None:
    for key, value in values.items():
        score = float(value)
        if score < 0 or score > 100:
            raise ScoringConfigurationError(f"{name}.{key} must be in [0, 100]")


def validate_account_risk_scoring_config(config: AccountRiskScoringConfig) -> None:
    """Validate account risk scoring configuration."""

    if not isinstance(config, AccountRiskScoringConfig):
        raise ScoringConfigurationError("config must be AccountRiskScoringConfig")
    if not config.score_name.strip():
        raise ScoringConfigurationError("score_name must be non-empty")
    if not config.score_version.strip():
        raise ScoringConfigurationError("score_version must be non-empty")
    _validate_score_mapping(config.weights, MAIN_WEIGHT_KEYS, "weights", sum_to_one=True)
    for severity in ("low", "medium", "high", "critical"):
        if severity not in config.severity_scores:
            raise ScoringConfigurationError(
                "severity_scores must include low, medium, high, critical"
            )
    _validate_scores_in_range(config.severity_scores, "severity_scores")
    band_values = [float(config.risk_bands[key]) for key in ("low", "medium", "high", "critical")]
    if any(value < 0 or value > 100 for value in band_values) or band_values != sorted(band_values):
        raise ScoringConfigurationError("risk_bands must be ordered thresholds in [0, 100]")
    _validate_score_mapping(
        config.graph_component_weights,
        GRAPH_COMPONENT_WEIGHT_KEYS,
        "graph_component_weights",
        sum_to_one=True,
    )
    _validate_scores_in_range(config.customer_risk_scores, "customer_risk_scores")
    for value in (
        config.high_risk_country_score,
        config.standard_country_score,
        config.unknown_country_score,
    ):
        if value < 0 or value > 100:
            raise ScoringConfigurationError("jurisdiction scores must be in [0, 100]")
    if config.alert_lookback_days is not None and config.alert_lookback_days <= 0:
        raise ScoringConfigurationError("alert_lookback_days must be positive when supplied")
    if not isinstance(config.include_inactive_accounts, bool):
        raise ScoringConfigurationError("include_inactive_accounts must be boolean")
    if config.min_component_coverage < 0 or config.min_component_coverage > 1:
        raise ScoringConfigurationError("min_component_coverage must be in [0, 1]")


def _parse_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ScoringConfigurationError(f"invalid feature_date: {value}") from exc


def account_risk_scoring_config_from_mapping(
    payload: dict[str, object] | None,
) -> AccountRiskScoringConfig:
    """Build scoring config from a plain mapping or YAML account_risk section."""

    if payload is None:
        return AccountRiskScoringConfig()
    data = dict(payload)
    jurisdiction = data.pop("jurisdiction", None)
    if isinstance(jurisdiction, dict):
        data["high_risk_country_score"] = jurisdiction.get("high_risk_country_score", 100.0)
        data["standard_country_score"] = jurisdiction.get("standard_country_score", 30.0)
        data["unknown_country_score"] = jurisdiction.get("unknown_country_score", 50.0)
    if "feature_date" in data:
        data["feature_date"] = _parse_date(data["feature_date"])
    allowed = set(AccountRiskScoringConfig.__dataclass_fields__)
    values = {key: value for key, value in data.items() if key in allowed}
    try:
        return AccountRiskScoringConfig(**values)  # type: ignore[arg-type]
    except ScoringConfigurationError:
        raise
    except Exception as exc:
        raise ScoringConfigurationError(f"invalid account risk scoring config: {exc}") from exc


def load_account_risk_scoring_config(
    config_path: Path | str = "config/scoring.yaml",
) -> AccountRiskScoringConfig:
    """Load account risk scoring configuration from YAML."""

    path = Path(config_path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ScoringConfigurationError(f"Failed to load scoring config: {exc}") from exc
    account_risk = payload.get("account_risk") if isinstance(payload, dict) else None
    if account_risk is None:
        account_risk = payload.get("account_risk_score") if isinstance(payload, dict) else None
    if not isinstance(account_risk, dict | None):
        raise ScoringConfigurationError("account_risk config must be a mapping")
    return account_risk_scoring_config_from_mapping(account_risk)
