"""Tests for environment-backed configuration helpers."""

import pytest

from graph_aml.config.exceptions import EnvironmentVariableError
from graph_aml.config.loader import load_app_config
from graph_aml.config.settings import (
    build_neo4j_settings,
    build_postgres_dsn,
    get_env_value,
    get_mlflow_tracking_uri,
)


def test_get_env_value_returns_environment_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRAPH_AML_TEST_VALUE", "configured")

    assert get_env_value("GRAPH_AML_TEST_VALUE") == "configured"


def test_get_env_value_returns_default_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRAPH_AML_TEST_MISSING", raising=False)

    assert get_env_value("GRAPH_AML_TEST_MISSING", "default") == "default"


def test_get_env_value_raises_when_required_variable_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GRAPH_AML_REQUIRED", raising=False)

    with pytest.raises(EnvironmentVariableError):
        get_env_value("GRAPH_AML_REQUIRED", required=True)


def test_build_postgres_dsn_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var in (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ):
        monkeypatch.delenv(env_var, raising=False)

    config = load_app_config()

    assert (
        build_postgres_dsn(config)
        == "postgresql+psycopg2://graph_aml_user:change_me@localhost:5432/graph_aml"
    )


def test_build_postgres_dsn_respects_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db.local")
    monkeypatch.setenv("POSTGRES_PORT", "15432")
    monkeypatch.setenv("POSTGRES_DB", "aml_test")
    monkeypatch.setenv("POSTGRES_USER", "aml_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")

    config = load_app_config()

    assert build_postgres_dsn(config) == (
        "postgresql+psycopg2://aml_user:secret@db.local:15432/aml_test"
    )


def test_build_neo4j_settings_returns_expected_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
        monkeypatch.delenv(env_var, raising=False)

    config = load_app_config()

    assert build_neo4j_settings(config) == {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "change_me",
        "database": "neo4j",
    }


def test_get_mlflow_tracking_uri_returns_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

    assert get_mlflow_tracking_uri() == "http://localhost:5000"


def test_get_mlflow_tracking_uri_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    assert get_mlflow_tracking_uri() == "mlruns"
