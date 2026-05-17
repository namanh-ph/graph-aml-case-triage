"""Graph visualisation components for the Streamlit dashboard."""

from __future__ import annotations

from typing import Any, cast

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from graph_aml.dashboard.config import DashboardConfig
from graph_aml.dashboard.exceptions import DashboardRenderError
from graph_aml.dashboard.graph_transform import calculate_node_sizes

NODE_COLOURS = {
    "account": "#2563eb",
    "counterparty": "#0f766e",
    "transaction": "#7c3aed",
    "alert": "#dc2626",
    "case": "#ea580c",
    "customer": "#475569",
    "node": "#64748b",
}


def _ensure_frames(nodes: pd.DataFrame, edges: pd.DataFrame) -> None:
    if not isinstance(nodes, pd.DataFrame) or not isinstance(edges, pd.DataFrame):
        raise DashboardRenderError("nodes and edges must be DataFrames")


def build_pyvis_network_html(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    height: str = "650px",
    width: str = "100%",
) -> str:
    """Build an embeddable PyVis HTML network."""

    try:
        _ensure_frames(nodes, edges)
        if nodes.empty:
            return "<div>No graph data available.</div>"
        try:
            from pyvis.network import Network
        except Exception:
            figure = build_plotly_network_figure(nodes, edges)
            return str(figure.to_html(include_plotlyjs=True, full_html=False))
        network = Network(height=height, width=width, directed=True, cdn_resources="in_line")
        sizes = calculate_node_sizes(nodes)
        for index, row in nodes.reset_index(drop=True).iterrows():
            node_type = str(row.get("node_type") or "node")
            network.add_node(
                str(row["node_id"]),
                label=str(row.get("label") or row["node_id"]),
                title=str(row.get("metadata") or ""),
                color=NODE_COLOURS.get(node_type, NODE_COLOURS["node"]),
                size=float(sizes.iloc[index]),
            )
        for row in edges.astype(object).to_dict("records"):
            network.add_edge(
                str(row.get("source_id")),
                str(row.get("target_id")),
                title=str(row.get("edge_type") or "relationship"),
                value=float(row.get("weight") or 1.0),
            )
        return str(network.generate_html())
    except DashboardRenderError:
        raise
    except Exception as exc:
        raise DashboardRenderError(f"Failed to build PyVis graph HTML: {exc}") from exc


def _positions(graph: nx.Graph, layout: str) -> dict[str, tuple[float, float]]:
    if graph.number_of_nodes() == 0:
        return {}
    if layout == "kamada_kawai":
        return cast(dict[str, tuple[float, float]], nx.kamada_kawai_layout(graph))
    if layout == "circular":
        return cast(dict[str, tuple[float, float]], nx.circular_layout(graph))
    if layout == "shell":
        return cast(dict[str, tuple[float, float]], nx.shell_layout(graph))
    return cast(dict[str, tuple[float, float]], nx.spring_layout(graph, seed=42))


def build_plotly_network_figure(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    layout: str = "spring",
) -> Any:
    """Build a Plotly network figure."""

    try:
        _ensure_frames(nodes, edges)
        graph = nx.Graph()
        for row in nodes.astype(object).to_dict("records"):
            graph.add_node(str(row["node_id"]))
        for row in edges.astype(object).to_dict("records"):
            graph.add_edge(str(row["source_id"]), str(row["target_id"]))
        pos = _positions(graph, layout)
        edge_x: list[float | None] = []
        edge_y: list[float | None] = []
        for source, target in graph.edges():
            x0, y0 = pos[source]
            x1, y1 = pos[target]
            edge_x.extend([float(x0), float(x1), None])
            edge_y.extend([float(y0), float(y1), None])
        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line={"width": 1, "color": "#94a3b8"},
            hoverinfo="none",
            mode="lines",
        )
        sizes = calculate_node_sizes(nodes)
        node_x = [float(pos[str(row["node_id"])][0]) for _, row in nodes.iterrows()]
        node_y = [float(pos[str(row["node_id"])][1]) for _, row in nodes.iterrows()]
        colours = [
            NODE_COLOURS.get(str(row.get("node_type") or "node"), NODE_COLOURS["node"])
            for _, row in nodes.iterrows()
        ]
        labels = [str(row.get("label") or row["node_id"]) for _, row in nodes.iterrows()]
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=labels,
            textposition="top center",
            marker={"size": sizes.tolist(), "color": colours, "line": {"width": 1}},
            hovertext=labels,
            hoverinfo="text",
        )
        return go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                showlegend=False,
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                xaxis={"showgrid": False, "zeroline": False, "visible": False},
                yaxis={"showgrid": False, "zeroline": False, "visible": False},
                height=650,
            ),
        )
    except DashboardRenderError:
        raise
    except Exception as exc:
        raise DashboardRenderError(f"Failed to build Plotly graph figure: {exc}") from exc


def render_graph_view(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    config: DashboardConfig | None = None,
) -> None:
    """Render a graph view in Streamlit."""

    try:
        import streamlit as st
        import streamlit.components.v1 as components

        resolved = config or DashboardConfig()
        if nodes.empty:
            st.info("No graph context is available for the selected filters.")
            return
        if resolved.graph_view.render_engine == "plotly":
            st.plotly_chart(
                build_plotly_network_figure(nodes, edges, resolved.graph_view.default_layout),
                use_container_width=True,
            )
        else:
            html = build_pyvis_network_html(nodes, edges)
            components.html(html, height=680, scrolling=True)
    except DashboardRenderError:
        raise
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render graph view: {exc}") from exc


def render_graph_legend() -> None:
    import streamlit as st

    st.markdown(
        "Account: blue | Counterparty: teal | Transaction: purple | Alert: red | Case: orange"
    )


def render_graph_summary(summary: dict[str, object]) -> None:
    import streamlit as st

    columns = st.columns(4)
    for index, key in enumerate(("node_count", "edge_count", "account_count", "max_risk_score")):
        with columns[index]:
            st.metric(key.replace("_", " ").title(), str(summary.get(key, 0)))
