"""Tests for case grouping helper functions."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseGroupingError,
    build_case_group_id,
    build_case_id,
    explode_alert_evidence_ids,
    normalise_case_list,
)


def test_case_list_normalisation_handles_common_inputs() -> None:
    assert normalise_case_list(["B", "A", "A"]) == ("A", "B")
    assert normalise_case_list(("T2", "T1")) == ("T1", "T2")
    assert normalise_case_list('["T2", "T1"]') == ("T1", "T2")
    assert normalise_case_list("T1") == ("T1",)


def test_evidence_ids_are_exploded_from_alert_records() -> None:
    alerts = pd.DataFrame({"alert_id": ["AL1"], "evidence_ids": [["T2", "T1"]]})
    result = explode_alert_evidence_ids(alerts)
    assert result["evidence_id"].tolist() == ["T1", "T2"]


def test_case_group_and_case_ids_are_deterministic() -> None:
    first = build_case_group_id("account", "A1", ["AL2", "AL1"])
    second = build_case_group_id("account", "A1", ["AL1", "AL2"])
    assert first == second
    assert build_case_id(first, "case_generation_v1") == build_case_id(first, "case_generation_v1")


def test_different_grouping_strategies_produce_different_ids() -> None:
    assert build_case_group_id("account", "A1", ["AL1"]) != build_case_group_id(
        "customer", "A1", ["AL1"]
    )


def test_malformed_evidence_payloads_raise() -> None:
    with pytest.raises(CaseGroupingError):
        normalise_case_list("[bad json")


def test_helper_functions_do_not_mutate_inputs() -> None:
    alerts = pd.DataFrame({"alert_id": ["AL1"], "evidence_ids": [["T1"]]})
    original = alerts.copy(deep=True)
    explode_alert_evidence_ids(alerts)
    pd.testing.assert_frame_equal(alerts, original)
