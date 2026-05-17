from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from graph_aml.demo import (
    DemoCommandConfig,
    DemoOrchestrationConfig,
    DemoRunResult,
    DemoStep,
    DemoStepConfig,
    build_demo_run_id,
    demo_run_result_to_dict,
    execute_demo_step,
    run_demo_pipeline,
)


def _single_step_config(command: str = "echo ok") -> DemoOrchestrationConfig:
    return DemoOrchestrationConfig(
        steps=DemoStepConfig(full_pipeline=("one",)),
        commands=DemoCommandConfig(commands={"one": command}),
    )


def test_demo_run_id_is_deterministic_for_fixed_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    assert build_demo_run_id(started_at=timestamp) == build_demo_run_id(started_at=timestamp)


def test_execute_demo_step_supports_dry_run(monkeypatch) -> None:
    def fail_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("subprocess should not run")

    monkeypatch.setattr("graph_aml.demo.runner.subprocess.run", fail_run)
    result = execute_demo_step(DemoStep("one", "echo ok"), dry_run=True)
    assert result.status == "planned"


def test_dry_run_does_not_call_subprocess(monkeypatch) -> None:
    called = False

    def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
        nonlocal called
        called = True

    monkeypatch.setattr("graph_aml.demo.runner.subprocess.run", fake_run)
    execute_demo_step(DemoStep("one", "echo ok"), dry_run=True)
    assert called is False


def test_successful_subprocess_result_returns_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.demo.runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )
    assert execute_demo_step(DemoStep("one", "echo ok")).status == "success"


def test_failed_subprocess_result_returns_failed(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.demo.runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="bad"),
    )
    result = execute_demo_step(DemoStep("one", "echo ok"))
    assert result.status == "failed"
    assert result.return_code == 1


def test_runner_stops_on_first_failure_when_configured(monkeypatch) -> None:
    config = replace(
        _single_step_config("echo fail"),
        steps=DemoStepConfig(full_pipeline=("one", "two")),
        commands=DemoCommandConfig(commands={"one": "echo fail", "two": "echo ok"}),
    )
    monkeypatch.setattr(
        "graph_aml.demo.runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="bad"),
    )
    result = run_demo_pipeline(config, stop_on_failure=True)
    assert [step.status for step in result.steps] == ["failed", "skipped"]


def test_runner_continues_on_failure_when_configured(monkeypatch) -> None:
    config = replace(
        _single_step_config("echo fail"),
        steps=DemoStepConfig(full_pipeline=("one", "two")),
        commands=DemoCommandConfig(commands={"one": "echo fail", "two": "echo ok"}),
    )
    responses = iter(
        [
            SimpleNamespace(returncode=1, stdout="", stderr="bad"),
            SimpleNamespace(returncode=0, stdout="ok", stderr=""),
        ]
    )
    monkeypatch.setattr(
        "graph_aml.demo.runner.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )
    result = run_demo_pipeline(config, stop_on_failure=False)
    assert [step.status for step in result.steps] == ["failed", "success"]


def test_runner_returns_demo_run_result(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.demo.runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )
    assert isinstance(run_demo_pipeline(_single_step_config()), DemoRunResult)


def test_run_result_converts_to_json_serialisable_dictionary(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.demo.runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )
    payload = demo_run_result_to_dict(run_demo_pipeline(_single_step_config()))
    assert payload["status"] == "success"


def test_runner_does_not_create_database_or_neo4j_drivers(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.demo.runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )
    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: pytest.fail("no db"))
    assert run_demo_pipeline(_single_step_config()).status == "success"
