"""Local artefact writers for release readiness outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.release.exceptions import ReleasePersistenceError
from graph_aml.release.portfolio_pack import ReleasePortfolioPack
from graph_aml.release.summary import release_readiness_result_to_dict
from graph_aml.release.validation import ReleaseReadinessResult


def _ensure_parent(output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(frame: pd.DataFrame, output_path: Path | str) -> Path:
    try:
        path = _ensure_parent(output_path)
        frame.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise ReleasePersistenceError(f"failed to write release CSV: {exc}") from exc


def write_release_repository_checks_csv(
    checks: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/release_repository_checks.csv",
) -> Path:
    return _write_csv(checks, output_path)


def write_release_documentation_checks_csv(
    checks: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/release_documentation_checks.csv",
) -> Path:
    return _write_csv(checks, output_path)


def write_release_artefact_checks_csv(
    checks: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/release_artefact_checks.csv",
) -> Path:
    return _write_csv(checks, output_path)


def write_release_validation_index_csv(
    index: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/release_validation_index.csv",
) -> Path:
    return _write_csv(index, output_path)


def write_release_evidence_index_csv(
    evidence: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/release_evidence_index.csv",
) -> Path:
    return _write_csv(evidence, output_path)


def write_release_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/release_readiness_summary.json",
) -> Path:
    try:
        path = _ensure_parent(output_path)
        path.write_text(
            json.dumps(summary, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise ReleasePersistenceError(f"failed to write release summary: {exc}") from exc


def _write_text(text: str, output_path: Path | str) -> Path:
    try:
        path = _ensure_parent(output_path)
        path.write_text(text, encoding="utf-8")
        return path
    except Exception as exc:
        raise ReleasePersistenceError(f"failed to write release Markdown: {exc}") from exc


def write_portfolio_summary_md(
    pack: ReleasePortfolioPack,
    output_path: Path | str = "reports/model_validation/release_pack/portfolio_summary.md",
) -> Path:
    return _write_text(pack.portfolio_summary_md, output_path)


def write_architecture_summary_md(
    pack: ReleasePortfolioPack,
    output_path: Path | str = "reports/model_validation/release_pack/architecture_summary.md",
) -> Path:
    return _write_text(pack.architecture_summary_md, output_path)


def write_dashboard_walkthrough_md(
    pack: ReleasePortfolioPack,
    output_path: Path | str = "reports/model_validation/release_pack/dashboard_walkthrough.md",
) -> Path:
    return _write_text(pack.dashboard_walkthrough_md, output_path)


def write_command_transcript_template_md(
    pack: ReleasePortfolioPack,
    output_path: Path | str = (
        "reports/model_validation/release_pack/command_transcript_template.md"
    ),
) -> Path:
    return _write_text(pack.command_transcript_template_md, output_path)


def write_demo_validation_checklist_md(
    pack: ReleasePortfolioPack,
    output_path: Path | str = "reports/model_validation/release_pack/demo_validation_checklist.md",
) -> Path:
    return _write_text(pack.demo_validation_checklist_md, output_path)


def write_release_readiness_report_md(
    result: ReleaseReadinessResult,
    output_path: Path | str = "reports/model_validation/release_readiness_report.md",
) -> Path:
    status = "not_ready" if result.summary.get("failed_check_count", 0) else "ready"
    report = "\n".join(
        [
            "# Release Readiness Report",
            "",
            f"- Release run: `{result.release_run_id}`",
            f"- Release version: `{result.summary.get('release_version')}`",
            f"- Status: `{status}`",
            f"- Failed checks: {result.summary.get('failed_check_count', 0)}",
            f"- Warning checks: {result.summary.get('warning_check_count', 0)}",
            f"- Validation artefacts indexed: {result.summary.get('validation_artefact_count', 0)}",
            f"- Evidence items indexed: {result.summary.get('evidence_item_count', 0)}",
            "",
            "## Scope",
            "",
            (
                "This report packages existing local evidence for portfolio review. It does not "
                "run data pipelines, alter analytical outputs, or launch the dashboard."
            ),
            "",
            "## Evidence Pack",
            "",
            "- `release_pack/portfolio_summary.md`",
            "- `release_pack/architecture_summary.md`",
            "- `release_pack/dashboard_walkthrough.md`",
            "- `release_pack/command_transcript_template.md`",
            "- `release_pack/demo_validation_checklist.md`",
            "",
        ]
    )
    return _write_text(report, output_path)


def generate_release_readiness_artefacts(
    result: ReleaseReadinessResult,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write all release readiness artefacts."""

    root = Path(output_dir)
    pack = result.portfolio_pack
    payload = release_readiness_result_to_dict(result)
    return {
        "repository_checks": write_release_repository_checks_csv(
            result.repository_checks,
            root / "release_repository_checks.csv",
        ),
        "documentation_checks": write_release_documentation_checks_csv(
            result.documentation_checks,
            root / "release_documentation_checks.csv",
        ),
        "artefact_checks": write_release_artefact_checks_csv(
            result.artefact_checks,
            root / "release_artefact_checks.csv",
        ),
        "validation_index": write_release_validation_index_csv(
            result.validation_index,
            root / "release_validation_index.csv",
        ),
        "evidence_index": write_release_evidence_index_csv(
            result.evidence_index,
            root / "release_evidence_index.csv",
        ),
        "summary": write_release_summary_json(payload, root / "release_readiness_summary.json"),
        "report": write_release_readiness_report_md(result, root / "release_readiness_report.md"),
        "portfolio_summary": write_portfolio_summary_md(
            pack,
            root / "release_pack" / "portfolio_summary.md",
        ),
        "architecture_summary": write_architecture_summary_md(
            pack,
            root / "release_pack" / "architecture_summary.md",
        ),
        "dashboard_walkthrough": write_dashboard_walkthrough_md(
            pack,
            root / "release_pack" / "dashboard_walkthrough.md",
        ),
        "command_transcript_template": write_command_transcript_template_md(
            pack,
            root / "release_pack" / "command_transcript_template.md",
        ),
        "demo_validation_checklist": write_demo_validation_checklist_md(
            pack,
            root / "release_pack" / "demo_validation_checklist.md",
        ),
    }
