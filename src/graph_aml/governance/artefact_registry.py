"""Local artefact registry builder for governance inventory."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from graph_aml.governance.config import GovernanceInventoryConfig
from graph_aml.governance.exceptions import ArtefactRegistryError

ARTEFACT_REGISTRY_COLUMNS = (
    "inventory_run_id",
    "artefact_id",
    "artefact_type",
    "file_name",
    "relative_path",
    "extension",
    "size_bytes",
    "hash_value",
    "modified_at",
    "source_dir",
    "metadata",
)


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=ARTEFACT_REGISTRY_COLUMNS)


def safe_relative_artefact_path(
    path: Path,
    root_dir: Path,
) -> str:
    """Return a safe POSIX relative path for a file under root_dir."""

    try:
        resolved_root = root_dir.resolve()
        resolved_path = path.resolve()
        relative = resolved_path.relative_to(resolved_root)
        return str(relative).replace("\\", "/")
    except Exception as exc:
        raise ArtefactRegistryError("artefact path is outside configured root directory") from exc


def hash_artefact_file(
    path: Path,
    algorithm: str = "sha256",
) -> str:
    """Hash a local artefact deterministically."""

    if algorithm not in {"sha256", "md5"}:
        raise ArtefactRegistryError("unsupported hash algorithm")
    try:
        digest = hashlib.new(algorithm)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception as exc:
        raise ArtefactRegistryError(f"failed to hash artefact {path}: {exc}") from exc


def classify_artefact_type(path: Path) -> str:
    """Classify artefact by path and extension."""

    name = path.name.lower()
    suffix = path.suffix.lower()
    if "model_card" in name or "model-card" in name or "consolidated_model_card" in name:
        return "model_card"
    if "metric" in name or "summary" in name:
        return "metrics"
    if "validation" in name or "monitoring" in name or "comparison" in name:
        return "validation_report"
    if suffix in {".csv", ".json"} and ("dataset" in name or "scores" in name):
        return "dataset_export"
    if suffix in {".yaml", ".yml"}:
        return "config"
    if suffix == ".md" or "docs" in [part.lower() for part in path.parts]:
        return "documentation"
    return "other"


def _artefact_id(relative_path: str, hash_value: str) -> str:
    return hashlib.sha256(f"{relative_path}|{hash_value}".encode()).hexdigest()[:24]


def build_artefact_registry(
    config: GovernanceInventoryConfig | None = None,
    inventory_run_id: str | None = None,
) -> pd.DataFrame:
    """Scan configured local roots and build an artefact registry."""

    resolved = config or GovernanceInventoryConfig()
    run_id = inventory_run_id or resolved.inventory_version
    max_bytes = resolved.artefacts.max_file_size_mb * 1024 * 1024
    extensions = {ext.lower() for ext in resolved.artefacts.allowed_extensions}
    rows: list[dict[str, object]] = []
    try:
        for root_raw in resolved.artefacts.root_dirs:
            root = Path(root_raw).resolve()
            if not root.exists():
                continue
            if not root.is_dir():
                raise ArtefactRegistryError(f"artefact root is not a directory: {root_raw}")
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in extensions:
                    continue
                stat = path.stat()
                if stat.st_size > max_bytes:
                    continue
                relative_path = safe_relative_artefact_path(path, root)
                hash_value = hash_artefact_file(path, resolved.artefacts.hash_algorithm)
                rows.append(
                    {
                        "inventory_run_id": run_id,
                        "artefact_id": _artefact_id(f"{root_raw}/{relative_path}", hash_value),
                        "artefact_type": classify_artefact_type(path),
                        "file_name": path.name,
                        "relative_path": relative_path,
                        "extension": path.suffix.lower(),
                        "size_bytes": int(stat.st_size),
                        "hash_value": hash_value,
                        "modified_at": pd.Timestamp(stat.st_mtime, unit="s").isoformat(),
                        "source_dir": root_raw,
                        "metadata": {"hash_algorithm": resolved.artefacts.hash_algorithm},
                    }
                )
        if not rows:
            return _empty()
        return (
            pd.DataFrame(rows, columns=ARTEFACT_REGISTRY_COLUMNS)
            .drop_duplicates("artefact_id")
            .sort_values(["source_dir", "relative_path"])
            .reset_index(drop=True)
        )
    except ArtefactRegistryError:
        raise
    except Exception as exc:
        raise ArtefactRegistryError(f"failed to build artefact registry: {exc}") from exc
