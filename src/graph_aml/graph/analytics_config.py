"""Configuration for NetworkX-based Neo4j graph analytics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from graph_aml.graph.exceptions import GraphAnalyticsConfigurationError

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_COMMUNITY_ALGORITHMS = {"connected_components", "greedy_modularity"}


@dataclass(frozen=True)
class GraphAnalyticsConfig:
    """Typed graph analytics configuration."""

    projection_relationship_types: tuple[str, ...] = (
        "OWNS",
        "SENT",
        "RECEIVED",
        "PAID_TO",
        "FLAGS_ACCOUNT",
        "INVOLVES_TRANSACTION",
    )
    account_flow_relationship_types: tuple[str, ...] = ("SENT", "RECEIVED")
    max_shortest_path_depth: int = 4
    pagerank_alpha: float = 0.85
    betweenness_sample_size: int | None = None
    community_algorithm: str = "connected_components"
    include_counterparties: bool = True
    include_alert_nodes: bool = True
    include_transaction_nodes: bool = True
    cycle_max_hops: int = 4
    high_risk_severities: tuple[str, ...] = ("high", "critical")

    def __post_init__(self) -> None:
        validate_graph_analytics_config(self)


def _tuple_of_strings(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values: tuple[str, ...] = (value,)
    elif isinstance(value, list | tuple):
        values = tuple(str(item) for item in value)
    else:
        raise GraphAnalyticsConfigurationError(f"{field_name} must be a string sequence")
    if not values or any(not item.strip() for item in values):
        raise GraphAnalyticsConfigurationError(f"{field_name} must be non-empty")
    return tuple(item.strip() for item in values)


def _bool_from_value(value: object, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalised = value.strip().lower()
        if normalised in {"true", "1", "yes", "y"}:
            return True
        if normalised in {"false", "0", "no", "n"}:
            return False
    raise GraphAnalyticsConfigurationError(f"{field_name} must be a boolean")


def _validate_relationship_types(values: tuple[str, ...], *, field_name: str) -> None:
    if not values:
        raise GraphAnalyticsConfigurationError(f"{field_name} must be non-empty")
    for value in values:
        if not _IDENTIFIER_PATTERN.fullmatch(value):
            raise GraphAnalyticsConfigurationError(
                f"{field_name} contains an unsafe relationship type: {value}"
            )


def validate_graph_analytics_config(config: GraphAnalyticsConfig) -> None:
    """Validate graph analytics configuration."""

    _validate_relationship_types(
        config.projection_relationship_types,
        field_name="projection_relationship_types",
    )
    _validate_relationship_types(
        config.account_flow_relationship_types,
        field_name="account_flow_relationship_types",
    )
    if config.max_shortest_path_depth <= 0:
        raise GraphAnalyticsConfigurationError("max_shortest_path_depth must be positive")
    if not 0 < config.pagerank_alpha < 1:
        raise GraphAnalyticsConfigurationError("pagerank_alpha must be between 0 and 1")
    if config.betweenness_sample_size is not None and config.betweenness_sample_size <= 0:
        raise GraphAnalyticsConfigurationError("betweenness_sample_size must be positive")
    if config.community_algorithm not in _COMMUNITY_ALGORITHMS:
        raise GraphAnalyticsConfigurationError("Unsupported community_algorithm")
    if config.cycle_max_hops < 2:
        raise GraphAnalyticsConfigurationError("cycle_max_hops must be at least 2")
    if not config.high_risk_severities or any(
        not str(value).strip() for value in config.high_risk_severities
    ):
        raise GraphAnalyticsConfigurationError("high_risk_severities must be non-empty")


def graph_analytics_config_from_mapping(
    payload: dict[str, object] | None,
) -> GraphAnalyticsConfig:
    """Build graph analytics config from a mapping."""

    data = {} if payload is None else dict(payload)
    try:
        config = GraphAnalyticsConfig(
            projection_relationship_types=_tuple_of_strings(
                data.get(
                    "projection_relationship_types",
                    GraphAnalyticsConfig.projection_relationship_types,
                ),
                field_name="projection_relationship_types",
            ),
            account_flow_relationship_types=_tuple_of_strings(
                data.get(
                    "account_flow_relationship_types",
                    GraphAnalyticsConfig.account_flow_relationship_types,
                ),
                field_name="account_flow_relationship_types",
            ),
            max_shortest_path_depth=int(
                cast(
                    Any,
                    data.get(
                        "max_shortest_path_depth",
                        GraphAnalyticsConfig.max_shortest_path_depth,
                    ),
                )
            ),
            pagerank_alpha=float(
                cast(
                    Any,
                    data.get("pagerank_alpha", GraphAnalyticsConfig.pagerank_alpha),
                )
            ),
            betweenness_sample_size=(
                None
                if data.get("betweenness_sample_size") is None
                else int(cast(Any, data["betweenness_sample_size"]))
            ),
            community_algorithm=str(
                data.get("community_algorithm", GraphAnalyticsConfig.community_algorithm)
            ),
            include_counterparties=_bool_from_value(
                data.get(
                    "include_counterparties",
                    GraphAnalyticsConfig.include_counterparties,
                ),
                field_name="include_counterparties",
            ),
            include_alert_nodes=_bool_from_value(
                data.get("include_alert_nodes", GraphAnalyticsConfig.include_alert_nodes),
                field_name="include_alert_nodes",
            ),
            include_transaction_nodes=_bool_from_value(
                data.get(
                    "include_transaction_nodes",
                    GraphAnalyticsConfig.include_transaction_nodes,
                ),
                field_name="include_transaction_nodes",
            ),
            cycle_max_hops=int(
                cast(
                    Any,
                    data.get("cycle_max_hops", GraphAnalyticsConfig.cycle_max_hops),
                )
            ),
            high_risk_severities=tuple(
                severity.lower()
                for severity in _tuple_of_strings(
                    data.get(
                        "high_risk_severities",
                        GraphAnalyticsConfig.high_risk_severities,
                    ),
                    field_name="high_risk_severities",
                )
            ),
        )
    except GraphAnalyticsConfigurationError:
        raise
    except Exception as exc:
        raise GraphAnalyticsConfigurationError(
            f"Invalid graph analytics configuration: {exc}"
        ) from exc
    return config


def load_graph_analytics_config(
    config_path: str | Path = "config/graph.yaml",
) -> GraphAnalyticsConfig:
    """Load graph analytics configuration from YAML."""

    path = Path(config_path)
    if not path.exists():
        return GraphAnalyticsConfig()
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise GraphAnalyticsConfigurationError(
            f"Failed to read graph analytics config: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise GraphAnalyticsConfigurationError("graph config file must contain a mapping")
    analytics_payload = payload.get("analytics", {})
    if analytics_payload is None:
        analytics_payload = {}
    if not isinstance(analytics_payload, dict):
        raise GraphAnalyticsConfigurationError("analytics config must be a mapping")
    return graph_analytics_config_from_mapping(cast(dict[str, object], analytics_payload))
