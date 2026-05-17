"""Environment-backed settings helpers for typed configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from graph_aml.config.exceptions import EnvironmentVariableError
from graph_aml.config.schemas import AppConfig

# Load the project-level .env file at import time so every script that touches
# environment-backed settings (DB connection, Neo4j auth, MLflow tracking URI,
# etc.) sees the same values. ``override=False`` keeps real shell env vars in
# priority over file-based defaults.
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
if _ENV_FILE.is_file():
    load_dotenv(_ENV_FILE, override=False)


class EnvironmentSettings(BaseSettings):
    """Minimal settings model used to read process environment values."""

    model_config = SettingsConfigDict(extra="ignore")

    def get_value(
        self,
        name: str,
        default: str | int | None = None,
        required: bool = False,
    ) -> str | int | None:
        """Resolve one environment variable with optional default and required handling."""

        value = os.environ.get(name)
        if value is not None:
            return value
        if default is not None:
            return default
        if required:
            raise EnvironmentVariableError(f"Required environment variable is missing: {name}")
        return None


def get_env_value(
    name: str,
    default: str | int | None = None,
    required: bool = False,
) -> str | int | None:
    """Return an environment variable value, a default, or raise when required."""

    return EnvironmentSettings().get_value(name=name, default=default, required=required)


def build_postgres_dsn(config: AppConfig) -> str:
    """Build a SQLAlchemy PostgreSQL DSN without opening a database connection."""

    postgres = config.database.postgres
    defaults = postgres.defaults

    host = get_env_value(postgres.host_env, defaults.host)
    port = get_env_value(postgres.port_env, defaults.port)
    database = get_env_value(postgres.database_env, defaults.database)
    user = get_env_value(postgres.user_env, defaults.user)
    password = get_env_value(postgres.password_env, "change_me")

    return f"{postgres.driver}://{user}:{password}@{host}:{port}/{database}"


def build_neo4j_settings(config: AppConfig) -> dict[str, str]:
    """Build Neo4j connection settings without opening a graph connection."""

    neo4j = config.neo4j.neo4j
    defaults = neo4j.defaults

    return {
        "uri": str(get_env_value(neo4j.uri_env, defaults.uri)),
        "user": str(get_env_value(neo4j.user_env, defaults.user)),
        "password": str(get_env_value(neo4j.password_env, "change_me")),
        "database": defaults.database,
    }


def get_mlflow_tracking_uri(default: str = "mlruns") -> str:
    """Return the MLflow tracking URI from the environment or a local default."""

    return str(get_env_value("MLFLOW_TRACKING_URI", default))
