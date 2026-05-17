"""Tests for release artefact checks."""

import pytest

from graph_aml.release import (
    ARTEFACT_CHECK_COLUMNS,
    ArtefactCheckError,
    ReleaseArtefactConfig,
    ReleaseReadinessConfig,
    build_release_validation_index,
    check_optional_release_artefacts,
    check_required_release_artefacts,
    classify_release_artefact,
    run_artefact_checks,
)


def test_artefact_classification_and_checks(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "model_card.md").write_text("card", encoding="utf-8")
    (report_dir / "metrics.json").write_text("{}", encoding="utf-8")
    config = ReleaseReadinessConfig(
        artefacts=ReleaseArtefactConfig(
            report_dir="reports",
            required_files=("model_card.md", "missing.md"),
            optional_files=("metrics.json",),
            max_file_size_mb=1,
        )
    )

    assert classify_release_artefact("model_card.md") == "model_card"
    assert classify_release_artefact("metrics.json") == "metrics"
    required = check_required_release_artefacts(config, "run")
    optional = check_optional_release_artefacts(config, "run")
    index = build_release_validation_index(config, "run")
    checks = run_artefact_checks(config, "run")

    assert tuple(checks.columns) == ARTEFACT_CHECK_COLUMNS
    assert "fail" in set(required["status"])
    assert set(optional["status"]) == {"pass"}
    assert len(index) >= len(checks)


def test_missing_report_directory_and_path_traversal(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = ReleaseReadinessConfig(
        artefacts=ReleaseArtefactConfig(report_dir="missing", required_files=("a.md",))
    )
    frame = check_required_release_artefacts(config, "run")
    assert frame.iloc[0]["status"] == "fail"
    with pytest.raises(ArtefactCheckError):
        check_required_release_artefacts(
            ReleaseReadinessConfig(
                artefacts=ReleaseArtefactConfig(report_dir="../outside", required_files=("a.md",))
            )
        )
