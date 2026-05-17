"""NetworkX-based graph analytics feature computation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import cast

import networkx as nx
import pandas as pd
from neo4j import Driver

from graph_aml.graph.analytics_config import GraphAnalyticsConfig
from graph_aml.graph.exceptions import GraphAnalyticsError, GraphProjectionError
from graph_aml.graph.mapping import normalise_graph_scalar
from graph_aml.graph.projection import (
    ProjectedGraphData,
    build_account_flow_graph,
    build_networkx_graph,
    read_projected_graph_data,
)

GRAPH_ANALYTICS_FEATURE_COLUMNS = (
    "account_id",
    "degree",
    "in_degree",
    "out_degree",
    "degree_centrality",
    "in_degree_centrality",
    "out_degree_centrality",
    "pagerank_score",
    "betweenness_centrality",
    "clustering_coefficient",
    "community_id",
    "community_size",
    "cycle_count",
    "fan_in_count",
    "fan_out_count",
    "alert_count",
    "high_risk_alert_count",
    "shortest_path_to_flagged",
    "neighbour_account_count",
    "counterparty_count",
    "transaction_count",
    "total_sent_amount",
    "total_received_amount",
    "graph_component_size",
)

_NUMERIC_COLUMNS = tuple(
    column for column in GRAPH_ANALYTICS_FEATURE_COLUMNS if column != "account_id"
)
_NULLABLE_COLUMNS = ("shortest_path_to_flagged",)


@dataclass(frozen=True)
class GraphAnalyticsResult:
    """Graph analytics features and metadata."""

    features: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def _normalise_account_ids(account_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(account_ids, list | tuple):
        raise GraphAnalyticsError("account_ids must be a list or tuple")
    values = sorted({str(value).strip() for value in account_ids if str(value).strip()})
    return tuple(values)


def initialise_account_feature_frame(account_ids: tuple[str, ...] | list[str]) -> pd.DataFrame:
    """Return a zero-filled account feature frame."""

    accounts = _normalise_account_ids(account_ids)
    rows: list[dict[str, object]] = []
    for account_id in accounts:
        row: dict[str, object] = {column: 0 for column in GRAPH_ANALYTICS_FEATURE_COLUMNS}
        row["account_id"] = account_id
        row["shortest_path_to_flagged"] = None
        rows.append(row)
    return pd.DataFrame(rows, columns=GRAPH_ANALYTICS_FEATURE_COLUMNS)


def _safe_graph(graph: object) -> nx.Graph | nx.DiGraph:
    if not isinstance(graph, nx.Graph):
        raise GraphAnalyticsError("graph must be a NetworkX graph")
    return graph


def compute_degree_features(
    graph: object,
    account_ids: tuple[str, ...] | list[str],
) -> pd.DataFrame:
    """Compute account degree and centrality features."""

    nx_graph = _safe_graph(graph)
    accounts = _normalise_account_ids(account_ids)
    try:
        degree_centrality = nx.degree_centrality(nx_graph) if nx_graph.number_of_nodes() else {}
        if nx_graph.is_directed():
            in_degree_centrality = nx.in_degree_centrality(cast(nx.DiGraph, nx_graph))
            out_degree_centrality = nx.out_degree_centrality(cast(nx.DiGraph, nx_graph))
        else:
            in_degree_centrality = degree_centrality
            out_degree_centrality = degree_centrality
        rows = []
        for account_id in accounts:
            rows.append(
                {
                    "account_id": account_id,
                    "degree": int(nx_graph.degree(account_id)) if account_id in nx_graph else 0,
                    "in_degree": int(nx_graph.in_degree(account_id))
                    if nx_graph.is_directed() and account_id in nx_graph
                    else int(nx_graph.degree(account_id))
                    if account_id in nx_graph
                    else 0,
                    "out_degree": int(nx_graph.out_degree(account_id))
                    if nx_graph.is_directed() and account_id in nx_graph
                    else int(nx_graph.degree(account_id))
                    if account_id in nx_graph
                    else 0,
                    "degree_centrality": float(degree_centrality.get(account_id, 0.0)),
                    "in_degree_centrality": float(in_degree_centrality.get(account_id, 0.0)),
                    "out_degree_centrality": float(out_degree_centrality.get(account_id, 0.0)),
                }
            )
        return (
            pd.DataFrame(
                rows,
                columns=[
                    "account_id",
                    "degree",
                    "in_degree",
                    "out_degree",
                    "degree_centrality",
                    "in_degree_centrality",
                    "out_degree_centrality",
                ],
            )
            .sort_values("account_id")
            .reset_index(drop=True)
        )
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to compute degree features: {exc}") from exc


def compute_influence_features(
    graph: object,
    account_ids: tuple[str, ...] | list[str],
    config: GraphAnalyticsConfig | None = None,
) -> pd.DataFrame:
    """Compute PageRank and betweenness centrality."""

    nx_graph = _safe_graph(graph)
    accounts = _normalise_account_ids(account_ids)
    resolved_config = GraphAnalyticsConfig() if config is None else config
    try:
        if nx_graph.number_of_nodes() == 0:
            pagerank: dict[str, float] = {}
            betweenness: dict[str, float] = {}
        else:
            pagerank = {
                str(key): float(value)
                for key, value in nx.pagerank(
                    nx_graph,
                    alpha=resolved_config.pagerank_alpha,
                ).items()
            }
            nodes = sorted(str(node) for node in nx_graph.nodes)
            if (
                resolved_config.betweenness_sample_size is not None
                and resolved_config.betweenness_sample_size < len(nodes)
            ):
                sources = nodes[: resolved_config.betweenness_sample_size]
                betweenness = {
                    str(key): float(value)
                    for key, value in nx.betweenness_centrality_subset(
                        nx_graph,
                        sources=sources,
                        targets=nodes,
                        normalized=True,
                    ).items()
                }
            else:
                betweenness = {
                    str(key): float(value)
                    for key, value in nx.betweenness_centrality(nx_graph).items()
                }
        return pd.DataFrame(
            [
                {
                    "account_id": account_id,
                    "pagerank_score": float(pagerank.get(account_id, 0.0)),
                    "betweenness_centrality": float(betweenness.get(account_id, 0.0)),
                }
                for account_id in accounts
            ],
            columns=["account_id", "pagerank_score", "betweenness_centrality"],
        )
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to compute influence features: {exc}") from exc


def _communities_for_graph(
    graph: nx.Graph,
    accounts: tuple[str, ...],
    config: GraphAnalyticsConfig,
) -> list[set[str]]:
    if graph.number_of_nodes() == 0:
        return [{account_id} for account_id in accounts]
    if config.community_algorithm == "greedy_modularity" and graph.number_of_edges() > 0:
        communities = [
            set(map(str, community))
            for community in nx.community.greedy_modularity_communities(graph)
        ]
    else:
        communities = [set(map(str, component)) for component in nx.connected_components(graph)]
    covered = set().union(*communities) if communities else set()
    for account_id in accounts:
        if account_id not in covered:
            communities.append({account_id})
    return communities


def compute_community_features(
    graph: object,
    account_ids: tuple[str, ...] | list[str],
    config: GraphAnalyticsConfig | None = None,
) -> pd.DataFrame:
    """Compute clustering, community, and component features."""

    nx_graph = _safe_graph(graph)
    accounts = _normalise_account_ids(account_ids)
    resolved_config = GraphAnalyticsConfig() if config is None else config
    try:
        undirected = nx_graph.to_undirected() if nx_graph.is_directed() else nx_graph.copy()
        clustering = nx.clustering(undirected) if undirected.number_of_nodes() else {}
        communities = _communities_for_graph(undirected, accounts, resolved_config)

        def community_sort_key(community: set[str]) -> str:
            account_members = sorted(account for account in community if account in accounts)
            return account_members[0] if account_members else sorted(community)[0]

        sorted_communities = sorted(communities, key=community_sort_key)
        account_to_community: dict[str, tuple[int, int, int]] = {}
        for index, community in enumerate(sorted_communities, start=1):
            account_members = {account for account in community if account in accounts}
            community_size = max(len(account_members), 1)
            component_size = max(len(community), 1)
            for account_id in account_members or community:
                if account_id in accounts:
                    account_to_community[account_id] = (
                        index,
                        community_size,
                        component_size,
                    )
        rows = []
        for account_id in accounts:
            community_id, community_size, component_size = account_to_community.get(
                account_id,
                (len(account_to_community) + 1, 1, 1),
            )
            rows.append(
                {
                    "account_id": account_id,
                    "clustering_coefficient": float(clustering.get(account_id, 0.0)),
                    "community_id": int(community_id),
                    "community_size": int(community_size),
                    "graph_component_size": int(component_size),
                }
            )
        return pd.DataFrame(
            rows,
            columns=[
                "account_id",
                "clustering_coefficient",
                "community_id",
                "community_size",
                "graph_component_size",
            ],
        )
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to compute community features: {exc}") from exc


def compute_cycle_features(
    graph: object,
    account_ids: tuple[str, ...] | list[str],
    config: GraphAnalyticsConfig | None = None,
) -> pd.DataFrame:
    """Count directed simple cycles involving each account."""

    nx_graph = _safe_graph(graph)
    accounts = _normalise_account_ids(account_ids)
    resolved_config = GraphAnalyticsConfig() if config is None else config
    cycle_counts = {account_id: 0 for account_id in accounts}
    try:
        directed_graph = nx_graph if nx_graph.is_directed() else nx_graph.to_directed()
        for index, cycle in enumerate(nx.simple_cycles(cast(nx.DiGraph, directed_graph))):
            if index >= 10000:
                break
            cycle_nodes = tuple(str(node) for node in cycle)
            if len(cycle_nodes) > resolved_config.cycle_max_hops:
                continue
            for account_id in accounts:
                if account_id in cycle_nodes:
                    cycle_counts[account_id] += 1
        return pd.DataFrame(
            [
                {"account_id": account_id, "cycle_count": int(cycle_counts[account_id])}
                for account_id in accounts
            ],
            columns=["account_id", "cycle_count"],
        )
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to compute cycle features: {exc}") from exc


def _edge_transaction_ids(attrs: dict[str, object]) -> set[str]:
    values = attrs.get("transaction_ids", attrs.get("transaction_id", []))
    if isinstance(values, str):
        return {values}
    if isinstance(values, list | tuple | set):
        return {str(value) for value in values if str(value).strip()}
    return set()


def compute_flow_features(
    account_flow_graph: object,
    account_ids: tuple[str, ...] | list[str],
) -> pd.DataFrame:
    """Compute account flow fan-in, fan-out, and amount features."""

    graph = _safe_graph(account_flow_graph)
    accounts = _normalise_account_ids(account_ids)
    rows = []
    try:
        for account_id in accounts:
            incoming_sources: set[str] = set()
            outgoing_targets: set[str] = set()
            neighbour_accounts: set[str] = set()
            counterparties: set[str] = set()
            transaction_ids: set[str] = set()
            total_sent = 0.0
            total_received = 0.0
            if account_id in graph:
                for source, _, attrs in graph.in_edges(account_id, data=True):
                    incoming_sources.add(str(source))
                    if graph.nodes[source].get("node_type") == "Account":
                        neighbour_accounts.add(str(source))
                    transaction_ids.update(_edge_transaction_ids(dict(attrs)))
                    total_received += float(attrs.get("amount") or 0.0)
                for _, target, attrs in graph.out_edges(account_id, data=True):
                    outgoing_targets.add(str(target))
                    target_type = graph.nodes[target].get("node_type")
                    if target_type == "Account":
                        neighbour_accounts.add(str(target))
                    if target_type == "Counterparty":
                        counterparties.add(str(target))
                    transaction_ids.update(_edge_transaction_ids(dict(attrs)))
                    total_sent += float(attrs.get("amount") or 0.0)
            rows.append(
                {
                    "account_id": account_id,
                    "fan_in_count": len(incoming_sources),
                    "fan_out_count": len(outgoing_targets),
                    "neighbour_account_count": len(neighbour_accounts),
                    "counterparty_count": len(counterparties),
                    "transaction_count": len(transaction_ids),
                    "total_sent_amount": total_sent,
                    "total_received_amount": total_received,
                }
            )
        return pd.DataFrame(
            rows,
            columns=[
                "account_id",
                "fan_in_count",
                "fan_out_count",
                "neighbour_account_count",
                "counterparty_count",
                "transaction_count",
                "total_sent_amount",
                "total_received_amount",
            ],
        )
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to compute flow features: {exc}") from exc


def compute_alert_proximity_features(
    graph: object,
    account_ids: tuple[str, ...] | list[str],
    config: GraphAnalyticsConfig | None = None,
) -> pd.DataFrame:
    """Compute account proximity to alert nodes."""

    nx_graph = _safe_graph(graph)
    accounts = _normalise_account_ids(account_ids)
    resolved_config = GraphAnalyticsConfig() if config is None else config
    high_risk = {severity.lower() for severity in resolved_config.high_risk_severities}
    try:
        undirected = nx_graph.to_undirected() if nx_graph.is_directed() else nx_graph.copy()
        high_risk_alerts = {
            str(node)
            for node, attrs in nx_graph.nodes(data=True)
            if attrs.get("node_type") == "Alert"
            and str(attrs.get("severity", "")).lower() in high_risk
        }
        rows = []
        for account_id in accounts:
            alert_count = 0
            high_risk_alert_count = 0
            distance: int | None = None
            if account_id in undirected:
                for neighbour in undirected.neighbors(account_id):
                    attrs = nx_graph.nodes[neighbour]
                    if attrs.get("node_type") == "Alert":
                        alert_count += 1
                        if str(attrs.get("severity", "")).lower() in high_risk:
                            high_risk_alert_count += 1
                distances = nx.single_source_shortest_path_length(
                    undirected,
                    account_id,
                    cutoff=resolved_config.max_shortest_path_depth,
                )
                reachable = [
                    value
                    for node, value in distances.items()
                    if str(node) in high_risk_alerts
                    and value <= resolved_config.max_shortest_path_depth
                ]
                distance = min(reachable) if reachable else None
            rows.append(
                {
                    "account_id": account_id,
                    "alert_count": alert_count,
                    "high_risk_alert_count": high_risk_alert_count,
                    "shortest_path_to_flagged": distance,
                }
            )
        frame = pd.DataFrame(
            rows,
            columns=[
                "account_id",
                "alert_count",
                "high_risk_alert_count",
                "shortest_path_to_flagged",
            ],
        )
        if "shortest_path_to_flagged" in frame.columns:
            frame["shortest_path_to_flagged"] = (
                frame["shortest_path_to_flagged"]
                .astype(object)
                .where(pd.notna(frame["shortest_path_to_flagged"]), None)
            )
        return frame
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to compute alert proximity features: {exc}") from exc


def merge_graph_feature_frames(
    frames: tuple[pd.DataFrame, ...] | list[pd.DataFrame],
    account_ids: tuple[str, ...] | list[str],
) -> pd.DataFrame:
    """Merge graph feature frames into the canonical feature schema."""

    accounts = _normalise_account_ids(account_ids)
    merged = initialise_account_feature_frame(accounts)
    try:
        for frame in frames:
            if not isinstance(frame, pd.DataFrame) or "account_id" not in frame.columns:
                raise GraphAnalyticsError("feature frames must include account_id")
            merged = merged.merge(
                frame.copy(deep=True),
                on="account_id",
                how="left",
                suffixes=("", "_new"),
            )
            for column in list(merged.columns):
                if column.endswith("_new"):
                    base = column.removesuffix("_new")
                    merged[base] = merged[column].combine_first(merged.get(base))
                    merged = merged.drop(columns=[column])
        for column in GRAPH_ANALYTICS_FEATURE_COLUMNS:
            if column not in merged.columns:
                merged[column] = None if column in _NULLABLE_COLUMNS else 0
        for column in _NUMERIC_COLUMNS:
            if column in _NULLABLE_COLUMNS:
                continue
            merged[column] = merged[column].fillna(0)
        merged = merged[list(GRAPH_ANALYTICS_FEATURE_COLUMNS)]
        return merged.sort_values("account_id").reset_index(drop=True)
    except GraphAnalyticsError:
        raise
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to merge graph feature frames: {exc}") from exc


def _summary_for_features(
    features: pd.DataFrame,
    full_graph: nx.Graph | nx.DiGraph,
    projected: ProjectedGraphData,
) -> dict[str, object]:
    return {
        "account_count": int(len(features)),
        "feature_count": int(len(features.columns)),
        "graph_node_count": int(full_graph.number_of_nodes()),
        "graph_relationship_count": int(full_graph.number_of_edges()),
        "nonzero_pagerank_count": int((features["pagerank_score"] > 0).sum())
        if not features.empty
        else 0,
        "nonzero_cycle_count": int((features["cycle_count"] > 0).sum())
        if not features.empty
        else 0,
        "high_risk_alert_connected_account_count": int(
            (features["high_risk_alert_count"] > 0).sum()
        )
        if not features.empty
        else 0,
        "community_count": int(features["community_id"].nunique()) if not features.empty else 0,
        "projected_account_count": len(projected.account_ids),
        "projected_alert_count": len(projected.alert_ids),
        "projected_transaction_count": len(projected.transaction_ids),
    }


def compute_graph_analytics_features(
    projected: ProjectedGraphData,
    config: GraphAnalyticsConfig | None = None,
) -> GraphAnalyticsResult:
    """Compute all account-level graph analytics features."""

    if not isinstance(projected, ProjectedGraphData):
        raise GraphAnalyticsError("projected must be ProjectedGraphData")
    resolved_config = GraphAnalyticsConfig() if config is None else config
    try:
        full_graph = build_networkx_graph(projected, directed=True)
        account_flow_graph = build_account_flow_graph(projected)
        account_ids = projected.account_ids
        frames = (
            compute_degree_features(full_graph, account_ids),
            compute_influence_features(full_graph, account_ids, resolved_config),
            compute_community_features(full_graph, account_ids, resolved_config),
            compute_cycle_features(account_flow_graph, account_ids, resolved_config),
            compute_flow_features(account_flow_graph, account_ids),
            compute_alert_proximity_features(full_graph, account_ids, resolved_config),
        )
        features = merge_graph_feature_frames(frames, account_ids)
        summary = _summary_for_features(features, full_graph, projected)
        metadata = {
            "config": asdict(resolved_config),
            "projection": dict(projected.metadata),
            "account_flow_node_count": account_flow_graph.number_of_nodes(),
            "account_flow_edge_count": account_flow_graph.number_of_edges(),
        }
        return GraphAnalyticsResult(features=features, summary=summary, metadata=metadata)
    except (GraphAnalyticsError, GraphProjectionError):
        raise
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to compute graph analytics features: {exc}") from exc


def compute_graph_analytics_features_from_neo4j(
    driver: Driver,
    config: GraphAnalyticsConfig | None = None,
    database: str | None = None,
) -> GraphAnalyticsResult:
    """Read Neo4j graph projection and compute account graph features."""

    resolved_config = GraphAnalyticsConfig() if config is None else config
    try:
        projected = read_projected_graph_data(driver, resolved_config, database=database)
        return compute_graph_analytics_features(projected, resolved_config)
    except (GraphAnalyticsError, GraphProjectionError):
        raise
    except Exception as exc:
        raise GraphAnalyticsError(
            f"Failed to compute graph analytics features from Neo4j: {exc}"
        ) from exc


def graph_features_to_records(features: pd.DataFrame) -> list[dict[str, object]]:
    """Convert graph feature frame to JSON-safe records."""

    if not isinstance(features, pd.DataFrame):
        raise GraphAnalyticsError("features must be a DataFrame")
    frame = features.copy(deep=True)
    for column in GRAPH_ANALYTICS_FEATURE_COLUMNS:
        if column not in frame.columns:
            frame[column] = None if column in _NULLABLE_COLUMNS else 0
    frame = frame[list(GRAPH_ANALYTICS_FEATURE_COLUMNS)]
    records: list[dict[str, object]] = []
    for record in frame.to_dict(orient="records"):
        records.append({key: normalise_graph_scalar(value) for key, value in record.items()})
    return records


def graph_features_from_records(records: list[dict[str, object]]) -> pd.DataFrame:
    """Build graph feature DataFrame from records."""

    if not isinstance(records, list):
        raise GraphAnalyticsError("records must be a list")
    if any(not isinstance(record, dict) for record in records):
        raise GraphAnalyticsError("records must contain dictionaries")
    frame = pd.DataFrame(records)
    if frame.empty:
        return pd.DataFrame(columns=GRAPH_ANALYTICS_FEATURE_COLUMNS)
    if "account_id" not in frame.columns:
        raise GraphAnalyticsError("records must include account_id")
    return merge_graph_feature_frames([frame], tuple(str(value) for value in frame["account_id"]))


def graph_analytics_result_to_dict(result: GraphAnalyticsResult) -> dict[str, object]:
    """Convert graph analytics result to a JSON-safe dictionary."""

    if not isinstance(result, GraphAnalyticsResult):
        raise GraphAnalyticsError("result must be GraphAnalyticsResult")
    return {
        "features": graph_features_to_records(result.features),
        "summary": dict(result.summary),
        "metadata": dict(result.metadata),
    }
