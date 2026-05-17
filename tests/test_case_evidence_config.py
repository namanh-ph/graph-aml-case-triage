"""Tests for case evidence configuration."""

import pytest
import yaml

from graph_aml.cases import (
    CaseEvidenceConfig,
    CaseEvidenceConfigurationError,
    CaseEvidenceIncludeConfig,
    CaseEvidenceLimitConfig,
    CaseEvidenceRiskDriverThresholdConfig,
    CaseEvidenceTransactionSortingConfig,
    CaseExplanationConfig,
    case_evidence_config_from_mapping,
    load_case_evidence_config,
)


def test_default_case_evidence_config_is_valid() -> None:
    CaseEvidenceConfig()


def test_invalid_versions_raise() -> None:
    with pytest.raises(CaseEvidenceConfigurationError):
        CaseEvidenceConfig(evidence_version="")
    with pytest.raises(CaseEvidenceConfigurationError):
        CaseEvidenceConfig(explanation_version="")


def test_invalid_include_limits_sorting_and_thresholds_raise() -> None:
    with pytest.raises(CaseEvidenceConfigurationError):
        CaseEvidenceConfig(include=CaseEvidenceIncludeConfig(alerts="yes"))  # type: ignore[arg-type]
    with pytest.raises(CaseEvidenceConfigurationError):
        CaseEvidenceConfig(limits=CaseEvidenceLimitConfig(max_alerts_per_case=0))
    with pytest.raises(CaseEvidenceConfigurationError):
        CaseEvidenceConfig(transaction_sorting=CaseEvidenceTransactionSortingConfig(primary=""))
    with pytest.raises(CaseEvidenceConfigurationError):
        CaseEvidenceConfig(
            risk_driver_thresholds=CaseEvidenceRiskDriverThresholdConfig(high_component_score=101)
        )


def test_disabling_every_explanation_section_raises() -> None:
    with pytest.raises(CaseEvidenceConfigurationError):
        CaseEvidenceConfig(
            explanation=CaseExplanationConfig(
                include_case_summary=False,
                include_typology_summary=False,
                include_risk_driver_summary=False,
                include_transaction_summary=False,
                include_graph_summary=False,
                include_recommended_review_focus=False,
            )
        )


def test_config_from_mapping_and_yaml_load(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = case_evidence_config_from_mapping(
        {"evidence_version": "v2", "limits": {"max_alerts_per_case": 10}}
    )
    assert config.evidence_version == "v2"
    assert config.limits.max_alerts_per_case == 10
    path = tmp_path / "scoring.yaml"
    path.write_text(
        yaml.safe_dump({"case_evidence": {"evidence_version": "yaml_v1"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not connect")),
        raising=False,
    )
    assert load_case_evidence_config(path).evidence_version == "yaml_v1"
