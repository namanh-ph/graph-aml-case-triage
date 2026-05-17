"""Tests for account risk scoring configuration."""

from pathlib import Path

import pytest

from graph_aml.scoring import (
    AccountRiskScoringConfig,
    ScoringConfigurationError,
    account_risk_scoring_config_from_mapping,
    load_account_risk_scoring_config,
    validate_account_risk_scoring_config,
)


def test_default_config_is_valid() -> None:
    validate_account_risk_scoring_config(AccountRiskScoringConfig())


def test_invalid_score_name_raises() -> None:
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(score_name="")


def test_invalid_score_version_raises() -> None:
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(score_version="")


def test_missing_main_weights_raise() -> None:
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(weights={"rule_risk_score": 1.0})


def test_main_weights_must_sum_to_one() -> None:
    weights = dict(AccountRiskScoringConfig().weights)
    weights["rule_risk_score"] = 0.99
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(weights=weights)


def test_invalid_severity_scores_raise() -> None:
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(
            severity_scores={"low": 101, "medium": 50, "high": 75, "critical": 100}
        )


def test_invalid_risk_band_thresholds_raise() -> None:
    bands = {"low": 0, "medium": 80, "high": 75, "critical": 90}
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(risk_bands=bands)


def test_invalid_graph_component_weights_raise() -> None:
    weights = dict(AccountRiskScoringConfig().graph_component_weights)
    weights["proximity_score"] = 0.5
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(graph_component_weights=weights)


def test_invalid_customer_risk_scores_raise() -> None:
    scores = dict(AccountRiskScoringConfig().customer_risk_scores)
    scores["unknown"] = -1
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(customer_risk_scores=scores)


def test_invalid_jurisdiction_scores_raise() -> None:
    with pytest.raises(ScoringConfigurationError):
        AccountRiskScoringConfig(high_risk_country_score=101)


def test_config_can_be_built_from_mapping() -> None:
    config = account_risk_scoring_config_from_mapping({"score_version": "v2"})
    assert config.score_version == "v2"


def test_config_can_be_loaded_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "scoring.yaml"
    path.write_text("account_risk:\n  score_version: v2\n", encoding="utf-8")
    assert load_account_risk_scoring_config(path).score_version == "v2"


def test_config_loading_does_not_connect_to_postgresql(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "scoring.yaml"
    path.write_text("account_risk:\n  score_name: local\n", encoding="utf-8")
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine", lambda: (_ for _ in ()).throw(AssertionError)
    )
    assert load_account_risk_scoring_config(path).score_name == "local"
