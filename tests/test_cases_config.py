"""Tests for case generation configuration."""

from pathlib import Path

import pytest

from graph_aml.cases import (
    CaseConfigurationError,
    CaseGenerationConfig,
    CaseGenerationPriorityConfig,
    CaseGenerationThresholdConfig,
    CaseGroupingConfig,
    case_generation_config_from_mapping,
    load_case_generation_config,
    validate_case_generation_config,
)


def test_default_case_generation_config_is_valid() -> None:
    validate_case_generation_config(CaseGenerationConfig())


def test_invalid_case_version_and_status_raise() -> None:
    with pytest.raises(CaseConfigurationError):
        CaseGenerationConfig(case_version="")
    with pytest.raises(CaseConfigurationError):
        CaseGenerationConfig(default_status="")


def test_disabling_all_grouping_options_raises() -> None:
    with pytest.raises(CaseConfigurationError):
        CaseGenerationConfig(grouping=CaseGroupingConfig(False, False, False, False, False, False))


def test_invalid_thresholds_raise() -> None:
    with pytest.raises(CaseConfigurationError):
        CaseGenerationConfig(thresholds=CaseGenerationThresholdConfig(min_alerts_per_case=0))
    with pytest.raises(CaseConfigurationError):
        CaseGenerationConfig(
            thresholds=CaseGenerationThresholdConfig(min_alerts_per_case=5, max_alerts_per_case=1)
        )
    with pytest.raises(CaseConfigurationError):
        CaseGenerationConfig(thresholds=CaseGenerationThresholdConfig(lookback_days=0))


def test_invalid_priority_settings_raise() -> None:
    with pytest.raises(CaseConfigurationError):
        CaseGenerationConfig(priority=CaseGenerationPriorityConfig(alert_count_uplift_per_alert=-1))


def test_config_can_be_built_from_mapping() -> None:
    config = case_generation_config_from_mapping(
        {"case_version": "v2", "grouping": {"group_by_account": True}}
    )
    assert config.case_version == "v2"


def test_config_can_be_loaded_from_temporary_yaml(tmp_path: Path) -> None:
    path = tmp_path / "scoring.yaml"
    path.write_text("case_generation:\n  case_version: test_v1\n", encoding="utf-8")
    assert load_case_generation_config(path).case_version == "test_v1"


def test_config_loading_does_not_connect_to_postgresql(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("should not connect")

    monkeypatch.setattr("graph_aml.database.create_database_engine", fail, raising=False)
    path = tmp_path / "scoring.yaml"
    path.write_text("case_generation:\n  case_version: test_v1\n", encoding="utf-8")
    assert load_case_generation_config(path).case_version == "test_v1"
