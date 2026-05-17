"""Local artefact writers for case generation."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import cast

import pandas as pd

from graph_aml.cases.exceptions import CasePersistenceError
from graph_aml.cases.generation import CaseGenerationResult
from graph_aml.cases.persistence import CasePersistenceResult


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return cast(
        list[dict[str, object]],
        frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records"),
    )


def write_generated_cases_csv(
    cases: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/generated_cases.csv",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        cases.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise CasePersistenceError(f"Failed to write generated cases CSV: {exc}") from exc


def write_generated_cases_json(
    cases: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/generated_cases.json",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        path.write_text(
            json.dumps(_records(cases), indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise CasePersistenceError(f"Failed to write generated cases JSON: {exc}") from exc


def write_case_links_json(
    case_alerts: pd.DataFrame,
    case_entities: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/generated_case_links.json",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        payload = {
            "case_alerts": _records(case_alerts),
            "case_entities": _records(case_entities),
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise CasePersistenceError(f"Failed to write case links JSON: {exc}") from exc


def write_case_generation_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/case_generation_summary.json",
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
        raise CasePersistenceError(f"Failed to write case generation summary JSON: {exc}") from exc


def write_case_persistence_summary_json(
    result: CasePersistenceResult,
    output_path: Path | str = "reports/model_validation/case_persistence_summary.json",
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
        raise CasePersistenceError(f"Failed to write case persistence summary JSON: {exc}") from exc


def generate_case_generation_artefacts(
    generation_result: CaseGenerationResult,
    persistence_result: CasePersistenceResult | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    output = Path(output_dir)
    paths = {
        "generated_cases_csv": write_generated_cases_csv(
            generation_result.cases,
            output / "generated_cases.csv",
        ),
        "generated_cases_json": write_generated_cases_json(
            generation_result.cases,
            output / "generated_cases.json",
        ),
        "case_links_json": write_case_links_json(
            generation_result.case_alerts,
            generation_result.case_entities,
            output / "generated_case_links.json",
        ),
        "case_generation_summary_json": write_case_generation_summary_json(
            generation_result.summary,
            output / "case_generation_summary.json",
        ),
    }
    if persistence_result is not None:
        paths["case_persistence_summary_json"] = write_case_persistence_summary_json(
            persistence_result,
            output / "case_persistence_summary.json",
        )
    return paths
