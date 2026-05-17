"""Tests for Neo4j graph configuration loading."""

from pathlib import Path

import pytest

from graph_aml.graph import (
    GraphConfigurationError,
    Neo4jConfig,
    load_neo4j_config,
    neo4j_config_from_env,
    neo4j_config_from_mapping,
    validate_neo4j_config,
)


def test_neo4j_config_defaults_are_valid_when_password_is_supplied() -> None:
    config = Neo4jConfig(password="secret")

    validate_neo4j_config(config)


def test_missing_uri_raises_configuration_error() -> None:
    with pytest.raises(GraphConfigurationError):
        validate_neo4j_config(Neo4jConfig(uri="", password="secret"))


def test_missing_username_raises_configuration_error() -> None:
    with pytest.raises(GraphConfigurationError):
        validate_neo4j_config(Neo4jConfig(username="", password="secret"))


def test_missing_password_raises_configuration_error() -> None:
    with pytest.raises(GraphConfigurationError):
        validate_neo4j_config(Neo4jConfig(password=None))


def test_missing_database_raises_configuration_error() -> None:
    with pytest.raises(GraphConfigurationError):
        validate_neo4j_config(Neo4jConfig(database="", password="secret"))


def test_invalid_timeout_raises_configuration_error() -> None:
    with pytest.raises(GraphConfigurationError):
        validate_neo4j_config(Neo4jConfig(password="secret", connection_timeout_seconds=0))


def test_invalid_pool_size_raises_configuration_error() -> None:
    with pytest.raises(GraphConfigurationError):
        validate_neo4j_config(Neo4jConfig(password="secret", max_connection_pool_size=0))


def test_config_can_be_loaded_from_mapping() -> None:
    config = neo4j_config_from_mapping(
        {
            "uri": "bolt://example:7687",
            "username": "neo4j",
            "password": "secret",
            "database": "aml",
            "encrypted": True,
            "connection_timeout_seconds": 5,
        }
    )

    assert config.uri == "bolt://example:7687"
    assert config.username == "neo4j"
    assert config.password == "secret"
    assert config.database == "aml"
    assert config.encrypted is True
    assert config.connection_timeout_seconds == 5


def test_config_can_be_loaded_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEO4J_URI", "bolt://env:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "env-user")
    monkeypatch.setenv("NEO4J_PASSWORD", "env-secret")
    monkeypatch.setenv("NEO4J_DATABASE", "env-db")

    config = neo4j_config_from_env()

    assert config.uri == "bolt://env:7687"
    assert config.username == "env-user"
    assert config.password == "env-secret"
    assert config.database == "env-db"


def test_config_can_be_loaded_from_temporary_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAPH_TEST_PASSWORD", "yaml-secret")
    config_path = tmp_path / "graph.yaml"
    config_path.write_text(
        """
neo4j:
  uri: bolt://yaml:7687
  username: yaml-user
  password_env_var: GRAPH_TEST_PASSWORD
  database: yaml-db
  encrypted: false
  connection_timeout_seconds: 7
  max_connection_lifetime_seconds: 99
  max_connection_pool_size: 8
""",
        encoding="utf-8",
    )

    config = load_neo4j_config(config_path, env_file=None)

    assert config.uri == "bolt://yaml:7687"
    assert config.username == "yaml-user"
    assert config.password == "yaml-secret"
    assert config.database == "yaml-db"
    assert config.connection_timeout_seconds == 7
    assert config.max_connection_lifetime_seconds == 99
    assert config.max_connection_pool_size == 8


def test_environment_overrides_yaml_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAPH_TEST_PASSWORD", "yaml-secret")
    monkeypatch.setenv("NEO4J_URI", "bolt://env:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "env-user")
    monkeypatch.setenv("NEO4J_PASSWORD", "env-secret")
    monkeypatch.setenv("NEO4J_DATABASE", "env-db")
    config_path = tmp_path / "graph.yaml"
    config_path.write_text(
        """
neo4j:
  uri: bolt://yaml:7687
  username: yaml-user
  password_env_var: GRAPH_TEST_PASSWORD
  database: yaml-db
""",
        encoding="utf-8",
    )

    config = load_neo4j_config(config_path, env_file=None)

    assert config.uri == "bolt://env:7687"
    assert config.username == "env-user"
    assert config.password == "env-secret"
    assert config.database == "env-db"


def test_no_neo4j_connection_is_attempted_during_config_loading(tmp_path: Path) -> None:
    config_path = tmp_path / "graph.yaml"
    config_path.write_text(
        """
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: secret
  database: neo4j
""",
        encoding="utf-8",
    )

    assert load_neo4j_config(config_path, env_file=None).password == "secret"
