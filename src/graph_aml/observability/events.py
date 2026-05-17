"""Structured event helpers for project logging."""

from dataclasses import asdict, dataclass, field
from typing import Any

from graph_aml.observability.context import RunContext, utc_now_iso


@dataclass(frozen=True)
class LogEvent:
    """Structured event payload for log records."""

    event_type: str
    message: str
    component: str
    run_id: str | None = None
    pipeline_stage: str | None = None
    status: str | None = None
    severity: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    metric_name: str | None = None
    metric_value: int | float | str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


EVENT_FIELD_NAMES = {
    "run_id",
    "environment",
    "pipeline_stage",
    "model_run_id",
    "case_id",
    "alert_id",
    "account_id",
    "status",
    "severity",
    "entity_type",
    "entity_id",
    "metric_name",
    "metric_value",
}


def build_event(
    event_type: str,
    message: str,
    component: str,
    context: RunContext | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a structured event dictionary for logging extra fields."""

    event: dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "event_type": event_type,
        "message": message,
        "component": component,
    }
    metadata: dict[str, Any] = {}

    if context is not None:
        event["run_id"] = context.run_id
        event["environment"] = context.environment
        event["pipeline_stage"] = context.pipeline_stage
        for key in ("model_run_id", "case_id", "alert_id", "account_id"):
            value = getattr(context, key)
            if value is not None:
                event[key] = value
        metadata.update(context.metadata)

    explicit_metadata = kwargs.pop("metadata", None)
    if isinstance(explicit_metadata, dict):
        metadata.update(explicit_metadata)
    elif explicit_metadata is not None:
        metadata["metadata"] = explicit_metadata

    for key, value in kwargs.items():
        if key in EVENT_FIELD_NAMES:
            event[key] = value
        else:
            metadata[key] = value

    if metadata:
        event["metadata"] = dict(metadata)

    return event


def normalise_event_dict(event: LogEvent | dict[str, Any]) -> dict[str, Any]:
    """Convert a supported structured event object to a dictionary."""

    if isinstance(event, LogEvent):
        return asdict(event)
    if isinstance(event, dict):
        return dict(event)
    raise TypeError(f"Unsupported event type: {type(event).__name__}")
