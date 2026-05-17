"""Local artefact writers for case evidence packs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import cast

import pandas as pd

from graph_aml.cases.evidence_builders import CaseEvidenceBuildResult
from graph_aml.cases.evidence_persistence import CaseEvidencePersistenceResult
from graph_aml.cases.exceptions import CaseEvidencePersistenceError, CaseEvidenceValidationError
from graph_aml.cases.summary import (
    case_evidence_build_result_to_dict,
    summarise_case_evidence_packs,
)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], frame.astype(object).to_dict(orient="records"))


def _write_json(payload: object, output_path: Path | str) -> Path:
    path = Path(output_path)
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def write_case_evidence_packs_json(
    evidence_packs: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_evidence_packs.json",
) -> Path:
    try:
        return _write_json(_records(evidence_packs), output_path)
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to write evidence packs JSON: {exc}") from exc


def write_case_explanations_json(
    explanations: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_explanations.json",
) -> Path:
    try:
        return _write_json(_records(explanations), output_path)
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to write explanations JSON: {exc}") from exc


def write_case_explanations_markdown(
    explanations: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_explanations.md",
) -> Path:
    try:
        path = Path(output_path)
        _ensure_parent(path)
        lines = ["# Case Explanations", ""]
        for row in explanations.sort_values("case_id").astype(object).to_dict(orient="records"):
            lines.extend(
                [
                    f"## {row.get('case_id')}",
                    "",
                    str(row.get("explanation_text", "")),
                    "",
                ]
            )
            bullets = row.get("explanation_bullets") or []
            if isinstance(bullets, list):
                lines.extend(f"- {bullet}" for bullet in bullets)
                lines.append("")
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to write explanations Markdown: {exc}") from exc


def write_case_evidence_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/case_evidence_summary.json",
) -> Path:
    try:
        return _write_json(summary, output_path)
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to write evidence summary JSON: {exc}") from exc


def write_case_evidence_persistence_summary_json(
    result: CaseEvidencePersistenceResult,
    output_path: Path | str = "reports/model_validation/case_evidence_persistence_summary.json",
) -> Path:
    try:
        return _write_json(asdict(result), output_path)
    except Exception as exc:
        raise CaseEvidencePersistenceError(
            f"Failed to write evidence persistence summary JSON: {exc}"
        ) from exc


def generate_case_evidence_artefacts(
    build_result: CaseEvidenceBuildResult,
    persistence_result: CaseEvidencePersistenceResult | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write all case evidence artefacts."""

    try:
        base = Path(output_dir)
        paths = {
            "case_evidence_packs_json": write_case_evidence_packs_json(
                build_result.evidence_packs, base / "case_evidence_packs.json"
            ),
            "case_explanations_json": write_case_explanations_json(
                build_result.explanations, base / "case_explanations.json"
            ),
            "case_explanations_markdown": write_case_explanations_markdown(
                build_result.explanations, base / "case_explanations.md"
            ),
            "case_evidence_summary_json": write_case_evidence_summary_json(
                {
                    **case_evidence_build_result_to_dict(build_result),
                    **summarise_case_evidence_packs(build_result.evidence_packs),
                },
                base / "case_evidence_summary.json",
            ),
        }
        if persistence_result is not None:
            paths["case_evidence_persistence_summary_json"] = (
                write_case_evidence_persistence_summary_json(
                    persistence_result, base / "case_evidence_persistence_summary.json"
                )
            )
        return paths
    except CaseEvidencePersistenceError:
        raise
    except Exception as exc:
        raise CaseEvidenceValidationError(
            f"Failed to generate case evidence artefacts: {exc}"
        ) from exc
