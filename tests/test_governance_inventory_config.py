"""Tests for governance inventory configuration."""

from pathlib import Path

import pytest
import yaml

from graph_aml.governance import (
    GovernanceArtefactConfig,
    GovernanceInventoryConfig,
    GovernanceInventoryConfigurationError,
    GovernanceInventoryIncludeConfig,
    GovernanceLineageConfig,
    GovernancePersistenceConfig,
    governance_inventory_config_from_mapping,
    load_governance_inventory_config,
    validate_governance_inventory_config,
)


def test_default_governance_inventory_config_is_valid() -> None:
    validate_governance_inventory_config(GovernanceInventoryConfig())


@pytest.mark.parametrize(
    "config",
    [
        GovernanceInventoryConfig(inventory_name=""),
        GovernanceInventoryConfig(inventory_version=""),
        GovernanceInventoryConfig(include=GovernanceInventoryIncludeConfig(database_tables="yes")),  # type: ignore[arg-type]
        GovernanceInventoryConfig(lineage=GovernanceLineageConfig(max_dependency_depth=0)),
        GovernanceInventoryConfig(artefacts=GovernanceArtefactConfig(allowed_extensions=("csv",))),
        GovernanceInventoryConfig(known_processes={"": {"inputs": ("a",), "outputs": ("b",)}}),
        GovernanceInventoryConfig(persistence=GovernancePersistenceConfig(write_database="yes")),  # type: ignore[arg-type]
    ],
)
def test_invalid_governance_inventory_config_raises(config: GovernanceInventoryConfig) -> None:
    with pytest.raises(GovernanceInventoryConfigurationError):
        validate_governance_inventory_config(config)


def test_governance_inventory_config_can_be_built_from_mapping() -> None:
    config = governance_inventory_config_from_mapping(
        {
            "inventory_version": "v2",
            "known_processes": {"p": {"inputs": ["a"], "outputs": ["b"]}},
        }
    )
    assert config.inventory_version == "v2"
    assert config.known_processes["p"]["inputs"] == ("a",)


def test_governance_inventory_config_can_be_loaded_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "governance.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "governance_inventory": {
                    "inventory_name": "test_inventory",
                    "known_processes": {"p": {"inputs": ["a"], "outputs": ["b"]}},
                }
            }
        ),
        encoding="utf-8",
    )
    assert load_governance_inventory_config(path).inventory_name == "test_inventory"


def test_governance_config_loading_does_not_connect_to_postgresql(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(*_: object, **__: object) -> None:
        raise AssertionError("database access is not allowed")

    monkeypatch.setattr("pandas.read_sql_query", fail)
    path = tmp_path / "governance.yaml"
    path.write_text("governance_inventory: {}\n", encoding="utf-8")
    validate_governance_inventory_config(load_governance_inventory_config(path))
