"""Validation artefact checks for release readiness."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from graph_aml.release.config import ReleaseReadinessConfig
from graph_aml.release.exceptions import ArtefactCheckError

ARTEFACT_CHECK_COLUMNS = (
    "release_run_id",
    "artefact_name",
    "relative_path",
    "artefact_type",
    "required",
    "status",
    "size_bytes",
    "modified_at",
    "details",
    "metadata",
)


def _report_root(config: ReleaseReadinessConfig) -> Path:
    root = Path(config.artefacts.report_dir)
    if root.is_absolute():
        raise ArtefactCheckError("report_dir must be relative")
    resolved = (Path.cwd().resolve() / root).resolve()
    cwd = Path.cwd().resolve()
    if resolved != cwd and cwd not in resolved.parents:
        raise ArtefactCheckError("report_dir escapes repository root")
    return resolved


def _safe_artefact_path(root: Path, relative_path: str) -> Path:
    if not relative_path or "\x00" in relative_path:
        raise ArtefactCheckError("artefact path must be non-empty and safe")
    path = Path(relative_path)
    if path.is_absolute():
        raise ArtefactCheckError("artefact paths must be relative")
    resolved = (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ArtefactCheckError("artefact path escapes report directory")
    return resolved


def classify_release_artefact(file_name: str) -> str:
    """Classify release artefact by filename."""

    name = file_name.lower()
    if "model_card" in name:
        return "model_card"
    if "governance" in name:
        return "governance"
    if "security" in name or "secret" in name or "permission" in name:
        return "security"
    if "monitoring" in name or "drift" in name:
        return "monitoring"
    if "comparison" in name or "champion" in name or "threshold" in name:
        return "model_validation"
    if "dataset" in name or "feature" in name:
        return "data_documentation"
    if name.endswith(".csv"):
        return "dataset_export"
    if name.endswith(".json"):
        return "metrics"
    if name.endswith(".md") or name.endswith(".txt"):
        return "documentation"
    return "other"


def _row(
    config: ReleaseReadinessConfig,
    root: Path,
    release_run_id: str | None,
    artefact_name: str,
    required: bool,
) -> dict[str, object]:
    path = _safe_artefact_path(root, artefact_name)
    exists = path.is_file()
    size = int(path.stat().st_size) if exists else None
    modified = pd.Timestamp(path.stat().st_mtime, unit="s").isoformat() if exists else None
    oversized = bool(size and size > config.artefacts.max_file_size_mb * 1024 * 1024)
    status = "pass" if exists and not oversized else "warning" if exists else "fail"
    if not required and not exists:
        status = "not_applicable"
    return {
        "release_run_id": release_run_id or "",
        "artefact_name": Path(artefact_name).name,
        "relative_path": artefact_name.replace("\\", "/"),
        "artefact_type": classify_release_artefact(artefact_name),
        "required": required,
        "status": status,
        "size_bytes": size,
        "modified_at": modified,
        "details": {"exists": exists, "oversized": oversized},
        "metadata": {},
    }


def check_required_release_artefacts(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Check required release artefacts exist."""

    resolved = config or ReleaseReadinessConfig()
    try:
        root = _report_root(resolved)
        if not root.exists():
            return pd.DataFrame(
                [
                    {
                        "release_run_id": release_run_id or "",
                        "artefact_name": item,
                        "relative_path": item,
                        "artefact_type": classify_release_artefact(item),
                        "required": True,
                        "status": "fail",
                        "size_bytes": None,
                        "modified_at": None,
                        "details": {"exists": False, "report_dir_exists": False},
                        "metadata": {},
                    }
                    for item in sorted(resolved.artefacts.required_files)
                ],
                columns=ARTEFACT_CHECK_COLUMNS,
            )
        return pd.DataFrame(
            [
                _row(resolved, root, release_run_id, item, True)
                for item in sorted(resolved.artefacts.required_files)
            ],
            columns=ARTEFACT_CHECK_COLUMNS,
        )
    except ArtefactCheckError:
        raise
    except Exception as exc:
        raise ArtefactCheckError(f"required artefact check failed: {exc}") from exc


def check_optional_release_artefacts(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Check optional release artefacts where configured."""

    resolved = config or ReleaseReadinessConfig()
    try:
        root = _report_root(resolved)
        if not root.exists():
            return pd.DataFrame(columns=ARTEFACT_CHECK_COLUMNS)
        return pd.DataFrame(
            [
                _row(resolved, root, release_run_id, item, False)
                for item in sorted(resolved.artefacts.optional_files)
            ],
            columns=ARTEFACT_CHECK_COLUMNS,
        )
    except ArtefactCheckError:
        raise
    except Exception as exc:
        raise ArtefactCheckError(f"optional artefact check failed: {exc}") from exc


def build_release_validation_index(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Build a deterministic validation artefact index."""

    resolved = config or ReleaseReadinessConfig()
    root = _report_root(resolved)
    frames = [check_required_release_artefacts(resolved, release_run_id)]
    if resolved.artefacts.optional_files:
        frames.append(check_optional_release_artefacts(resolved, release_run_id))
    if root.exists():
        configured = set(resolved.artefacts.required_files) | set(resolved.artefacts.optional_files)
        rows = []
        for path in sorted(root.rglob("*")):
            if (
                not path.is_file()
                or path.suffix.lower() not in resolved.artefacts.allowed_extensions
            ):
                continue
            relative = str(path.relative_to(root)).replace("\\", "/")
            if relative in configured:
                continue
            stat = path.stat()
            rows.append(
                {
                    "release_run_id": release_run_id or "",
                    "artefact_name": path.name,
                    "relative_path": relative,
                    "artefact_type": classify_release_artefact(path.name),
                    "required": False,
                    "status": "pass",
                    "size_bytes": int(stat.st_size),
                    "modified_at": pd.Timestamp(stat.st_mtime, unit="s").isoformat(),
                    "details": {"indexed": True},
                    "metadata": {},
                }
            )
        if rows:
            frames.append(pd.DataFrame(rows, columns=ARTEFACT_CHECK_COLUMNS))
    return pd.concat(frames, ignore_index=True)[list(ARTEFACT_CHECK_COLUMNS)]


def run_artefact_checks(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Run required and optional artefact checks."""

    return pd.concat(
        (
            check_required_release_artefacts(config, release_run_id),
            check_optional_release_artefacts(config, release_run_id),
        ),
        ignore_index=True,
    )[list(ARTEFACT_CHECK_COLUMNS)]
