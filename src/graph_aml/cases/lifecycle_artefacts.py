"""Local artefact writers for AML case lifecycle records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pandas as pd

from graph_aml.cases.exceptions import (
    CaseLifecyclePersistenceError,
    CaseLifecycleValidationError,
)
from graph_aml.cases.lifecycle_validation import (
    build_case_lifecycle_quality_summary,
    validate_case_assignment_frame,
    validate_lifecycle_event_frame,
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


def write_case_lifecycle_events_csv(
    events: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_lifecycle_events.csv",
) -> Path:
    try:
        validate_lifecycle_event_frame(events)
        path = Path(output_path)
        _ensure_parent(path)
        events.to_csv(path, index=False)
        return path
    except CaseLifecycleValidationError:
        raise
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to write lifecycle CSV: {exc}") from exc


def write_case_lifecycle_events_json(
    events: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_lifecycle_events.json",
) -> Path:
    try:
        validate_lifecycle_event_frame(events)
        return _write_json(_records(events), output_path)
    except CaseLifecycleValidationError:
        raise
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to write lifecycle JSON: {exc}") from exc


def write_case_assignments_json(
    assignments: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_assignments.json",
) -> Path:
    try:
        validate_case_assignment_frame(assignments)
        return _write_json(_records(assignments), output_path)
    except CaseLifecycleValidationError:
        raise
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to write assignment JSON: {exc}") from exc


def write_case_lifecycle_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/case_lifecycle_summary.json",
) -> Path:
    try:
        return _write_json(summary, output_path)
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to write lifecycle summary: {exc}") from exc


def generate_case_lifecycle_artefacts(
    events: pd.DataFrame,
    assignments: pd.DataFrame | None = None,
    summary: dict[str, object] | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    base = Path(output_dir)
    paths: dict[str, Path] = {
        "events_csv": write_case_lifecycle_events_csv(events, base / "case_lifecycle_events.csv"),
        "events_json": write_case_lifecycle_events_json(
            events, base / "case_lifecycle_events.json"
        ),
    }
    if assignments is not None:
        paths["assignments_json"] = write_case_assignments_json(
            assignments, base / "case_assignments.json"
        )
    payload = summary if summary is not None else build_case_lifecycle_quality_summary(events)
    paths["summary_json"] = write_case_lifecycle_summary_json(
        payload, base / "case_lifecycle_summary.json"
    )
    return paths
