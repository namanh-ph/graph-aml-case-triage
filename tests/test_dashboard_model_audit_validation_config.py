"""Tests for dashboard model metrics, audit log, and validation report config."""

import pytest

from graph_aml.dashboard.config import (
    DashboardAuditLogConfig,
    DashboardConfig,
    DashboardModelMetricsConfig,
    DashboardValidationReportConfig,
    dashboard_config_from_mapping,
    load_dashboard_config,
)
from graph_aml.dashboard.exceptions import DashboardConfigurationError


def test_default_governance_dashboard_configs_are_valid() -> None:
    config = DashboardConfig(
        model_metrics=DashboardModelMetricsConfig(),
        audit_log=DashboardAuditLogConfig(),
        validation_report=DashboardValidationReportConfig(),
    )

    assert config.model_metrics.enabled is True
    assert config.audit_log.enabled is True
    assert config.validation_report.enabled is True


def test_invalid_model_metrics_limits_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(model_metrics=DashboardModelMetricsConfig(default_score_limit=0))


def test_invalid_top_k_values_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(model_metrics=DashboardModelMetricsConfig(default_top_k_values=(10, 10)))


def test_invalid_audit_limits_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(audit_log=DashboardAuditLogConfig(default_limit=20, max_limit=10))


def test_invalid_audit_string_defaults_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(audit_log=DashboardAuditLogConfig(default_components=("rules", "")))
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(audit_log=DashboardAuditLogConfig(searchable_fields=("run_id", "run_id")))


def test_invalid_validation_report_config_raises() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(validation_report=DashboardValidationReportConfig(report_dir=""))
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(validation_report=DashboardValidationReportConfig(allowed_extensions=("json",)))


def test_config_can_be_built_from_mapping_with_governance_sections() -> None:
    config = dashboard_config_from_mapping(
        {
            "model_metrics": {"default_top_k_values": [5, 10]},
            "audit_log": {"default_components": ["rules", "cases"]},
            "validation_report": {"allowed_extensions": [".md", ".json"]},
        }
    )

    assert config.model_metrics.default_top_k_values == (5, 10)
    assert config.audit_log.default_components == ("rules", "cases")
    assert config.validation_report.allowed_extensions == (".md", ".json")


def test_config_loading_does_not_connect_to_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("engine")),
    )

    assert load_dashboard_config().model_metrics.enabled is True
