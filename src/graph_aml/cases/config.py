"""Configuration loading and validation for case generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from graph_aml.cases.exceptions import CaseConfigurationError


@dataclass(frozen=True)
class CaseGroupingConfig:
    group_by_account: bool = True
    group_by_customer: bool = True
    group_by_graph_community: bool = True
    group_by_circular_flow: bool = True
    group_by_common_counterparty: bool = True
    group_by_shared_identifier: bool = False


@dataclass(frozen=True)
class CaseGenerationThresholdConfig:
    min_alerts_per_case: int = 1
    max_alerts_per_case: int = 50
    max_cases_per_account: int = 5
    max_cases_total: int = 1000
    lookback_days: int | None = None
    min_account_risk_score: float = 0.0
    include_low_risk_accounts: bool = True


@dataclass(frozen=True)
class CaseGenerationPriorityConfig:
    use_account_risk_score: bool = True
    use_max_alert_score: bool = True
    use_alert_count_uplift: bool = True
    alert_count_uplift_per_alert: float = 1.5
    max_alert_count_uplift: float = 10.0


@dataclass(frozen=True)
class CaseGenerationConfig:
    case_version: str = "case_generation_v1"
    default_status: str = "New"
    grouping: CaseGroupingConfig = field(default_factory=CaseGroupingConfig)
    thresholds: CaseGenerationThresholdConfig = field(default_factory=CaseGenerationThresholdConfig)
    severity_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "critical": "critical",
        }
    )
    priority: CaseGenerationPriorityConfig = field(default_factory=CaseGenerationPriorityConfig)
    artefact_output_dir: str = "reports/model_validation"

    def __post_init__(self) -> None:
        validate_case_generation_config(self)


def validate_case_generation_config(config: CaseGenerationConfig) -> None:
    """Validate case generation configuration."""

    if not isinstance(config, CaseGenerationConfig):
        raise CaseConfigurationError("config must be CaseGenerationConfig")
    if not config.case_version.strip():
        raise CaseConfigurationError("case_version must be non-empty")
    if not config.default_status.strip():
        raise CaseConfigurationError("default_status must be non-empty")
    if not any(vars(config.grouping).values()):
        raise CaseConfigurationError("at least one grouping option must be enabled")
    thresholds = config.thresholds
    if thresholds.min_alerts_per_case <= 0:
        raise CaseConfigurationError("min_alerts_per_case must be positive")
    if thresholds.max_alerts_per_case < thresholds.min_alerts_per_case:
        raise CaseConfigurationError("max_alerts_per_case must be >= min_alerts_per_case")
    if thresholds.max_cases_per_account <= 0 or thresholds.max_cases_total <= 0:
        raise CaseConfigurationError("case count thresholds must be positive")
    if thresholds.lookback_days is not None and thresholds.lookback_days <= 0:
        raise CaseConfigurationError("lookback_days must be positive when supplied")
    if thresholds.min_account_risk_score < 0 or thresholds.min_account_risk_score > 100:
        raise CaseConfigurationError("min_account_risk_score must be in [0, 100]")
    if not isinstance(thresholds.include_low_risk_accounts, bool):
        raise CaseConfigurationError("include_low_risk_accounts must be boolean")
    if {"low", "medium", "high", "critical"}.difference(config.severity_mapping):
        raise CaseConfigurationError("severity_mapping must contain low, medium, high, critical")
    priority = config.priority
    for name in (
        "use_account_risk_score",
        "use_max_alert_score",
        "use_alert_count_uplift",
    ):
        if not isinstance(getattr(priority, name), bool):
            raise CaseConfigurationError(f"{name} must be boolean")
    if priority.alert_count_uplift_per_alert < 0 or priority.max_alert_count_uplift < 0:
        raise CaseConfigurationError("priority uplift values must be non-negative")


def case_generation_config_from_mapping(
    payload: dict[str, object] | None,
) -> CaseGenerationConfig:
    """Build case generation config from a mapping."""

    if payload is None:
        return CaseGenerationConfig()
    data = dict(payload)
    data.pop("enabled", None)
    if isinstance(data.get("grouping"), dict):
        data["grouping"] = CaseGroupingConfig(**data["grouping"])  # type: ignore[arg-type]
    if isinstance(data.get("thresholds"), dict):
        data["thresholds"] = CaseGenerationThresholdConfig(  # type: ignore[arg-type]
            **data["thresholds"]
        )
    if isinstance(data.get("priority"), dict):
        data["priority"] = CaseGenerationPriorityConfig(**data["priority"])  # type: ignore[arg-type]
    allowed = set(CaseGenerationConfig.__dataclass_fields__)
    values = {key: value for key, value in data.items() if key in allowed}
    try:
        return CaseGenerationConfig(**values)  # type: ignore[arg-type]
    except CaseConfigurationError:
        raise
    except Exception as exc:
        raise CaseConfigurationError(f"invalid case generation config: {exc}") from exc


def load_case_generation_config(
    config_path: Path | str = "config/scoring.yaml",
) -> CaseGenerationConfig:
    """Load case generation config from scoring YAML."""

    path = Path(config_path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise CaseConfigurationError(f"Failed to load case generation config: {exc}") from exc
    case_generation = payload.get("case_generation") if isinstance(payload, dict) else None
    if case_generation is not None and not isinstance(case_generation, dict):
        raise CaseConfigurationError("case_generation config must be a mapping")
    return case_generation_config_from_mapping(case_generation)
