"""Tests for release repository checks."""

import pytest

from graph_aml.release import (
    REPOSITORY_CHECK_COLUMNS,
    ReleaseReadinessConfig,
    ReleaseRepositoryConfig,
    RepositoryCheckError,
    check_forbidden_paths_absent,
    check_makefile_targets,
    check_required_directories,
    check_required_files,
    run_repository_checks,
)


def _config() -> ReleaseReadinessConfig:
    return ReleaseReadinessConfig(
        repository=ReleaseRepositoryConfig(
            required_files=("README.md", "missing.txt"),
            required_directories=("docs", "missing_dir"),
            forbidden_paths=("secrets",),
            required_make_targets=("check", "missing-target"),
        )
    )


def test_repository_checks_statuses_and_columns(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "Makefile").write_text("check:\n\tpython -m pytest\n", encoding="utf-8")

    config = _config()
    files = check_required_files(config, "run")
    dirs = check_required_directories(config, "run")
    forbidden = check_forbidden_paths_absent(config, "run")
    targets = check_makefile_targets(config, "run")
    all_checks = run_repository_checks(config, "run")

    assert tuple(all_checks.columns) == REPOSITORY_CHECK_COLUMNS
    assert "pass" in set(files["status"])
    assert "fail" in set(files["status"])
    assert "fail" in set(dirs["status"])
    assert set(forbidden["status"]) == {"pass"}
    assert "fail" in set(targets["status"])


def test_forbidden_path_fails_when_present(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "secrets").mkdir()
    frame = check_forbidden_paths_absent(_config(), "run")
    assert frame.iloc[0]["status"] == "fail"


def test_repository_checks_reject_unsafe_paths() -> None:
    with pytest.raises(RepositoryCheckError):
        check_required_files(
            ReleaseReadinessConfig(
                repository=ReleaseRepositoryConfig(required_files=("../outside",))
            )
        )
