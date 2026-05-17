"""Tests for case risk artefact writers."""

import json

import pandas as pd

from graph_aml.cases import (
    CaseRiskScorePersistenceResult,
    CaseRiskScoreResult,
    generate_case_risk_score_artefacts,
    write_case_risk_score_persistence_summary_json,
    write_case_risk_score_summary_json,
    write_case_risk_scores_csv,
    write_case_risk_scores_json,
)
from tests.fixtures.case_risk import case_risk_score_result


def test_case_risk_artefact_writers(tmp_path) -> None:  # noqa: ANN001
    result = case_risk_score_result()
    csv_path = write_case_risk_scores_csv(result.scores, tmp_path / "nested" / "scores.csv")
    json_path = write_case_risk_scores_json(result.scores, tmp_path / "scores.json")
    summary_path = write_case_risk_score_summary_json({"row_count": 1}, tmp_path / "summary.json")
    persistence_path = write_case_risk_score_persistence_summary_json(
        CaseRiskScorePersistenceResult(),
        tmp_path / "persist.json",
    )
    assert csv_path.exists()
    for path in (json_path, summary_path, persistence_path):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), list | dict)


def test_high_level_case_risk_artefact_generator(tmp_path) -> None:  # noqa: ANN001
    paths = generate_case_risk_score_artefacts(
        case_risk_score_result(),
        CaseRiskScorePersistenceResult(),
        tmp_path,
    )
    assert set(paths) == {
        "case_risk_scores_csv",
        "case_risk_scores_json",
        "case_risk_score_summary_json",
        "case_risk_score_persistence_summary_json",
    }
    assert all(path.exists() for path in paths.values())


def test_empty_case_risk_frames_still_write_valid_artefacts(tmp_path) -> None:  # noqa: ANN001
    empty = CaseRiskScoreResult(pd.DataFrame(), pd.DataFrame())
    paths = generate_case_risk_score_artefacts(empty, None, tmp_path)
    assert all(path.exists() for path in paths.values())
