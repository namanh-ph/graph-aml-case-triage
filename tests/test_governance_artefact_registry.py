"""Tests for governance artefact registry helpers."""

from pathlib import Path

import pytest

from graph_aml.governance import (
    ARTEFACT_REGISTRY_COLUMNS,
    ArtefactRegistryError,
    GovernanceArtefactConfig,
    GovernanceInventoryConfig,
    build_artefact_registry,
    classify_artefact_type,
    hash_artefact_file,
    safe_relative_artefact_path,
)


def test_safe_relative_paths_and_traversal_rejection(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    file_path = root / "a.md"
    file_path.write_text("x", encoding="utf-8")
    assert safe_relative_artefact_path(file_path, root) == "a.md"
    with pytest.raises(ArtefactRegistryError):
        safe_relative_artefact_path(tmp_path / "outside.md", root)


def test_file_hashing_is_deterministic(tmp_path: Path) -> None:
    file_path = tmp_path / "metrics.json"
    file_path.write_text('{"a": 1}', encoding="utf-8")
    assert hash_artefact_file(file_path) == hash_artefact_file(file_path)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("model_card.md", "model_card"),
        ("metrics.json", "metrics"),
        ("scores.csv", "dataset_export"),
        ("config.yaml", "config"),
        ("note.bin", "other"),
    ],
)
def test_artefact_type_classification(name: str, expected: str) -> None:
    assert classify_artefact_type(Path(name)) == expected


def test_registry_scans_roots_filters_extensions_and_size(tmp_path: Path) -> None:
    root = tmp_path / "reports"
    root.mkdir()
    (root / "a.md").write_text("a", encoding="utf-8")
    (root / "b.exe").write_text("b", encoding="utf-8")
    (root / "large.csv").write_text("x" * 20, encoding="utf-8")
    config = GovernanceInventoryConfig(
        artefacts=GovernanceArtefactConfig(
            root_dirs=(str(root),),
            allowed_extensions=(".md", ".csv"),
            max_file_size_mb=1,
        )
    )
    registry = build_artefact_registry(config, "run1")
    assert tuple(registry.columns) == ARTEFACT_REGISTRY_COLUMNS
    assert set(registry["file_name"]) == {"a.md", "large.csv"}


def test_registry_missing_directory_returns_empty(tmp_path: Path) -> None:
    config = GovernanceInventoryConfig(
        artefacts=GovernanceArtefactConfig(root_dirs=(str(tmp_path / "missing"),))
    )
    assert build_artefact_registry(config, "run1").empty
