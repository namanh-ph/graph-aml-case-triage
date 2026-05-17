from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "demo.py"


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_demo_cli_exists() -> None:
    assert SCRIPT.exists()


def test_demo_cli_help_exits_zero() -> None:
    result = _run_help()
    assert result.returncode == 0
    assert "plan" in result.stdout
    assert "readiness" in result.stdout
    assert "run" in result.stdout
    assert "validate" in result.stdout
    assert "artefacts" in result.stdout


def test_plan_help_exits_zero() -> None:
    assert _run_help("plan").returncode == 0


def test_readiness_help_exits_zero() -> None:
    assert _run_help("readiness").returncode == 0


def test_run_help_includes_safety_options() -> None:
    stdout = _run_help("run").stdout
    assert "--dry-run" in stdout
    assert "--include-reset" in stdout
    assert "--stop-on-failure" in stdout
    assert "--continue-on-failure" in stdout


def test_validate_help_exits_zero() -> None:
    assert _run_help("validate").returncode == 0


def test_artefacts_help_exits_zero() -> None:
    assert _run_help("artefacts").returncode == 0


def test_cli_source_uses_subprocess_only_through_runner_helpers() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "import subprocess" not in text
    assert "subprocess.run" not in text
    assert "run_demo_pipeline" in text


def test_cli_source_disposes_postgresql_engine_in_validation_command() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "dispose_dashboard_engine(engine)" in text


def test_cli_source_does_not_create_neo4j_driver_or_launch_streamlit() -> None:
    text = SCRIPT.read_text(encoding="utf-8").lower()
    assert "graphdatabase.driver" not in text
    assert "streamlit run" not in text


def test_cli_source_does_not_run_cloud_deployment_commands() -> None:
    text = SCRIPT.read_text(encoding="utf-8").lower()
    assert "terraform" not in text
    assert "kubectl" not in text
    assert "aws " not in text
