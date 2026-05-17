"""Tests for case risk scoring configuration."""

from pathlib import Path

import pytest

from graph_aml.cases import (
    CaseRiskAlertConfig,
    CaseRiskAnomalyConfig,
    CaseRiskConfigurationError,
    CaseRiskEvidenceConfig,
    CaseRiskGraphConfig,
    CaseRiskScoringConfig,
    case_risk_scoring_config_from_mapping,
    load_case_risk_scoring_config,
    validate_case_risk_scoring_config,
)


def test_default_case_risk_config_is_valid() -> None:
    validate_case_risk_scoring_config(CaseRiskScoringConfig())


def test_invalid_score_name_and_version_raise() -> None:
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(score_name="")
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(score_version="")


def test_invalid_main_weights_raise() -> None:
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(weights={"alert_risk_score": 1.0})
    weights = CaseRiskScoringConfig().weights | {"alert_risk_score": 0.9}
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(weights=weights)


def test_invalid_risk_bands_raise() -> None:
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(risk_bands={"low": 0, "medium": 90, "high": 75, "critical": 100})


def test_invalid_subcomponent_weights_raise() -> None:
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(
            alert=CaseRiskAlertConfig(max_alert_weight=1.0, mean_alert_weight=1.0)
        )
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(graph=CaseRiskGraphConfig(pagerank_weight=1.0))
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(
            anomaly=CaseRiskAnomalyConfig(max_anomaly_weight=1.0, mean_anomaly_weight=1.0)
        )
    with pytest.raises(CaseRiskConfigurationError):
        CaseRiskScoringConfig(evidence=CaseRiskEvidenceConfig(evidence_count_percentile_weight=1.0))


def test_config_can_be_built_from_mapping() -> None:
    config = case_risk_scoring_config_from_mapping({"score_version": "case_risk_v2"})
    assert config.score_version == "case_risk_v2"


def test_config_can_be_loaded_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "scoring.yaml"
    path.write_text("case_risk:\n  score_version: case_risk_v2\n", encoding="utf-8")
    assert load_case_risk_scoring_config(path).score_version == "case_risk_v2"


def test_config_loading_does_not_connect_to_postgresql(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not connect")),
        raising=False,
    )
    path = tmp_path / "scoring.yaml"
    path.write_text("case_risk:\n  score_version: case_risk_v2\n", encoding="utf-8")
    load_case_risk_scoring_config(path)
