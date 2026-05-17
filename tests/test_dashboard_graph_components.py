"""Tests for dashboard graph render helpers."""

import pandas as pd
import pytest

from graph_aml.dashboard.exceptions import DashboardRenderError
from graph_aml.dashboard.graph_components import (
    build_plotly_network_figure,
    build_pyvis_network_html,
    render_graph_legend,
    render_graph_summary,
    render_graph_view,
)


def _nodes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "node_id": ["A1", "A2"],
            "node_type": ["account", "counterparty"],
            "label": ["A1", "A2"],
            "risk_score": [90.0, None],
        }
    )


def _edges() -> pd.DataFrame:
    return pd.DataFrame({"source_id": ["A1"], "target_id": ["A2"], "edge_type": ["pays"]})


def test_pyvis_html_builder_returns_html_string() -> None:
    html = build_pyvis_network_html(_nodes(), _edges())

    assert isinstance(html, str)
    assert "html" in html.lower() or "graph" in html.lower()


def test_plotly_figure_builder_returns_figure_like_object() -> None:
    figure = build_plotly_network_figure(_nodes(), _edges())

    assert hasattr(figure, "to_html")


def test_empty_graph_frames_are_handled() -> None:
    assert "No graph data" in build_pyvis_network_html(pd.DataFrame(), pd.DataFrame())


def test_graph_renderers_are_callable_with_empty_inputs() -> None:
    render_graph_view(pd.DataFrame(), pd.DataFrame())
    render_graph_legend()
    render_graph_summary({"node_count": 0, "edge_count": 0})


def test_malformed_graph_inputs_raise_render_error() -> None:
    with pytest.raises(DashboardRenderError):
        build_pyvis_network_html({"bad": "input"}, pd.DataFrame())  # type: ignore[arg-type]
