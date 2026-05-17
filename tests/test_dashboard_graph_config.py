"""Tests for dashboard graph and account profile configuration."""

import pytest

from graph_aml.dashboard.config import (
    DashboardAccountProfileConfig,
    DashboardConfig,
    DashboardGraphViewConfig,
    dashboard_config_from_mapping,
    load_dashboard_config,
)
from graph_aml.dashboard.exceptions import DashboardConfigurationError


def test_default_graph_view_config_is_valid() -> None:
    assert DashboardConfig(graph_view=DashboardGraphViewConfig()).graph_view.enabled is True


def test_default_account_profile_config_is_valid() -> None:
    assert (
        DashboardConfig(account_profile=DashboardAccountProfileConfig()).account_profile.enabled
        is True
    )


def test_invalid_graph_layout_raises() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(graph_view=DashboardGraphViewConfig(default_layout="bad"))


def test_invalid_render_engine_raises() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(graph_view=DashboardGraphViewConfig(render_engine="canvas"))


def test_invalid_graph_limits_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(graph_view=DashboardGraphViewConfig(max_nodes=0))


def test_invalid_node_size_bounds_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(graph_view=DashboardGraphViewConfig(risk_node_size_min=50))


def test_invalid_account_profile_limits_raise() -> None:
    with pytest.raises(DashboardConfigurationError):
        DashboardConfig(account_profile=DashboardAccountProfileConfig(max_transactions=0))


def test_config_can_be_built_from_mapping_with_graph_and_account_sections() -> None:
    config = dashboard_config_from_mapping(
        {
            "graph_view": {"max_nodes": 25, "render_engine": "plotly"},
            "account_profile": {"max_transactions": 10},
        }
    )

    assert config.graph_view.max_nodes == 25
    assert config.graph_view.render_engine == "plotly"
    assert config.account_profile.max_transactions == 10


def test_graph_config_loading_does_not_connect_to_postgresql_or_neo4j(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError)
    )

    config = load_dashboard_config()

    assert config.graph_view.enabled is True
    assert config.account_profile.enabled is True
