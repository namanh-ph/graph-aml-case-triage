"""Tests for dashboard configuration loading."""

from pathlib import Path

import pytest

from graph_aml.dashboard.config import (
    DashboardConfig,
    DashboardFormattingConfig,
    DashboardTriageConfig,
    dashboard_config_from_mapping,
    load_dashboard_config,
    validate_dashboard_config,
)
from graph_aml.dashboard.exceptions import DashboardConfigurationError


def test_default_dashboard_config_is_valid() -> None:
    validate_dashboard_config(DashboardConfig())


def test_invalid_title_raises() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(title="")


def test_invalid_layout_raises() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(layout="full")


def test_invalid_page_sizes_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(default_page_size=10, max_page_size=5)


def test_invalid_feature_flags_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(enable_lifecycle_actions="yes")  # type: ignore[arg-type]


def test_invalid_triage_limits_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(triage=DashboardTriageConfig(case_detail_max_alerts=0))


def test_invalid_formatting_config_raises() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(formatting=DashboardFormattingConfig(score_decimals=-1))


def test_config_can_be_built_from_mapping() -> None:
    config = dashboard_config_from_mapping(
        {
            "title": "AML",
            "default_case_statuses": ["New"],
            "triage": {"case_detail_max_alerts": 10},
            "formatting": {"currency": "USD"},
        }
    )

    assert config.title == "AML"
    assert config.default_case_statuses == ("New",)
    assert config.triage.case_detail_max_alerts == 10
    assert config.formatting.currency == "USD"


def test_config_can_be_loaded_from_temporary_yaml(tmp_path: Path) -> None:
    path = tmp_path / "dashboard.yaml"
    path.write_text(
        """
dashboard:
  title: Test Dashboard
  layout: centered
triage:
  case_detail_max_alerts: 25
formatting:
  amount_decimals: 3
""",
        encoding="utf-8",
    )

    config = load_dashboard_config(path)

    assert config.title == "Test Dashboard"
    assert config.layout == "centered"
    assert config.triage.case_detail_max_alerts == 25
    assert config.formatting.amount_decimals == 3


def test_config_loading_does_not_connect_to_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_connect(*_: object, **__: object) -> object:
        raise AssertionError("database connection attempted")

    monkeypatch.setattr("sqlalchemy.create_engine", fail_connect)

    config = load_dashboard_config()

    assert config.title
