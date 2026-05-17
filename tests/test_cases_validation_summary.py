"""Tests for case validation and summaries."""

import json

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseGenerationResult,
    CaseValidationError,
    build_case_generation_quality_summary,
    case_generation_result_to_dict,
    compare_case_row_counts,
    summarise_case_groups,
    summarise_generated_cases,
    validate_case_generation_result,
    validate_case_group_frame,
    validate_prepared_case_frames,
)
from graph_aml.cases.grouping import CASE_GROUP_COLUMNS, CASE_RECORD_COLUMNS


def generated() -> CaseGenerationResult:
    cases = pd.DataFrame(
        [
            [
                "CASE1",
                "case_generation_v1",
                "A1",
                "C1",
                ["A1"],
                ["C1"],
                ["AL1"],
                ["structuring"],
                ["Structuring"],
                10.0,
                1,
                1,
                1,
                80.0,
                80.0,
                85.0,
                85.0,
                "high",
                "New",
                "account",
                "A1",
                "summary",
                pd.Timestamp("2026-01-01", tz="UTC"),
                pd.Timestamp("2026-01-01", tz="UTC"),
            ]
        ],
        columns=CASE_RECORD_COLUMNS,
    )
    return CaseGenerationResult(
        cases=cases,
        case_alerts=pd.DataFrame({"case_id": ["CASE1"], "alert_id": ["AL1"]}),
        case_entities=pd.DataFrame(),
        groups=pd.DataFrame(),
    )


def test_valid_case_group_and_generation_result_pass() -> None:
    groups = pd.DataFrame(
        [["G1", "account", "A1", "C1", ["AL1"], ["A1"], ["C1"], [], ["t"], ["r"], "A1"]],
        columns=CASE_GROUP_COLUMNS,
    )
    validate_case_group_frame(groups)
    validate_case_generation_result(generated())


def test_duplicate_case_ids_and_alert_links_fail() -> None:
    result = generated()
    result.cases.loc[1] = result.cases.loc[0]
    with pytest.raises(CaseValidationError):
        validate_case_generation_result(result)
    result = generated()
    result.case_alerts.loc[1] = result.case_alerts.loc[0]
    with pytest.raises(CaseValidationError):
        validate_case_generation_result(result)


def test_invalid_priority_score_fails() -> None:
    result = generated()
    result.cases.loc[0, "priority_score"] = 101
    with pytest.raises(CaseValidationError):
        validate_case_generation_result(result)


def test_prepared_case_frames_pass_validation() -> None:
    result = generated()
    prepared = {
        "cases": result.cases.assign(metadata=[{}]),
        "case_alerts": result.case_alerts,
        "case_entities": pd.DataFrame(
            columns=("case_id", "entity_type", "entity_id", "relationship")
        ),
    }
    validate_prepared_case_frames(prepared)


def test_quality_row_count_and_summaries_are_serialisable() -> None:
    result = generated()
    quality = build_case_generation_quality_summary(result)
    assert quality["case_count"] == 1
    assert quality["grouping_strategy_counts"]["account"] == 1
    assert compare_case_row_counts(result.cases, result.cases)["status"] == "ok"
    assert summarise_generated_cases(result.cases)["case_count"] == 1
    assert summarise_case_groups(pd.DataFrame(columns=CASE_GROUP_COLUMNS))["case_group_count"] == 0
    json.dumps(case_generation_result_to_dict(result), default=str)
