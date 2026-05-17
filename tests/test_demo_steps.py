from __future__ import annotations

from datetime import UTC, datetime

import pytest

from graph_aml.demo import (
    DemoOrchestrationConfig,
    DemoStepConfig,
    DemoStepError,
    DemoStepResult,
    build_demo_steps,
    demo_step_result_to_dict,
    validate_demo_command_safety,
)


def test_demo_steps_are_built_in_configured_order() -> None:
    config = DemoOrchestrationConfig(
        steps=DemoStepConfig(full_pipeline=("db_health", "graph_health"))
    )
    assert [step.name for step in build_demo_steps(config)] == ["db_health", "graph_health"]


def test_reset_step_is_excluded_by_default() -> None:
    assert build_demo_steps(DemoOrchestrationConfig())[0].name != "db_reset"


def test_reset_step_can_be_included_explicitly() -> None:
    assert build_demo_steps(DemoOrchestrationConfig(), include_reset=True)[0].name == "db_reset"


def test_commands_are_preserved_deterministically() -> None:
    steps = build_demo_steps(DemoOrchestrationConfig())
    assert steps[0].command == "python scripts/db.py health"
    assert steps == build_demo_steps(DemoOrchestrationConfig())


def test_safe_commands_pass_validation() -> None:
    validate_demo_command_safety("python scripts/dashboard.py summary")


def test_forbidden_commands_raise() -> None:
    with pytest.raises(DemoStepError):
        validate_demo_command_safety("echo start && DROP DATABASE aml")


def test_reset_commands_raise_without_destructive_permission() -> None:
    with pytest.raises(DemoStepError):
        validate_demo_command_safety("make db-reset")


def test_reset_commands_pass_with_destructive_permission() -> None:
    validate_demo_command_safety("make db-reset", allow_destructive=True)


def test_step_result_converts_to_json_serialisable_dictionary() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    payload = demo_step_result_to_dict(
        DemoStepResult(
            name="db_health",
            command="python scripts/db.py health",
            started_at=now,
            completed_at=now,
            return_code=0,
            status="success",
        )
    )
    assert payload["started_at"] == "2026-01-01T00:00:00+00:00"


def test_step_construction_does_not_execute_commands(monkeypatch) -> None:
    def fail_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("subprocess should not run")

    monkeypatch.setattr("subprocess.run", fail_run)
    assert build_demo_steps(DemoOrchestrationConfig())
