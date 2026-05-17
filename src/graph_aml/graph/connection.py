"""Neo4j driver lifecycle helpers."""

from __future__ import annotations

from typing import Any, cast

from neo4j import Driver, GraphDatabase

from graph_aml.graph.config import Neo4jConfig, load_neo4j_config, validate_neo4j_config
from graph_aml.graph.exceptions import GraphConnectionError


def create_neo4j_driver(config: Neo4jConfig | None = None) -> Driver:
    """Create an authenticated Neo4j driver without verifying connectivity."""

    try:
        resolved = config or load_neo4j_config()
        validate_neo4j_config(resolved)
        return GraphDatabase.driver(
            resolved.uri,
            auth=(resolved.username, cast(str, resolved.password)),
            encrypted=resolved.encrypted,
            connection_timeout=resolved.connection_timeout_seconds,
            max_connection_lifetime=resolved.max_connection_lifetime_seconds,
            max_connection_pool_size=resolved.max_connection_pool_size,
        )
    except GraphConnectionError:
        raise
    except Exception as exc:
        raise GraphConnectionError(f"Could not create Neo4j driver: {exc}") from exc


def close_neo4j_driver(driver: Driver | None) -> None:
    """Close a Neo4j driver if one was created."""

    if driver is None:
        return
    try:
        driver.close()
    except Exception as exc:
        raise GraphConnectionError(f"Could not close Neo4j driver: {exc}") from exc


def verify_neo4j_connectivity(driver: Driver) -> None:
    """Verify a Neo4j driver can connect to the server."""

    try:
        driver.verify_connectivity()
    except Exception as exc:
        raise GraphConnectionError(f"Neo4j connectivity verification failed: {exc}") from exc


def get_neo4j_server_info(driver: Driver) -> dict[str, object]:
    """Return compact JSON-serialisable Neo4j server information."""

    try:
        raw_info = driver.get_server_info()
        if isinstance(raw_info, dict):
            return {str(key): _json_safe(value) for key, value in raw_info.items()}
        return {
            "agent": _json_safe(getattr(raw_info, "agent", None)),
            "protocol_version": _json_safe(getattr(raw_info, "protocol_version", None)),
            "address": _json_safe(getattr(raw_info, "address", None)),
        }
    except Exception as exc:
        raise GraphConnectionError(f"Could not fetch Neo4j server info: {exc}") from exc


def create_verified_neo4j_driver(config: Neo4jConfig | None = None) -> Driver:
    """Create a Neo4j driver and verify connectivity before returning it."""

    driver = create_neo4j_driver(config)
    try:
        verify_neo4j_connectivity(driver)
        return driver
    except Exception:
        close_neo4j_driver(driver)
        raise


def _json_safe(value: Any) -> object:
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)
