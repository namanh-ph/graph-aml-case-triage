"""Documentation completeness checks for release readiness."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from graph_aml.release.config import ReleaseReadinessConfig
from graph_aml.release.exceptions import DocumentationCheckError

DOCUMENTATION_CHECK_COLUMNS = (
    "release_run_id",
    "document_path",
    "check_name",
    "required_section",
    "status",
    "severity",
    "details",
    "metadata",
)


def _safe_path(item: str) -> Path:
    if not item or "\x00" in item:
        raise DocumentationCheckError("document path must be non-empty and safe")
    root = Path.cwd().resolve()
    path = Path(item)
    if path.is_absolute():
        raise DocumentationCheckError("document paths must be relative")
    resolved = (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise DocumentationCheckError("document path escapes repository root")
    return resolved


def _row(
    release_run_id: str | None,
    document_path: str,
    check_name: str,
    required_section: str | None,
    status: str,
    severity: str,
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "release_run_id": release_run_id or "",
        "document_path": document_path,
        "check_name": check_name,
        "required_section": required_section,
        "status": status,
        "severity": severity,
        "details": details,
        "metadata": {},
    }


def check_required_documents(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Check required documentation files exist."""

    resolved = config or ReleaseReadinessConfig()
    try:
        rows = []
        for item in sorted(resolved.documentation.required_docs):
            path = _safe_path(item)
            exists = path.is_file()
            rows.append(
                _row(
                    release_run_id,
                    item,
                    "required_document_exists",
                    None,
                    "pass" if exists else "fail",
                    "info" if exists else "high",
                    {"exists": exists},
                )
            )
        return pd.DataFrame(rows, columns=DOCUMENTATION_CHECK_COLUMNS)
    except DocumentationCheckError:
        raise
    except Exception as exc:
        raise DocumentationCheckError(f"required document check failed: {exc}") from exc


def check_document_sections(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Check required section strings appear in configured documents."""

    resolved = config or ReleaseReadinessConfig()
    try:
        rows = []
        for item, sections in sorted(resolved.documentation.required_sections.items()):
            path = _safe_path(item)
            text = (
                path.read_text(encoding="utf-8", errors="replace").lower()
                if path.exists()
                else ""
            )
            for section in sections:
                found = section.lower() in text
                rows.append(
                    _row(
                        release_run_id,
                        item,
                        "required_section_present",
                        section,
                        "pass" if found else "warning",
                        "info" if found else "medium",
                        {"found": found, "document_exists": path.exists()},
                    )
                )
        return pd.DataFrame(rows, columns=DOCUMENTATION_CHECK_COLUMNS)
    except DocumentationCheckError:
        raise
    except Exception as exc:
        raise DocumentationCheckError(f"document section check failed: {exc}") from exc


def run_documentation_checks(
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> pd.DataFrame:
    """Run all documentation checks."""

    return pd.concat(
        (
            check_required_documents(config, release_run_id),
            check_document_sections(config, release_run_id),
        ),
        ignore_index=True,
    )[list(DOCUMENTATION_CHECK_COLUMNS)]
