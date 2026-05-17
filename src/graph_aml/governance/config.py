"""Configuration for governance inventory and lineage builds."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from graph_aml.governance.exceptions import GovernanceInventoryConfigurationError


@dataclass(frozen=True)
class GovernanceInventoryIncludeConfig:
    database_tables: bool = True
    audit_events: bool = True
    model_runs: bool = True
    supervised_model_runs: bool = True
    model_comparison_runs: bool = True
    monitoring_runs: bool = True
    explainability_runs: bool = True
    dashboard_artefacts: bool = True
    validation_artefacts: bool = True
    documentation_files: bool = True


@dataclass(frozen=True)
class GovernanceLineageConfig:
    include_table_lineage: bool = True
    include_process_lineage: bool = True
    include_run_dependencies: bool = True
    include_column_level_notes: bool = False
    max_dependency_depth: int = 5


@dataclass(frozen=True)
class GovernanceArtefactConfig:
    root_dirs: tuple[str, ...] = ("reports/model_validation", "docs")
    allowed_extensions: tuple[str, ...] = (".md", ".json", ".csv", ".txt", ".yaml", ".yml")
    max_file_size_mb: int = 25
    hash_algorithm: str = "sha256"


@dataclass(frozen=True)
class GovernancePersistenceConfig:
    write_database: bool = True
    write_artefacts: bool = True
    write_audit: bool = True
    artefact_output_dir: str = "reports/model_validation"


@dataclass(frozen=True)
class GovernanceInventoryConfig:
    inventory_name: str = "aml_governance_inventory"
    inventory_version: str = "governance_inventory_v1"
    include: GovernanceInventoryIncludeConfig = field(
        default_factory=GovernanceInventoryIncludeConfig
    )
    lineage: GovernanceLineageConfig = field(default_factory=GovernanceLineageConfig)
    artefacts: GovernanceArtefactConfig = field(default_factory=GovernanceArtefactConfig)
    known_processes: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)
    persistence: GovernancePersistenceConfig = field(default_factory=GovernancePersistenceConfig)


def _bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise GovernanceInventoryConfigurationError(f"{name} must be boolean")
    return value


def _int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GovernanceInventoryConfigurationError(f"{name} must be an integer")
    return int(value)


def _tuple_strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise GovernanceInventoryConfigurationError(f"{name} must be a list")
    values = tuple(str(item).strip() for item in value)
    if not values or any(not item for item in values):
        raise GovernanceInventoryConfigurationError(f"{name} must contain non-empty strings")
    return values


def _normalise_processes(raw: object) -> dict[str, dict[str, tuple[str, ...]]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise GovernanceInventoryConfigurationError("known_processes must be a mapping")
    processes: dict[str, dict[str, tuple[str, ...]]] = {}
    for name, payload in raw.items():
        process_name = str(name).strip()
        if not process_name:
            raise GovernanceInventoryConfigurationError("known process names must be non-empty")
        if not isinstance(payload, dict):
            raise GovernanceInventoryConfigurationError("known process config must be a mapping")
        inputs = _tuple_strings(payload.get("inputs", ()), f"{process_name}.inputs")
        outputs = _tuple_strings(payload.get("outputs", ()), f"{process_name}.outputs")
        processes[process_name] = {"inputs": inputs, "outputs": outputs}
    return processes


def validate_governance_inventory_config(config: GovernanceInventoryConfig) -> None:
    """Validate governance inventory configuration without service access."""

    if not config.inventory_name.strip():
        raise GovernanceInventoryConfigurationError("inventory_name must be non-empty")
    if not config.inventory_version.strip():
        raise GovernanceInventoryConfigurationError("inventory_version must be non-empty")
    for field_name, value in vars(config.include).items():
        _bool(value, f"include.{field_name}")
    for field_name, value in vars(config.lineage).items():
        if field_name == "max_dependency_depth":
            if _int(value, f"lineage.{field_name}") <= 0:
                raise GovernanceInventoryConfigurationError("max_dependency_depth must be positive")
        else:
            _bool(value, f"lineage.{field_name}")
    roots = _tuple_strings(config.artefacts.root_dirs, "artefacts.root_dirs")
    if len(roots) != len(set(roots)):
        raise GovernanceInventoryConfigurationError("artefact root directories must be unique")
    extensions = tuple(ext.lower() for ext in config.artefacts.allowed_extensions)
    if (
        not extensions
        or len(extensions) != len(set(extensions))
        or any(not ext.startswith(".") or ext == "." for ext in extensions)
    ):
        raise GovernanceInventoryConfigurationError(
            "allowed extensions must be unique strings starting with '.'"
        )
    if config.artefacts.max_file_size_mb <= 0:
        raise GovernanceInventoryConfigurationError("max_file_size_mb must be positive")
    if config.artefacts.hash_algorithm not in {"sha256", "md5"}:
        raise GovernanceInventoryConfigurationError("hash_algorithm must be sha256 or md5")
    _normalise_processes(config.known_processes)
    for field_name, value in vars(config.persistence).items():
        if field_name == "artefact_output_dir":
            if not str(value).strip():
                raise GovernanceInventoryConfigurationError("artefact_output_dir must be non-empty")
        else:
            _bool(value, f"persistence.{field_name}")


def governance_inventory_config_from_mapping(
    payload: dict[str, object] | None,
) -> GovernanceInventoryConfig:
    """Build governance inventory configuration from a mapping."""

    data = payload or {}
    if "governance_inventory" in data and isinstance(data["governance_inventory"], dict):
        data = cast("dict[str, object]", data["governance_inventory"])
    default = GovernanceInventoryConfig()
    include_raw = (
        cast("dict[str, object]", data.get("include", {}))
        if isinstance(data.get("include"), dict)
        else {}
    )
    lineage_raw = (
        cast("dict[str, object]", data.get("lineage", {}))
        if isinstance(data.get("lineage"), dict)
        else {}
    )
    artefacts_raw = (
        cast("dict[str, object]", data.get("artefacts", {}))
        if isinstance(data.get("artefacts"), dict)
        else {}
    )
    persistence_raw = (
        cast("dict[str, object]", data.get("persistence", {}))
        if isinstance(data.get("persistence"), dict)
        else {}
    )
    config = GovernanceInventoryConfig(
        inventory_name=str(data.get("inventory_name", default.inventory_name)),
        inventory_version=str(data.get("inventory_version", default.inventory_version)),
        include=GovernanceInventoryIncludeConfig(
            **{
                field_name: _bool(include_raw.get(field_name, value), f"include.{field_name}")
                for field_name, value in vars(default.include).items()
            }
        ),
        lineage=GovernanceLineageConfig(
            include_table_lineage=_bool(
                lineage_raw.get("include_table_lineage", default.lineage.include_table_lineage),
                "lineage.include_table_lineage",
            ),
            include_process_lineage=_bool(
                lineage_raw.get("include_process_lineage", default.lineage.include_process_lineage),
                "lineage.include_process_lineage",
            ),
            include_run_dependencies=_bool(
                lineage_raw.get(
                    "include_run_dependencies",
                    default.lineage.include_run_dependencies,
                ),
                "lineage.include_run_dependencies",
            ),
            include_column_level_notes=_bool(
                lineage_raw.get(
                    "include_column_level_notes",
                    default.lineage.include_column_level_notes,
                ),
                "lineage.include_column_level_notes",
            ),
            max_dependency_depth=_int(
                lineage_raw.get("max_dependency_depth", default.lineage.max_dependency_depth),
                "lineage.max_dependency_depth",
            ),
        ),
        artefacts=GovernanceArtefactConfig(
            root_dirs=_tuple_strings(
                artefacts_raw.get("root_dirs", default.artefacts.root_dirs),
                "artefacts.root_dirs",
            ),
            allowed_extensions=tuple(
                ext.lower()
                for ext in _tuple_strings(
                    artefacts_raw.get("allowed_extensions", default.artefacts.allowed_extensions),
                    "artefacts.allowed_extensions",
                )
            ),
            max_file_size_mb=_int(
                artefacts_raw.get("max_file_size_mb", default.artefacts.max_file_size_mb),
                "artefacts.max_file_size_mb",
            ),
            hash_algorithm=str(
                artefacts_raw.get("hash_algorithm", default.artefacts.hash_algorithm)
            ).strip(),
        ),
        known_processes=_normalise_processes(data.get("known_processes", default.known_processes)),
        persistence=GovernancePersistenceConfig(
            write_database=_bool(
                persistence_raw.get("write_database", default.persistence.write_database),
                "persistence.write_database",
            ),
            write_artefacts=_bool(
                persistence_raw.get("write_artefacts", default.persistence.write_artefacts),
                "persistence.write_artefacts",
            ),
            write_audit=_bool(
                persistence_raw.get("write_audit", default.persistence.write_audit),
                "persistence.write_audit",
            ),
            artefact_output_dir=str(
                persistence_raw.get("artefact_output_dir", default.persistence.artefact_output_dir)
            ),
        ),
    )
    validate_governance_inventory_config(config)
    return config


def load_governance_inventory_config(
    config_path: Path | str = "config/governance.yaml",
) -> GovernanceInventoryConfig:
    """Load governance inventory configuration from YAML."""

    path = Path(config_path)
    if not path.exists():
        return GovernanceInventoryConfig()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise GovernanceInventoryConfigurationError("governance config must be a mapping")
    return governance_inventory_config_from_mapping(cast("dict[str, Any]", payload))
