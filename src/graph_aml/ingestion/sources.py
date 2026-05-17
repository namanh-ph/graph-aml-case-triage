"""Source resolution utilities for silver-layer parquet datasets."""

from __future__ import annotations

from pathlib import Path

DEFAULT_SILVER_DIR = "data/silver"

TABLE_NAMES: tuple[str, ...] = (
    "accounts",
    "counterparties",
    "countries",
    "customers",
    "devices",
    "scenario_manifest",
    "transactions",
)

CORE_TABLE_NAMES: tuple[str, ...] = (
    "accounts",
    "counterparties",
    "countries",
    "customers",
    "devices",
    "transactions",
)


def resolve_silver_paths(silver_dir: Path | str = DEFAULT_SILVER_DIR) -> dict[str, Path]:
    """Return parquet file paths for each known table in the silver layer.

    Validates that the silver directory exists and that every core table file
    is present. The optional ``scenario_manifest`` is included when found.
    """

    base = Path(silver_dir)
    if not base.is_dir():
        raise FileNotFoundError(f"Silver directory not found: {base}")

    paths: dict[str, Path] = {}
    for name in TABLE_NAMES:
        path = base / f"{name}.parquet"
        if name in CORE_TABLE_NAMES:
            if not path.is_file():
                raise FileNotFoundError(f"Silver table file not found: {path}")
            paths[name] = path
        else:
            if path.is_file():
                paths[name] = path
    return paths
