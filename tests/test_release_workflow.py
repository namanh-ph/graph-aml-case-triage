"""Tests for release readiness workflow."""

import pandas as pd
import pytest

from graph_aml.release import (
    ReleaseArtefactConfig,
    ReleaseDocumentationConfig,
    ReleaseReadinessConfig,
    ReleaseReadinessResult,
    ReleaseRepositoryConfig,
    ReleaseValidationError,
    build_release_run_id,
    run_release_readiness_from_inputs,
)


def _config() -> ReleaseReadinessConfig:
    return ReleaseReadinessConfig(
        repository=ReleaseRepositoryConfig(
            required_files=("README.md",),
            required_directories=("docs",),
            forbidden_paths=("secrets",),
            required_make_targets=("check",),
        ),
        documentation=ReleaseDocumentationConfig(
            required_docs=("README.md",),
            required_sections={"README.md": ("overview",)},
        ),
        artefacts=ReleaseArtefactConfig(
            report_dir="reports",
            required_files=("model_card.md",),
            optional_files=(),
        ),
    )


def test_release_run_id_is_deterministic() -> None:
    timestamp = pd.Timestamp("2026-01-01T00:00:00Z")
    assert build_release_run_id(_config(), timestamp) == build_release_run_id(_config(), timestamp)


def test_release_workflow_builds_result(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("# Overview\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "model_card.md").write_text("card", encoding="utf-8")
    (tmp_path / "Makefile").write_text("check:\n\tpython -m pytest\n", encoding="utf-8")

    inputs: dict[str, object] = {"engine_supplied": False}
    result = run_release_readiness_from_inputs(inputs, _config())

    assert isinstance(result, ReleaseReadinessResult)
    assert not result.repository_checks.empty
    assert not result.documentation_checks.empty
    assert not result.artefact_checks.empty
    assert not result.validation_index.empty
    assert not result.evidence_index.empty
    assert result.summary["failed_check_count"] == 0
    assert inputs == {"engine_supplied": False}


def test_release_workflow_rejects_bad_inputs() -> None:
    with pytest.raises(ReleaseValidationError):
        run_release_readiness_from_inputs("bad")  # type: ignore[arg-type]
