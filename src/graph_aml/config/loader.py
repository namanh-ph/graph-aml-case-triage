"""YAML loading helpers for typed application configuration."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from yaml import YAMLError

from graph_aml.config.exceptions import ConfigFileNotFoundError, ConfigValidationError
from graph_aml.config.schemas import AppConfig

CONFIG_FILE_MAP: dict[str, str] = {
    "project": "project.yaml",
    "paths": "paths.yaml",
    "database": "database.yaml",
    "neo4j": "neo4j.yaml",
    "rules": "rules.yaml",
    "scoring": "scoring.yaml",
    "model": "model.yaml",
    "dashboard": "dashboard.yaml",
}


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load one YAML file and ensure the YAML root is a mapping."""

    if not path.is_file():
        raise ConfigFileNotFoundError(f"Configuration file not found: {path}")

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise ConfigValidationError(f"Failed to parse YAML file {path}: {exc}") from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigValidationError(f"Configuration file root must be a dictionary: {path}")
    return loaded


def load_config_dict(config_dir: Path | str = "config") -> dict[str, Any]:
    """Load all required YAML files into the aggregate AppConfig input shape."""

    config_path = Path(config_dir)
    return {
        aggregate_key: load_yaml_file(config_path / filename)
        for aggregate_key, filename in CONFIG_FILE_MAP.items()
    }


def load_app_config(config_dir: Path | str = "config") -> AppConfig:
    """Load and validate all application configuration files."""

    config_dict = load_config_dict(config_dir)
    try:
        return AppConfig.model_validate(config_dict)
    except ValidationError as exc:
        raise ConfigValidationError(f"Configuration validation failed: {exc}") from exc
