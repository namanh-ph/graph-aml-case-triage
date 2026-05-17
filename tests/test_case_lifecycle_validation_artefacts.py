"""Tests for lifecycle validation and artefacts."""

import json

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseLifecycleValidationError,
    build_case_lifecycle_quality_summary,
    compare_case_lifecycle_event_counts,
    generate_case_lifecycle_artefacts,
    validate_case_assignment_frame,
    validate_lifecycle_event_frame,
    write_case_assignments_json,
    write_case_lifecycle_events_csv,
    write_case_lifecycle_events_json,
    write_case_lifecycle_summary_json,
)


def events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "action_id": ["A1"],
            "case_id": ["CASE1"],
            "action_type": ["comment"],
            "analyst_id": ["analyst"],
            "action_timestamp": [pd.Timestamp("2026-01-01", tz="UTC")],
        }
    )


def assignments() -> pd.DataFrame:
    return pd.DataFrame({"case_id": ["CASE1"], "assigned_to": ["analyst"], "queue": ["AML Review"]})


def test_valid_frames_pass_and_invalid_frames_fail() -> None:
    validate_lifecycle_event_frame(events())
    validate_case_assignment_frame(assignments())
    with pytest.raises(CaseLifecycleValidationError):
        validate_lifecycle_event_frame(events().assign(action_id=""))
    with pytest.raises(CaseLifecycleValidationError):
        validate_lifecycle_event_frame(pd.concat([events(), events()], ignore_index=True))
    with pytest.raises(CaseLifecycleValidationError):
        validate_lifecycle_event_frame(events().assign(case_id=""))


def test_quality_summary_and_row_count_comparison_are_json_serialisable() -> None:
    summary = build_case_lifecycle_quality_summary(events())
    assert summary["action_type_counts"] == {"comment": 1}
    assert compare_case_lifecycle_event_counts(1, events())["status"] == "ok"
    json.dumps(summary)


def test_artefact_writers(tmp_path) -> None:
    assert write_case_lifecycle_events_csv(events(), tmp_path / "events.csv").is_file()
    events_json = write_case_lifecycle_events_json(events(), tmp_path / "events.json")
    json.loads(events_json.read_text())
    assignments_json = write_case_assignments_json(assignments(), tmp_path / "assignments.json")
    json.loads(assignments_json.read_text())
    summary_json = write_case_lifecycle_summary_json({"event_count": 1}, tmp_path / "summary.json")
    json.loads(summary_json.read_text())
    paths = generate_case_lifecycle_artefacts(
        events(), assignments(), {"event_count": 1}, tmp_path / "all"
    )
    assert all(path.is_file() for path in paths.values())
