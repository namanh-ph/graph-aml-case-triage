"""Repository hygiene checks for release readiness."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from graph_aml.release.config import ReleaseReadinessConfig
from graph_aml.release.exceptions import RepositoryCheckError

REPOSITORY_CHECK_COLUMNS = (
    "release_run_id",
    "check_name",
    "item_type",
    "item_name",
    "status",
    "severity",
    "details",
    "metadata",
)


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=REPOSITORY_CHECK_COLUMNS)


def _repo_root() -> Path:
    return Path.cwd().resolve()


def _safe_path(item: str) -> Path:
    if not item or "\x00" in item:
        raise RepositoryCheckError("repository check path must be non-empty and safe")
    root = _repo_root()
    path = Path(item)
    if path.is_absolute():
        raise RepositoryCheckError("repository check paths must be relative")
    resolved = (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise RepositoryCheckError("repository check path escapes repository root")
    return resolved


def _row(
    release_run_id: str | None,
    check_name: str,
    item_type: str,
    item_name: str,
    status: str,
    severity: str,
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "release_run_id": release_run_id or "",
        "check_name": check_name,
        "item_type": item_type,
        "item_name": item_name,
        "status": status,
        "severity": severity,
        "details": details,
        "metadata": {},
    }


def check_required_files(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Check configured required files exist."""

    resolved = config or ReleaseReadinessConfig()
    try:
        rows = []
        for item in sorted(resolved.repository.required_files):
            path = _safe_path(item)
            exists = path.is_file()
            rows.append(
                _row(
                    release_run_id,
                    "required_file_exists",
                    "file",
                    item,
                    "pass" if exists else "fail",
                    "info" if exists else "high",
                    {"exists": exists},
                )
            )
        return pd.DataFrame(rows, columns=REPOSITORY_CHECK_COLUMNS)
    except RepositoryCheckError:
        raise
    except Exception as exc:
        raise RepositoryCheckError(f"required file check failed: {exc}") from exc


def check_required_directories(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Check configured required directories exist."""

    resolved = config or ReleaseReadinessConfig()
    try:
        rows = []
        for item in sorted(resolved.repository.required_directories):
            path = _safe_path(item)
            exists = path.is_dir()
            rows.append(
                _row(
                    release_run_id,
                    "required_directory_exists",
                    "directory",
                    item,
                    "pass" if exists else "fail",
                    "info" if exists else "high",
                    {"exists": exists},
                )
            )
        return pd.DataFrame(rows, columns=REPOSITORY_CHECK_COLUMNS)
    except RepositoryCheckError:
        raise
    except Exception as exc:
        raise RepositoryCheckError(f"required directory check failed: {exc}") from exc


def check_forbidden_paths_absent(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Check configured forbidden local paths are absent."""

    resolved = config or ReleaseReadinessConfig()
    try:
        rows = []
        for item in sorted(resolved.repository.forbidden_paths):
            path = _safe_path(item)
            exists = path.exists()
            rows.append(
                _row(
                    release_run_id,
                    "forbidden_path_absent",
                    "path",
                    item,
                    "fail" if exists else "pass",
                    "high" if exists else "info",
                    {"exists": exists},
                )
            )
        return pd.DataFrame(rows, columns=REPOSITORY_CHECK_COLUMNS)
    except RepositoryCheckError:
        raise
    except Exception as exc:
        raise RepositoryCheckError(f"forbidden path check failed: {exc}") from exc


def _make_targets(makefile_text: str) -> set[str]:
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)\s*:", re.MULTILINE)
    return set(pattern.findall(makefile_text))


def check_makefile_targets(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Check configured Makefile targets are present."""

    resolved = config or ReleaseReadinessConfig()
    try:
        makefile = _safe_path("Makefile")
        text = makefile.read_text(encoding="utf-8") if makefile.exists() else ""
        targets = _make_targets(text)
        rows = []
        for item in sorted(resolved.repository.required_make_targets):
            exists = item in targets
            rows.append(
                _row(
                    release_run_id,
                    "makefile_target_exists",
                    "make_target",
                    item,
                    "pass" if exists else "fail",
                    "info" if exists else "medium",
                    {"exists": exists},
                )
            )
        return pd.DataFrame(rows, columns=REPOSITORY_CHECK_COLUMNS)
    except RepositoryCheckError:
        raise
    except Exception as exc:
        raise RepositoryCheckError(f"Makefile target check failed: {exc}") from exc


def run_repository_checks(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Run all repository checks."""

    frames = (
        check_required_files(config, release_run_id),
        check_required_directories(config, release_run_id),
        check_forbidden_paths_absent(config, release_run_id),
        check_makefile_targets(config, release_run_id),
    )
    if not frames:
        return _empty()
    return pd.concat(frames, ignore_index=True)[list(REPOSITORY_CHECK_COLUMNS)]
