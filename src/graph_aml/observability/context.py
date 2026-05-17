"""Run context helpers for structured project logs."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class RunContext:
    """Context fields shared across related runtime log events."""

    run_id: str
    component: str
    environment: str = "local"
    pipeline_stage: str | None = None
    model_run_id: str | None = None
    case_id: str | None = None
    alert_id: str | None = None
    account_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def create_run_context(
    component: str,
    environment: str = "local",
    pipeline_stage: str | None = None,
    **metadata: Any,
) -> RunContext:
    """Create a new immutable run context with a unique run identifier."""

    return RunContext(
        run_id=str(uuid4()),
        component=component,
        environment=environment,
        pipeline_stage=pipeline_stage,
        metadata=dict(metadata),
    )


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return datetime.now(UTC).isoformat()
