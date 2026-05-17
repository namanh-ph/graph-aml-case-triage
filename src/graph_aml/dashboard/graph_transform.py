"""Graph frame transformation helpers for dashboard rendering."""

from __future__ import annotations

import json

import pandas as pd

from graph_aml.dashboard.config import DashboardConfig
from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.graph_data import GRAPH_VIEW_EDGE_COLUMNS, GRAPH_VIEW_NODE_COLUMNS


def _json_safe(value: object) -> object:
    if isinstance(value, dict | list | tuple):
        return json.loads(json.dumps(value, default=str))
    if value is None:
        return {}
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def normalise_graph_node_frame(nodes: pd.DataFrame) -> pd.DataFrame:
    """Normalise node rows to dashboard graph node columns."""

    if not isinstance(nodes, pd.DataFrame):
        raise DashboardDataError("nodes must be a DataFrame")
    if nodes.empty:
        return pd.DataFrame(columns=GRAPH_VIEW_NODE_COLUMNS)
    frame = nodes.copy()
    if "node_id" not in frame.columns:
        if "account_id" in frame.columns:
            frame["node_id"] = frame["account_id"]
        else:
            raise DashboardDataError("nodes require node_id or account_id")
    frame["node_type"] = frame.get("node_type", "account").fillna("account")
    frame["label"] = frame.get("label", frame["node_id"]).fillna(frame["node_id"])
    for column in ("risk_score", "risk_band", "community_id", "metadata"):
        if column not in frame.columns:
            frame[column] = None if column != "metadata" else {}
    frame["metadata"] = frame["metadata"].map(_json_safe)
    frame = frame.loc[:, list(GRAPH_VIEW_NODE_COLUMNS)]
    frame["node_id"] = frame["node_id"].astype(str)
    return frame.drop_duplicates("node_id").sort_values("node_id").reset_index(drop=True)


def normalise_graph_edge_frame(edges: pd.DataFrame) -> pd.DataFrame:
    """Normalise edge rows to dashboard graph edge columns."""

    if not isinstance(edges, pd.DataFrame):
        raise DashboardDataError("edges must be a DataFrame")
    if edges.empty:
        return pd.DataFrame(columns=GRAPH_VIEW_EDGE_COLUMNS)
    frame = edges.copy()
    if "source_id" not in frame.columns or "target_id" not in frame.columns:
        raise DashboardDataError("edges require source_id and target_id")
    for column, default in (
        ("edge_type", "relationship"),
        ("weight", 1.0),
        ("transaction_id", None),
        ("amount", None),
        ("metadata", {}),
    ):
        if column not in frame.columns:
            frame[column] = default
    frame["metadata"] = frame["metadata"].map(_json_safe)
    frame = frame.loc[:, list(GRAPH_VIEW_EDGE_COLUMNS)]
    frame["source_id"] = frame["source_id"].astype(str)
    frame["target_id"] = frame["target_id"].astype(str)
    return (
        frame.drop_duplicates(["source_id", "target_id", "edge_type", "transaction_id"])
        .sort_values(["source_id", "target_id", "edge_type", "transaction_id"], na_position="last")
        .reset_index(drop=True)
    )


def build_graph_view_frames(
    context: dict[str, pd.DataFrame],
    config: DashboardConfig | None = None,
) -> dict[str, pd.DataFrame]:
    """Build clipped, render-ready graph frames."""

    try:
        resolved = config or DashboardConfig()
        nodes = normalise_graph_node_frame(context.get("nodes", pd.DataFrame()))
        edges = normalise_graph_edge_frame(context.get("edges", pd.DataFrame()))
        nodes = nodes.head(resolved.graph_view.max_nodes).copy()
        keep = set(nodes["node_id"].astype(str))
        edges = edges[
            edges["source_id"].astype(str).isin(keep) & edges["target_id"].astype(str).isin(keep)
        ].head(resolved.graph_view.max_edges)
        return {"nodes": nodes.reset_index(drop=True), "edges": edges.reset_index(drop=True)}
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to build graph view frames: {exc}") from exc


def calculate_node_sizes(
    nodes: pd.DataFrame,
    min_size: int = 12,
    max_size: int = 42,
) -> pd.Series:
    """Calculate deterministic node sizes from risk scores."""

    if min_size <= 0 or max_size <= 0 or min_size > max_size:
        raise DashboardDataError("node size bounds are invalid")
    if nodes.empty or "risk_score" not in nodes.columns:
        return pd.Series([min_size] * len(nodes), index=nodes.index, dtype="float64")
    scores = pd.to_numeric(nodes["risk_score"], errors="coerce").fillna(0).clip(0, 100)
    return min_size + (scores / 100.0) * (max_size - min_size)


def summarise_graph_view(nodes: pd.DataFrame, edges: pd.DataFrame) -> dict[str, object]:
    """Build a JSON-serialisable graph summary."""

    if not isinstance(nodes, pd.DataFrame) or not isinstance(edges, pd.DataFrame):
        raise DashboardDataError("nodes and edges must be DataFrames")
    node_types = nodes.get("node_type", pd.Series(dtype="object")).astype(str)
    risk_scores = pd.to_numeric(
        nodes.get("risk_score", pd.Series(dtype="float64")), errors="coerce"
    )
    return {
        "node_count": int(len(nodes)),
        "edge_count": int(len(edges)),
        "account_count": int((node_types == "account").sum()),
        "transaction_count": int((node_types == "transaction").sum()),
        "counterparty_count": int((node_types == "counterparty").sum()),
        "alert_count": int((node_types == "alert").sum()),
        "case_count": int((node_types == "case").sum()),
        "community_count": int(
            nodes.get("community_id", pd.Series(dtype="object")).dropna().nunique()
        ),
        "max_risk_score": None if risk_scores.dropna().empty else float(risk_scores.max()),
    }
