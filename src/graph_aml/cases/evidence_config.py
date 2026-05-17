"""Configuration loading and validation for case evidence packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from graph_aml.cases.exceptions import CaseEvidenceConfigurationError


@dataclass(frozen=True)
class CaseEvidenceIncludeConfig:
    alerts: bool = True
    transactions: bool = True
    risk_drivers: bool = True
    graph_context: bool = True
    account_context: bool = True
    typology_context: bool = True
    chronology: bool = True


@dataclass(frozen=True)
class CaseEvidenceLimitConfig:
    max_transactions_per_case: int = 100
    max_alerts_per_case: int = 50
    max_related_accounts: int = 50
    max_graph_paths: int = 25
    max_reason_codes: int = 25
    max_explanation_bullets: int = 12


@dataclass(frozen=True)
class CaseEvidenceTransactionSortingConfig:
    primary: str = "transaction_timestamp"
    secondary: str = "amount"
    descending_amount: bool = True


@dataclass(frozen=True)
class CaseEvidenceRiskDriverThresholdConfig:
    high_component_score: float = 75.0
    critical_component_score: float = 90.0
    high_transaction_value_percentile: float = 90.0
    high_alert_count: int = 5
    high_typology_count: int = 3


@dataclass(frozen=True)
class CaseExplanationConfig:
    include_case_summary: bool = True
    include_typology_summary: bool = True
    include_risk_driver_summary: bool = True
    include_transaction_summary: bool = True
    include_graph_summary: bool = True
    include_recommended_review_focus: bool = True


@dataclass(frozen=True)
class CaseEvidenceConfig:
    evidence_version: str = "case_evidence_v1"
    explanation_version: str = "deterministic_explanation_v1"
    include: CaseEvidenceIncludeConfig = field(default_factory=CaseEvidenceIncludeConfig)
    limits: CaseEvidenceLimitConfig = field(default_factory=CaseEvidenceLimitConfig)
    transaction_sorting: CaseEvidenceTransactionSortingConfig = field(
        default_factory=CaseEvidenceTransactionSortingConfig
    )
    risk_driver_thresholds: CaseEvidenceRiskDriverThresholdConfig = field(
        default_factory=CaseEvidenceRiskDriverThresholdConfig
    )
    explanation: CaseExplanationConfig = field(default_factory=CaseExplanationConfig)
    artefact_output_dir: str = "reports/model_validation"

    def __post_init__(self) -> None:
        validate_case_evidence_config(self)


def _validate_boolean_fields(instance: object, label: str) -> None:
    for field_name, value in instance.__dict__.items():
        if not isinstance(value, bool):
            raise CaseEvidenceConfigurationError(f"{label}.{field_name} must be boolean")


def validate_case_evidence_config(config: CaseEvidenceConfig) -> None:
    """Validate case evidence configuration."""

    if not isinstance(config, CaseEvidenceConfig):
        raise CaseEvidenceConfigurationError("config must be CaseEvidenceConfig")
    if not config.evidence_version.strip():
        raise CaseEvidenceConfigurationError("evidence_version must be non-empty")
    if not config.explanation_version.strip():
        raise CaseEvidenceConfigurationError("explanation_version must be non-empty")
    _validate_boolean_fields(config.include, "include")
    _validate_boolean_fields(config.explanation, "explanation")
    if not any(config.explanation.__dict__.values()):
        raise CaseEvidenceConfigurationError("at least one explanation section must be enabled")
    for field_name, value in config.limits.__dict__.items():
        if value <= 0:
            raise CaseEvidenceConfigurationError(f"limits.{field_name} must be positive")
    if not config.transaction_sorting.primary.strip():
        raise CaseEvidenceConfigurationError("transaction_sorting.primary must be non-empty")
    if not config.transaction_sorting.secondary.strip():
        raise CaseEvidenceConfigurationError("transaction_sorting.secondary must be non-empty")
    if not isinstance(config.transaction_sorting.descending_amount, bool):
        raise CaseEvidenceConfigurationError(
            "transaction_sorting.descending_amount must be boolean"
        )
    thresholds = config.risk_driver_thresholds
    for field_name in (
        "high_component_score",
        "critical_component_score",
        "high_transaction_value_percentile",
    ):
        value = getattr(thresholds, field_name)
        if value < 0 or value > 100:
            raise CaseEvidenceConfigurationError(
                f"risk_driver_thresholds.{field_name} must be in [0, 100]"
            )
    if thresholds.high_alert_count <= 0:
        raise CaseEvidenceConfigurationError("risk_driver_thresholds.high_alert_count is invalid")
    if thresholds.high_typology_count <= 0:
        raise CaseEvidenceConfigurationError(
            "risk_driver_thresholds.high_typology_count is invalid"
        )


def case_evidence_config_from_mapping(payload: dict[str, object] | None) -> CaseEvidenceConfig:
    """Build case evidence config from a mapping."""

    if payload is None:
        return CaseEvidenceConfig()
    data = dict(payload)
    data.pop("enabled", None)
    try:
        for key, klass in (
            ("include", CaseEvidenceIncludeConfig),
            ("limits", CaseEvidenceLimitConfig),
            ("transaction_sorting", CaseEvidenceTransactionSortingConfig),
            ("risk_driver_thresholds", CaseEvidenceRiskDriverThresholdConfig),
            ("explanation", CaseExplanationConfig),
        ):
            if isinstance(data.get(key), dict):
                data[key] = klass(**data[key])  # type: ignore[arg-type]
        allowed = set(CaseEvidenceConfig.__dataclass_fields__)
        values = {key: value for key, value in data.items() if key in allowed}
        return CaseEvidenceConfig(**values)  # type: ignore[arg-type]
    except CaseEvidenceConfigurationError:
        raise
    except Exception as exc:
        raise CaseEvidenceConfigurationError(f"invalid case evidence config: {exc}") from exc


def load_case_evidence_config(
    config_path: Path | str = "config/scoring.yaml",
) -> CaseEvidenceConfig:
    """Load case evidence config from scoring YAML."""

    path = Path(config_path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise CaseEvidenceConfigurationError(f"Failed to load case evidence config: {exc}") from exc
    case_evidence = payload.get("case_evidence") if isinstance(payload, dict) else None
    if case_evidence is not None and not isinstance(case_evidence, dict):
        raise CaseEvidenceConfigurationError("case_evidence config must be a mapping")
    return case_evidence_config_from_mapping(case_evidence)
