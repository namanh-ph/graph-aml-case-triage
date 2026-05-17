"""Demo evidence pack builders for release readiness."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from graph_aml.release.config import ReleaseReadinessConfig
from graph_aml.release.exceptions import DemoEvidenceError

DEMO_EVIDENCE_COLUMNS = (
    "release_run_id",
    "evidence_name",
    "evidence_type",
    "relative_path",
    "status",
    "details",
    "metadata",
)


def build_command_transcript_template(
    config: ReleaseReadinessConfig | None = None,
) -> str:
    """Return a reviewer command transcript template without executing commands."""

    _ = config or ReleaseReadinessConfig()
    commands = [
        "cp .env.example .env",
        "make services-up",
        "make demo-run",
        "make labels-build-persist",
        "make model-supervised-train-persist",
        "make model-comparison-run-persist",
        "make monitoring-run-persist",
        "make explainability-run-persist",
        "make governance-inventory-run-persist",
        "make security-controls-run-persist",
        "make release-readiness-run-persist",
        "make release-readiness-summary",
        "make services-down",
    ]
    return "\n".join(
        [
            "# Command Transcript Template",
            "",
            "Record command start time, exit code, and short reviewer notes for each command.",
            "",
            *[f"- [ ] `{command}` | exit code: ____ | notes: ____" for command in commands],
            "",
        ]
    )


def build_dashboard_walkthrough_markdown(
    config: ReleaseReadinessConfig | None = None,
) -> str:
    """Build a deterministic dashboard review path."""

    _ = config or ReleaseReadinessConfig()
    pages = (
        "Overview",
        "Alert Queue",
        "Case Queue",
        "Case Detail",
        "Graph View",
        "Account Profile",
        "Model Metrics",
        "Audit Log",
        "Validation Report",
    )
    return "\n".join(
        [
            "# Dashboard Walkthrough",
            "",
            "Use the Streamlit dashboard to review the system in this order:",
            "",
            *[f"1. {page}" for page in pages],
            "",
            "Confirm that each page uses persisted local data and does not trigger upstream runs.",
            "",
        ]
    )


def build_demo_validation_checklist_markdown(
    inputs: dict[str, object],
    config: ReleaseReadinessConfig | None = None,
) -> str:
    """Build a checklist of expected persisted evidence classes."""

    if not isinstance(inputs, dict):
        raise DemoEvidenceError("inputs must be a mapping")
    _ = config or ReleaseReadinessConfig()
    evidence = (
        "persisted transactions",
        "alerts",
        "graph features",
        "anomaly scores",
        "cases",
        "case evidence",
        "labels",
        "supervised scores",
        "model comparison",
        "monitoring",
        "explainability",
        "governance inventory",
        "security controls",
    )
    return "\n".join(
        [
            "# Demo Validation Checklist",
            "",
            "Expected evidence before final portfolio review:",
            "",
            *[f"- [ ] {item}" for item in evidence],
            "",
            "Input summaries are read-only snapshots from persisted tables where available.",
            "",
        ]
    )


def _evidence_type(path: str) -> str:
    name = path.lower()
    if "walkthrough" in name:
        return "dashboard_walkthrough"
    if "transcript" in name:
        return "command_transcript"
    if "architecture" in name:
        return "architecture_summary"
    if "portfolio" in name:
        return "portfolio_summary"
    if "checklist" in name:
        return "demo_checklist"
    if "index" in name:
        return "index"
    return Path(path).suffix.lower().lstrip(".") or "other"


def build_demo_evidence_index(
    generated_paths: dict[str, str],
    release_run_id: str,
) -> pd.DataFrame:
    """Build evidence index rows for generated release pack paths."""

    if not isinstance(generated_paths, dict) or not release_run_id:
        raise DemoEvidenceError("generated paths and release_run_id are required")
    rows = [
        {
            "release_run_id": release_run_id,
            "evidence_name": str(name),
            "evidence_type": _evidence_type(str(path)),
            "relative_path": str(path).replace("\\", "/"),
            "status": "available",
            "details": {"generated": True},
            "metadata": {},
        }
        for name, path in sorted(generated_paths.items())
    ]
    return pd.DataFrame(rows, columns=DEMO_EVIDENCE_COLUMNS)
