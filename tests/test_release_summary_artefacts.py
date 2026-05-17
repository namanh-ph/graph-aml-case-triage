"""Tests for release summaries and artefact writers."""

import json

import pandas as pd

from graph_aml.release import (
    release_readiness_result_to_dict,
    run_release_readiness_from_inputs,
    summarise_artefact_checks,
    summarise_evidence_index,
    summarise_repository_checks,
)
from graph_aml.release.artefacts import generate_release_readiness_artefacts
from tests.test_release_workflow import _config


def test_release_summaries_and_artefacts(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("# Overview\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "model_card.md").write_text("card", encoding="utf-8")
    (tmp_path / "Makefile").write_text("check:\n\tpython -m pytest\n", encoding="utf-8")
    result = run_release_readiness_from_inputs({}, _config())

    assert summarise_repository_checks(result.repository_checks)["pass_count"] >= 1
    assert summarise_artefact_checks(result.artefact_checks)["required_count"] == 1
    assert summarise_evidence_index(result.evidence_index)["row_count"] >= 1
    json.dumps(release_readiness_result_to_dict(result), default=str)

    paths = generate_release_readiness_artefacts(result, tmp_path / "out")
    assert all(path.exists() for path in paths.values())
    assert pd.read_csv(paths["repository_checks"]).empty is False
    json.loads(paths["summary"].read_text(encoding="utf-8"))
    assert "# Release Readiness Report" in paths["report"].read_text(encoding="utf-8")
