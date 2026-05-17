"""Demo step construction and command safety checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from graph_aml.demo.config import DemoOrchestrationConfig, validate_demo_orchestration_config
from graph_aml.demo.exceptions import DemoStepError


@dataclass(frozen=True)
class DemoStep:
    name: str
    command: str
    description: str | None = None
    destructive: bool = False
    required: bool = True


@dataclass(frozen=True)
class DemoStepResult:
    name: str
    command: str
    started_at: datetime
    completed_at: datetime | None = None
    return_code: int | None = None
    status: str = "not_started"
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def _config_or_default(config: DemoOrchestrationConfig | None) -> DemoOrchestrationConfig:
    resolved = config or DemoOrchestrationConfig()
    validate_demo_orchestration_config(resolved)
    return resolved


def validate_demo_command_safety(
    command: str,
    config: DemoOrchestrationConfig | None = None,
    allow_destructive: bool = False,
) -> None:
    """Validate a configured command before it is planned or executed."""

    resolved = _config_or_default(config)
    clean_command = str(command).strip()
    if not clean_command:
        raise DemoStepError("demo command must be non-empty")

    lower_command = clean_command.lower()
    for pattern in resolved.safety.forbidden_demo_commands:
        if pattern.lower() in lower_command:
            raise DemoStepError(f"demo command contains forbidden pattern: {pattern}")

    for blocked in resolved.safety.blocked_without_flag:
        if blocked.lower() in lower_command and not allow_destructive:
            raise DemoStepError("destructive demo command requires explicit permission")


def build_demo_steps(
    config: DemoOrchestrationConfig | None = None,
    include_reset: bool = False,
) -> tuple[DemoStep, ...]:
    """Build ordered demo steps without executing commands."""

    resolved = _config_or_default(config)
    names: list[str] = []
    if include_reset and "db_reset" in resolved.commands.commands:
        names.append("db_reset")
    names.extend(resolved.steps.full_pipeline)

    steps: list[DemoStep] = []
    for name in names:
        command = resolved.commands.commands.get(name)
        if command is None:
            raise DemoStepError(f"missing command for demo step {name}")
        destructive = name in resolved.safety.destructive_steps
        validate_demo_command_safety(
            command,
            resolved,
            allow_destructive=include_reset and destructive,
        )
        steps.append(
            DemoStep(
                name=name,
                command=command,
                description=f"Run {name.replace('_', ' ')}",
                destructive=destructive,
                required=True,
            )
        )
    return tuple(steps)


def demo_step_result_to_dict(result: DemoStepResult) -> dict[str, object]:
    """Convert a demo step result to a JSON-serialisable dictionary."""

    return {
        "name": result.name,
        "command": result.command,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        "return_code": result.return_code,
        "status": result.status,
        "stdout_tail": result.stdout_tail,
        "stderr_tail": result.stderr_tail,
        "metadata": result.metadata,
    }
