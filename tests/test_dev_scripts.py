"""Tests for local developer utility scripts."""

import sys
from pathlib import Path
from subprocess import run

from scripts import dev

ROOT = Path(__file__).resolve().parents[1]
DEV_SCRIPT = ROOT / "scripts" / "dev.py"


def run_dev_command(*args: str) -> object:
    return run(
        [sys.executable, str(DEV_SCRIPT), *args],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )


def test_dev_script_exists() -> None:
    assert DEV_SCRIPT.is_file()


def test_dev_script_help_command_works() -> None:
    result = run_dev_command("--help")

    assert result.returncode == 0
    assert "Local developer utilities" in result.stdout


def test_check_env_command_exits_zero() -> None:
    result = run_dev_command("check-env")

    assert result.returncode == 0
    assert "Python:" in result.stdout
    assert "docker-compose.yml exists:" in result.stdout


def test_info_command_exits_zero() -> None:
    result = run_dev_command("info")

    assert result.returncode == 0
    assert "Project: graph-aml-case-triage" in result.stdout


def test_verify_scaffold_command_exits_zero() -> None:
    result = run_dev_command("verify-scaffold")

    assert result.returncode == 0
    assert "Scaffold verification: OK" in result.stdout


def test_clean_caches_runs_safely_in_temp_directory(tmp_path: Path) -> None:
    for directory_name in (
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        "dist",
        "build",
    ):
        (tmp_path / directory_name).mkdir()
    (tmp_path / ".coverage").write_text("coverage", encoding="utf-8")
    package_cache = tmp_path / "src" / "package" / "__pycache__"
    package_cache.mkdir(parents=True)
    egg_info = tmp_path / "example.egg-info"
    egg_info.mkdir()

    assert dev.clean_caches(tmp_path) == 0
    assert not package_cache.exists()
    assert not egg_info.exists()
    assert not (tmp_path / ".coverage").exists()


def test_verify_scaffold_reports_missing_paths_for_incomplete_root(
    tmp_path: Path,
    capsys: object,
) -> None:
    result = dev.verify_scaffold(tmp_path)
    captured = capsys.readouterr()

    assert result == 1
    assert "Scaffold verification: FAILED" in captured.out
    assert "Missing: README.md" in captured.out


def test_check_env_does_not_require_docker_to_be_running() -> None:
    result = run_dev_command("check-env")

    assert result.returncode == 0
    assert "Docker" not in result.stderr
