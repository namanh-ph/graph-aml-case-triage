"""Local validation report artefact readers for dashboard pages."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine

from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.governance import (
    GovernanceInventoryPersistenceError,
    read_artefact_registry,
    read_governance_inventory_summary,
    read_inventory_runs,
    read_lineage_edges,
    read_lineage_nodes,
    read_model_inventory,
    read_process_inventory,
    read_validation_inventory,
)
from graph_aml.release import (
    ReleasePersistenceError,
    read_release_artefact_checks,
    read_release_evidence_index,
    read_release_portfolio_pack,
    read_release_readiness_runs,
    read_release_readiness_summary,
    read_release_repository_checks,
)
from graph_aml.security import (
    SecurityPersistenceError,
    read_audit_integrity_checks,
    read_permission_matrix,
    read_secrets_scan_findings,
    read_security_control_runs,
    read_security_control_summary,
    read_sensitive_field_inventory,
)


def _normalise_extensions(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    extensions = tuple(str(value).strip().lower() for value in values)
    if any(not value.startswith(".") for value in extensions):
        raise DashboardDataError("allowed extensions must start with '.'")
    return extensions


def _report_root(report_dir: Path | str) -> Path:
    return Path(report_dir).resolve()


def _resolve_report_path(file_path: Path | str, report_dir: Path | str) -> Path:
    root = _report_root(report_dir)
    candidate = Path(file_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise DashboardDataError("report path is outside the configured report directory")
    return resolved


def _category(path: Path) -> str:
    name = path.name.lower()
    if "case" in name:
        return "case"
    if "graph" in name:
        return "graph"
    if "risk" in name or "score" in name or "model" in name:
        return "model"
    if "audit" in name or "validation" in name:
        return "governance"
    return "general"


def list_validation_report_files(
    report_dir: Path | str = "reports/model_validation",
    allowed_extensions: tuple[str, ...] | list[str] = (".md", ".json", ".csv", ".txt"),
) -> pd.DataFrame:
    root = _report_root(report_dir)
    extensions = _normalise_extensions(allowed_extensions)
    if not root.exists():
        return pd.DataFrame(
            columns=(
                "file_name",
                "relative_path",
                "extension",
                "size_bytes",
                "modified_at",
                "category",
            )
        )
    if not root.is_dir():
        raise DashboardDataError("report_dir must be a directory")
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        stat = path.stat()
        rows.append(
            {
                "file_name": path.name,
                "relative_path": str(path.relative_to(root)).replace("\\", "/"),
                "extension": path.suffix.lower(),
                "size_bytes": int(stat.st_size),
                "modified_at": pd.Timestamp(stat.st_mtime, unit="s").isoformat(),
                "category": _category(path),
            }
        )
    return pd.DataFrame(rows)


def read_validation_report_file(
    file_path: Path | str,
    report_dir: Path | str = "reports/model_validation",
    max_preview_chars: int = 12000,
) -> dict[str, object]:
    if max_preview_chars <= 0:
        raise DashboardDataError("max_preview_chars must be positive")
    path = _resolve_report_path(file_path, report_dir)
    if not path.exists() or not path.is_file():
        raise DashboardDataError("report file does not exist")
    text = path.read_text(encoding="utf-8", errors="replace")
    preview_text = text[:max_preview_chars]
    payload: dict[str, object] = {
        "file_name": path.name,
        "relative_path": str(path.relative_to(_report_root(report_dir))).replace("\\", "/"),
        "extension": path.suffix.lower(),
        "size_bytes": int(path.stat().st_size),
        "truncated": len(text) > max_preview_chars,
        "preview_text": preview_text,
    }
    if path.suffix.lower() == ".json":
        try:
            payload["json"] = json.loads(text)
        except json.JSONDecodeError:
            payload["json"] = None
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
        payload["row_count"] = int(len(frame))
        payload["column_count"] = int(len(frame.columns))
        payload["sample_rows"] = frame.head(25).astype(object).to_dict("records")
    return payload


def build_validation_report_index(
    report_dir: Path | str = "reports/model_validation",
    allowed_extensions: tuple[str, ...] | list[str] = (".md", ".json", ".csv", ".txt"),
) -> dict[str, object]:
    files = list_validation_report_files(report_dir, allowed_extensions)
    categories = (
        files["category"].value_counts().sort_index().to_dict()
        if "category" in files.columns and not files.empty
        else {}
    )
    return {
        "report_dir": str(report_dir),
        "file_count": int(len(files)),
        "categories": {str(key): int(value) for key, value in categories.items()},
        "files": files.astype(object).to_dict("records"),
    }


def read_dashboard_governance_inventory_bundle(
    engine: Engine,
    limit: int = 25,
) -> dict[str, object]:
    """Read persisted governance inventory outputs for dashboard display."""

    if limit <= 0:
        raise DashboardDataError("limit must be positive")
    try:
        runs = read_inventory_runs(engine, limit=1)
        latest_run_id = (
            str(runs.iloc[0]["inventory_run_id"])
            if not runs.empty and "inventory_run_id" in runs.columns
            else None
        )
        return {
            "summary": read_governance_inventory_summary(engine),
            "inventory_runs": runs,
            "lineage_nodes": read_lineage_nodes(
                engine,
                inventory_run_id=latest_run_id,
                limit=limit,
            ),
            "lineage_edges": read_lineage_edges(
                engine,
                inventory_run_id=latest_run_id,
                limit=limit,
            ),
            "artefact_registry": read_artefact_registry(
                engine,
                inventory_run_id=latest_run_id,
                limit=limit,
            ),
            "process_inventory": read_process_inventory(
                engine,
                inventory_run_id=latest_run_id,
                limit=limit,
            ),
            "model_inventory": read_model_inventory(
                engine,
                inventory_run_id=latest_run_id,
                limit=limit,
            ),
            "validation_inventory": read_validation_inventory(
                engine,
                inventory_run_id=latest_run_id,
                limit=limit,
            ),
        }
    except GovernanceInventoryPersistenceError as exc:
        raise DashboardDataError(f"governance inventory outputs are unavailable: {exc}") from exc


def read_dashboard_security_control_bundle(
    engine: Engine,
    limit: int = 25,
) -> dict[str, object]:
    """Read persisted security control outputs for dashboard display."""

    if limit <= 0:
        raise DashboardDataError("limit must be positive")
    try:
        runs = read_security_control_runs(engine, limit=1)
        latest_run_id = (
            str(runs.iloc[0]["security_run_id"])
            if not runs.empty and "security_run_id" in runs.columns
            else None
        )
        return {
            "summary": read_security_control_summary(engine),
            "security_runs": runs,
            "sensitive_fields": read_sensitive_field_inventory(
                engine,
                security_run_id=latest_run_id,
                limit=limit,
            ),
            "permission_matrix": read_permission_matrix(
                engine,
                security_run_id=latest_run_id,
                limit=limit,
            ),
            "secrets_scan": read_secrets_scan_findings(
                engine,
                security_run_id=latest_run_id,
                limit=limit,
            ),
            "audit_integrity": read_audit_integrity_checks(
                engine,
                security_run_id=latest_run_id,
                limit=limit,
            ),
        }
    except SecurityPersistenceError as exc:
        raise DashboardDataError(f"security control outputs are unavailable: {exc}") from exc


def read_dashboard_release_readiness_bundle(
    engine: Engine,
    limit: int = 25,
) -> dict[str, object]:
    """Read persisted release readiness outputs for dashboard display."""

    if limit <= 0:
        raise DashboardDataError("limit must be positive")
    try:
        runs = read_release_readiness_runs(engine, limit=1)
        latest_run_id = (
            str(runs.iloc[0]["release_run_id"])
            if not runs.empty and "release_run_id" in runs.columns
            else None
        )
        return {
            "summary": read_release_readiness_summary(engine),
            "release_runs": runs,
            "repository_checks": read_release_repository_checks(
                engine,
                release_run_id=latest_run_id,
                limit=limit,
            ),
            "artefact_checks": read_release_artefact_checks(
                engine,
                release_run_id=latest_run_id,
                limit=limit,
            ),
            "evidence_index": read_release_evidence_index(
                engine,
                release_run_id=latest_run_id,
                limit=limit,
            ),
            "portfolio_pack": read_release_portfolio_pack(
                engine,
                release_run_id=latest_run_id,
                limit=limit,
            ),
        }
    except ReleasePersistenceError as exc:
        raise DashboardDataError(f"release readiness outputs are unavailable: {exc}") from exc
