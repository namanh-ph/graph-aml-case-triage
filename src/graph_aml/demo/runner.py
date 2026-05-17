"""Controlled demo pipeline runner."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime

from graph_aml.demo.config import DemoOrchestrationConfig, validate_demo_orchestration_config
from graph_aml.demo.exceptions import DemoStepError
from graph_aml.demo.steps import (
    DemoStep,
    DemoStepResult,
    build_demo_steps,
    demo_step_result_to_dict,
    validate_demo_command_safety,
)


@dataclass(frozen=True)
class DemoRunResult:
    run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "not_started"
    steps: tuple[DemoStepResult, ...] = ()
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def _config_or_default(config: DemoOrchestrationConfig | None) -> DemoOrchestrationConfig:
    resolved = config or DemoOrchestrationConfig()
    validate_demo_orchestration_config(resolved)
    return resolved


def _tail(value: str | None, max_chars: int = 4000) -> str | None:
    if value is None:
        return None
    return value[-max_chars:]


def build_demo_run_id(
    config: DemoOrchestrationConfig | None = None,
    started_at: datetime | None = None,
) -> str:
    """Build a stable run ID when the timestamp is fixed."""

    resolved = _config_or_default(config)
    timestamp = started_at or datetime.now(UTC)
    raw = f"{resolved.demo.name}|{resolved.demo.version}|{timestamp.isoformat()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"DEMO_{digest}"


def execute_demo_step(
    step: DemoStep,
    dry_run: bool = False,
    timeout_seconds: int | None = None,
) -> DemoStepResult:
    """Execute a single controlled demo step or return a planned dry-run result."""

    started_at = datetime.now(UTC)
    validate_demo_command_safety(step.command, allow_destructive=step.destructive)
    if dry_run:
        return DemoStepResult(
            name=step.name,
            command=step.command,
            started_at=started_at,
            completed_at=started_at,
            return_code=0,
            status="planned",
            metadata={"dry_run": True, "destructive": step.destructive},
        )
    try:
        completed = subprocess.run(
            step.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        completed_at = datetime.now(UTC)
        return DemoStepResult(
            name=step.name,
            command=step.command,
            started_at=started_at,
            completed_at=completed_at,
            return_code=int(completed.returncode),
            status="success" if completed.returncode == 0 else "failed",
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
            metadata={"destructive": step.destructive},
        )
    except Exception as exc:
        completed_at = datetime.now(UTC)
        return DemoStepResult(
            name=step.name,
            command=step.command,
            started_at=started_at,
            completed_at=completed_at,
            return_code=None,
            status="failed",
            stderr_tail=str(exc),
            metadata={"destructive": step.destructive, "exception": exc.__class__.__name__},
        )


def _status_counts(results: tuple[DemoStepResult, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    return counts


def run_demo_pipeline(
    config: DemoOrchestrationConfig | None = None,
    include_reset: bool = False,
    dry_run: bool = False,
    stop_on_failure: bool = True,
    timeout_seconds: int | None = None,
) -> DemoRunResult:
    """Run the configured demo pipeline with controlled command execution."""

    resolved = _config_or_default(config)
    started_at = datetime.now(UTC)
    run_id = build_demo_run_id(resolved, started_at)
    steps = build_demo_steps(resolved, include_reset=include_reset)
    results: list[DemoStepResult] = []

    for index, step in enumerate(steps):
        result = execute_demo_step(step, dry_run=dry_run, timeout_seconds=timeout_seconds)
        results.append(result)
        if result.status == "failed" and stop_on_failure:
            for skipped_step in steps[index + 1 :]:
                now = datetime.now(UTC)
                results.append(
                    DemoStepResult(
                        name=skipped_step.name,
                        command=skipped_step.command,
                        started_at=now,
                        completed_at=now,
                        status="skipped",
                        metadata={"reason": "prior_step_failed"},
                    )
                )
            break

    completed_at = datetime.now(UTC)
    result_tuple = tuple(results)
    counts = _status_counts(result_tuple)
    if dry_run:
        status = "planned"
    elif counts.get("failed", 0) > 0:
        status = "failed"
    else:
        status = "success"
    return DemoRunResult(
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        status=status,
        steps=result_tuple,
        summary={
            "step_count": len(result_tuple),
            "status_counts": counts,
            "include_reset": include_reset,
            "dry_run": dry_run,
        },
        metadata={
            "demo_name": resolved.demo.name,
            "demo_version": resolved.demo.version,
            "stop_on_failure": stop_on_failure,
        },
    )


def demo_run_result_to_dict(result: DemoRunResult) -> dict[str, object]:
    """Convert a demo run result to a JSON-serialisable dictionary."""

    if not isinstance(result, DemoRunResult):
        raise DemoStepError("result must be a DemoRunResult")
    return {
        "run_id": result.run_id,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        "status": result.status,
        "steps": [demo_step_result_to_dict(step) for step in result.steps],
        "summary": result.summary,
        "metadata": result.metadata,
    }
