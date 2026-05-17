"""Artefact writers for case-level risk scoring."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import cast

import pandas as pd

from graph_aml.cases.exceptions import CaseRiskPersistenceError
from graph_aml.cases.risk_persistence import CaseRiskScorePersistenceResult
from graph_aml.cases.risk_scoring import CaseRiskScoreResult


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return cast(
        list[dict[str, object]],
        frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records"),
    )


def write_case_risk_scores_csv(
    scores: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_risk_scores.csv",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        scores.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to write case risk score CSV: {exc}") from exc


def write_case_risk_scores_json(
    scores: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_risk_scores.json",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        path.write_text(
            json.dumps(_records(scores), indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to write case risk score JSON: {exc}") from exc


def write_case_risk_score_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/case_risk_score_summary.json",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        path.write_text(
            json.dumps(summary, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to write case risk summary JSON: {exc}") from exc


def write_case_risk_score_persistence_summary_json(
    result: CaseRiskScorePersistenceResult,
    output_path: Path | str = "reports/model_validation/case_risk_score_persistence_summary.json",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        payload = asdict(result) if is_dataclass(result) else dict(result)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise CaseRiskPersistenceError(
            f"Failed to write case risk persistence summary JSON: {exc}"
        ) from exc


def generate_case_risk_score_artefacts(
    scoring_result: CaseRiskScoreResult,
    persistence_result: CaseRiskScorePersistenceResult | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    output = Path(output_dir)
    paths = {
        "case_risk_scores_csv": write_case_risk_scores_csv(
            scoring_result.scores,
            output / "case_risk_scores.csv",
        ),
        "case_risk_scores_json": write_case_risk_scores_json(
            scoring_result.scores,
            output / "case_risk_scores.json",
        ),
        "case_risk_score_summary_json": write_case_risk_score_summary_json(
            scoring_result.summary,
            output / "case_risk_score_summary.json",
        ),
    }
    if persistence_result is not None:
        paths["case_risk_score_persistence_summary_json"] = (
            write_case_risk_score_persistence_summary_json(
                persistence_result,
                output / "case_risk_score_persistence_summary.json",
            )
        )
    return paths
