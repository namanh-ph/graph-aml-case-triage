"""Tests for account risk scoring artefact writers."""

import json

from graph_aml.scoring import (
    AccountRiskScorePersistenceResult,
    compute_account_risk_scores,
    generate_account_risk_score_artefacts,
    write_account_risk_score_persistence_summary_json,
    write_account_risk_score_summary_json,
    write_account_risk_scores_csv,
    write_account_risk_scores_json,
)
from tests.test_scoring_composite import components


def test_artefact_writers(tmp_path) -> None:
    result = compute_account_risk_scores(components())
    csv_path = write_account_risk_scores_csv(result.scores, tmp_path / "scores.csv")
    json_path = write_account_risk_scores_json(result.scores, tmp_path / "scores.json")
    summary_path = write_account_risk_score_summary_json(result.summary, tmp_path / "summary.json")
    persistence_path = write_account_risk_score_persistence_summary_json(
        AccountRiskScorePersistenceResult(),
        tmp_path / "persist.json",
    )
    assert csv_path.is_file()
    json.loads(json_path.read_text())
    json.loads(summary_path.read_text())
    json.loads(persistence_path.read_text())


def test_high_level_generator_writes_expected_paths(tmp_path) -> None:
    paths = generate_account_risk_score_artefacts(
        compute_account_risk_scores(components()),
        AccountRiskScorePersistenceResult(),
        tmp_path,
    )
    assert {"scores_csv", "scores_json", "score_summary_json", "persistence_summary_json"} <= set(
        paths
    )
    assert all(path.is_file() for path in paths.values())
