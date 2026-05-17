"""Neo4j configuration loading for local graph utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv
from yaml import YAMLError

from graph_aml.graph.exceptions import GraphConfigurationError


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str | None = None
    database: str = "neo4j"
    encrypted: bool = False
    connection_timeout_seconds: int = 10
    max_connection_lifetime_seconds: int = 3600
    max_connection_pool_size: int = 50


def load_neo4j_config(
    config_path: str | Path = "config/graph.yaml",
    env_file: str | Path | None = ".env",
) -> Neo4jConfig:
    """Load Neo4j settings from YAML and environment variables."""

    if env_file is not None and Path(env_file).is_file():
        load_dotenv(Path(env_file), override=False)

    payload: dict[str, object] = {}
    path = Path(config_path)
    if path.is_file():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except YAMLError as exc:
            raise GraphConfigurationError(
                f"Could not parse Neo4j config file {path}: {exc}"
            ) from exc
        if not isinstance(loaded, dict):
            raise GraphConfigurationError(f"Neo4j config root must be a mapping: {path}")
        raw_payload = loaded.get("neo4j", loaded)
        if not isinstance(raw_payload, dict):
            raise GraphConfigurationError("neo4j configuration section must be a mapping")
        payload = dict(raw_payload)

    config = neo4j_config_from_mapping(payload) if payload else Neo4jConfig()
    env_config = neo4j_config_from_env()
    merged = Neo4jConfig(
        uri=env_config.uri or config.uri,
        username=env_config.username or config.username,
        password=env_config.password if env_config.password is not None else config.password,
        database=env_config.database or config.database,
        encrypted=config.encrypted,
        connection_timeout_seconds=config.connection_timeout_seconds,
        max_connection_lifetime_seconds=config.max_connection_lifetime_seconds,
        max_connection_pool_size=config.max_connection_pool_size,
    )
    validate_neo4j_config(merged)
    return merged


def neo4j_config_from_mapping(payload: dict[str, object]) -> Neo4jConfig:
    """Build Neo4j configuration from a plain mapping."""

    try:
        password = _optional_string(payload.get("password"))
        password_env_var = _optional_string(payload.get("password_env_var"))
        password_env_var = password_env_var or _optional_string(payload.get("password_env"))
        if password is None and password_env_var:
            password = os.getenv(password_env_var)
        username = _optional_string(payload.get("username"))
        if username is None:
            username = _optional_string(payload.get("user"))
        if username is None and _optional_string(payload.get("user_env")):
            username = os.getenv(str(payload["user_env"]))
        uri = _optional_string(payload.get("uri"))
        if uri is None and _optional_string(payload.get("uri_env")):
            uri = os.getenv(str(payload["uri_env"]))
        database = _optional_string(payload.get("database"))
        defaults = payload.get("defaults")
        if isinstance(defaults, dict):
            uri = uri or _optional_string(defaults.get("uri"))
            username = username or _optional_string(defaults.get("username"))
            username = username or _optional_string(defaults.get("user"))
            database = database or _optional_string(defaults.get("database"))
        connection = payload.get("connection")
        connection_payload = connection if isinstance(connection, dict) else payload
        return Neo4jConfig(
            uri=uri or Neo4jConfig.uri,
            username=username or Neo4jConfig.username,
            password=password,
            database=database or Neo4jConfig.database,
            encrypted=_to_bool(payload.get("encrypted", Neo4jConfig.encrypted)),
            connection_timeout_seconds=_to_int(
                connection_payload.get("connection_timeout_seconds"),
                Neo4jConfig.connection_timeout_seconds,
            ),
            max_connection_lifetime_seconds=_to_int(
                connection_payload.get("max_connection_lifetime_seconds"),
                Neo4jConfig.max_connection_lifetime_seconds,
            ),
            max_connection_pool_size=_to_int(
                connection_payload.get("max_connection_pool_size"),
                Neo4jConfig.max_connection_pool_size,
            ),
        )
    except (TypeError, ValueError) as exc:
        raise GraphConfigurationError(f"Invalid Neo4j configuration mapping: {exc}") from exc


def neo4j_config_from_env() -> Neo4jConfig:
    """Build Neo4j configuration from environment variables only."""

    return Neo4jConfig(
        uri=os.getenv("NEO4J_URI", ""),
        username=str(os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER") or ""),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", ""),
    )


def validate_neo4j_config(config: Neo4jConfig) -> None:
    """Validate Neo4j configuration before authenticated driver creation."""

    if not str(config.uri).strip():
        raise GraphConfigurationError("Neo4j URI is required")
    if not str(config.username).strip():
        raise GraphConfigurationError("Neo4j username is required")
    if not str(config.password or "").strip():
        raise GraphConfigurationError("Neo4j password is required")
    if not str(config.database).strip():
        raise GraphConfigurationError("Neo4j database is required")
    if config.connection_timeout_seconds <= 0:
        raise GraphConfigurationError("Neo4j connection timeout must be positive")
    if config.max_connection_lifetime_seconds <= 0:
        raise GraphConfigurationError("Neo4j max connection lifetime must be positive")
    if config.max_connection_pool_size <= 0:
        raise GraphConfigurationError("Neo4j max connection pool size must be positive")


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _to_int(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str | float):
        return int(value)
    raise ValueError(f"expected integer-compatible value, got {type(value).__name__}")
