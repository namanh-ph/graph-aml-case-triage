"""Local readiness checks for the portfolio demo."""

from __future__ import annotations

import importlib
from pathlib import Path

from graph_aml.demo.config import DemoOrchestrationConfig, validate_demo_orchestration_config
from graph_aml.demo.exceptions import DemoValidationError

DEFAULT_REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "pyproject.toml",
    "docker-compose.yml",
    "config/database.yaml",
    "config/graph.yaml",
    "config/model.yaml",
    "config/scoring.yaml",
    "config/dashboard.yaml",
    "config/demo.yaml",
)

DEFAULT_REQUIRED_DIRECTORIES: tuple[str, ...] = (
    "src/graph_aml",
    "scripts",
    "app",
    "app/pages",
    "tests",
    "reports/model_validation",
)

DEFAULT_REQUIRED_PACKAGES: tuple[str, ...] = (
    "pandas",
    "sqlalchemy",
    "sklearn",
    "networkx",
    "streamlit",
    "plotly",
)


def _normalise_paths(
    values: tuple[str, ...] | list[str] | None,
    defaults: tuple[str, ...],
) -> tuple[str, ...]:
    raw_values = defaults if values is None else tuple(values)
    normalised = tuple(str(value).strip() for value in raw_values)
    if any(not value for value in normalised):
        raise DemoValidationError("readiness paths must be non-empty")
    return normalised


def check_required_files_exist(
    paths: tuple[str, ...] | list[str] | None = None,
) -> dict[str, object]:
    """Check required local files without connecting to services."""

    values = _normalise_paths(paths, DEFAULT_REQUIRED_FILES)
    rows = [
        {"path": value, "exists": Path(value).is_file()}
        for value in values
    ]
    missing = [row["path"] for row in rows if not row["exists"]]
    return {
        "status": "ok" if not missing else "warning",
        "checked_count": len(rows),
        "missing_count": len(missing),
        "missing": missing,
        "files": rows,
    }


def check_required_directories_exist(
    paths: tuple[str, ...] | list[str] | None = None,
) -> dict[str, object]:
    """Check required local directories without connecting to services."""

    values = _normalise_paths(paths, DEFAULT_REQUIRED_DIRECTORIES)
    rows = [
        {"path": value, "exists": Path(value).is_dir()}
        for value in values
    ]
    missing = [row["path"] for row in rows if not row["exists"]]
    return {
        "status": "ok" if not missing else "warning",
        "checked_count": len(rows),
        "missing_count": len(missing),
        "missing": missing,
        "directories": rows,
    }


def check_python_package_imports(
    package_names: tuple[str, ...] | list[str] | None = None,
) -> dict[str, object]:
    """Check local Python imports without touching external services."""

    values = _normalise_paths(package_names, DEFAULT_REQUIRED_PACKAGES)
    rows: list[dict[str, object]] = []
    for package_name in values:
        try:
            importlib.import_module(package_name)
            rows.append({"package": package_name, "importable": True, "error": None})
        except Exception as exc:
            rows.append({"package": package_name, "importable": False, "error": str(exc)})
    missing = [row["package"] for row in rows if not row["importable"]]
    return {
        "status": "ok" if not missing else "warning",
        "checked_count": len(rows),
        "missing_count": len(missing),
        "missing": missing,
        "packages": rows,
    }


def build_demo_readiness_summary(
    config: DemoOrchestrationConfig | None = None,
) -> dict[str, object]:
    """Build a local readiness summary for demo preparation."""

    resolved = config or DemoOrchestrationConfig()
    validate_demo_orchestration_config(resolved)
    files = check_required_files_exist()
    directories = check_required_directories_exist()
    packages = check_python_package_imports()
    statuses = (files["status"], directories["status"], packages["status"])
    return {
        "demo_name": resolved.demo.name,
        "demo_version": resolved.demo.version,
        "status": "ok" if all(status == "ok" for status in statuses) else "warning",
        "files": files,
        "directories": directories,
        "packages": packages,
    }
