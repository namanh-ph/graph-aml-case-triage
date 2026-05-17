"""Static validation tests for Docker Compose local infrastructure."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"


def load_compose() -> dict[str, Any]:
    loaded = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_docker_compose_file_exists() -> None:
    assert COMPOSE_FILE.is_file()


def test_docker_compose_parses_as_yaml() -> None:
    assert load_compose()


def test_top_level_compose_keys_exist() -> None:
    compose = load_compose()

    assert {"services", "volumes", "networks"} <= set(compose)


def test_required_services_exist() -> None:
    services = load_compose()["services"]

    assert {"postgres", "neo4j", "mlflow"} <= set(services)


def test_postgres_service_has_required_configuration() -> None:
    postgres = load_compose()["services"]["postgres"]

    assert postgres["image"]
    assert "environment" in postgres
    assert "ports" in postgres
    assert "volumes" in postgres
    assert "healthcheck" in postgres


def test_neo4j_service_has_required_configuration() -> None:
    neo4j = load_compose()["services"]["neo4j"]

    assert neo4j["image"]
    assert "environment" in neo4j
    assert "ports" in neo4j
    assert "volumes" in neo4j
    assert "healthcheck" in neo4j


def test_mlflow_service_is_profiled_and_exposes_server() -> None:
    mlflow = load_compose()["services"]["mlflow"]
    command = mlflow["command"]

    assert "mlflow" in mlflow["profiles"]
    assert any("5000" in port for port in mlflow["ports"])
    assert "mlflow server" in command


def test_required_named_volumes_exist() -> None:
    volumes = load_compose()["volumes"]

    assert {
        "postgres_data",
        "neo4j_data",
        "neo4j_logs",
        "neo4j_import",
        "neo4j_plugins",
        "mlflow_runs",
        "mlflow_artifacts",
    } <= set(volumes)


def test_project_network_exists() -> None:
    networks = load_compose()["networks"]

    assert "graph_aml_network" in networks
    assert networks["graph_aml_network"]["driver"] == "bridge"


def test_env_example_contains_required_variables() -> None:
    env_example = ENV_EXAMPLE.read_text(encoding="utf-8")

    for variable in (
        "PROJECT_ENV",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "MLFLOW_TRACKING_URI",
        "MLFLOW_PORT",
    ):
        assert f"{variable}=" in env_example
