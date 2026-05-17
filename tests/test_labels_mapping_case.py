from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.labels import (
    CASE_LABEL_COLUMNS,
    LabelMappingError,
    build_case_labels,
    map_status_to_binary_label,
    normalise_label_status,
    select_latest_eligible_decision_events,
)


def _cases() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": ["C1"],
            "primary_account_id": ["A1"],
            "created_at": [pd.Timestamp("2026-01-01", tz="UTC")],
            "updated_at": [pd.Timestamp("2026-01-02", tz="UTC")],
        }
    )


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "action_id": ["E1", "E2"],
            "case_id": ["C1", "C1"],
            "to_status": ["In review", "Closed suspicious"],
            "action_type": ["status_change", "close_suspicious"],
            "analyst_id": ["u1", "u2"],
            "decision_reason": ["review", "suspicious pattern"],
            "comment": ["open", "closed"],
            "action_timestamp": [
                pd.Timestamp("2026-01-02", tz="UTC"),
                pd.Timestamp("2026-01-03", tz="UTC"),
            ],
        }
    )


def test_status_normalisation_is_deterministic() -> None:
    assert normalise_label_status(" Closed suspicious ") == "Closed suspicious"


def test_closed_suspicious_maps_to_one() -> None:
    assert map_status_to_binary_label("Closed suspicious") == 1


def test_closed_false_positive_maps_to_zero() -> None:
    assert map_status_to_binary_label("Closed false positive") == 0


def test_excluded_statuses_do_not_map_to_labels() -> None:
    assert map_status_to_binary_label("Archived") is None


def test_latest_eligible_decision_is_selected_per_case() -> None:
    selected = select_latest_eligible_decision_events(_events())
    assert selected.iloc[0]["action_id"] == "E2"


def test_case_labels_include_analyst_id_and_decision_reason() -> None:
    labels = build_case_labels(_cases(), _events())
    assert labels.iloc[0]["analyst_id"] == "u2"
    assert labels.iloc[0]["decision_reason"] == "suspicious pattern"


def test_case_labels_enforce_closure_reason_when_configured() -> None:
    events = _events()
    events.loc[1, "decision_reason"] = ""
    with pytest.raises(LabelMappingError):
        build_case_labels(_cases(), events)


def test_case_labels_enforce_closure_comment_when_configured() -> None:
    events = _events()
    events.loc[1, "comment"] = ""
    with pytest.raises(LabelMappingError):
        build_case_labels(_cases(), events)


def test_label_timestamp_before_case_creation_fails_leakage_control() -> None:
    cases = _cases()
    cases.loc[0, "created_at"] = pd.Timestamp("2026-01-04", tz="UTC")
    with pytest.raises(LabelMappingError):
        build_case_labels(cases, _events())


def test_case_label_output_columns_equal_constant() -> None:
    assert tuple(build_case_labels(_cases(), _events()).columns) == CASE_LABEL_COLUMNS


def test_input_dataframes_are_not_mutated() -> None:
    cases = _cases()
    events = _events()
    cases_copy = cases.copy(deep=True)
    events_copy = events.copy(deep=True)
    build_case_labels(cases, events)
    pd.testing.assert_frame_equal(cases, cases_copy)
    pd.testing.assert_frame_equal(events, events_copy)
