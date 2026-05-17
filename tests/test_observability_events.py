"""Tests for structured event helpers."""

import pytest

from graph_aml.observability.context import create_run_context
from graph_aml.observability.events import LogEvent, build_event, normalise_event_dict


def test_build_event_returns_dictionary() -> None:
    event = build_event("pipeline", "Started", "ingestion")

    assert isinstance(event, dict)


def test_build_event_includes_core_fields_and_run_id() -> None:
    context = create_run_context(component="ingestion")
    event = build_event("pipeline", "Started", "ingestion", context=context)

    assert "timestamp" in event
    assert event["event_type"] == "pipeline"
    assert event["message"] == "Started"
    assert event["component"] == "ingestion"
    assert event["run_id"] == context.run_id


def test_build_event_includes_context_fields() -> None:
    context = create_run_context(
        component="ingestion",
        environment="test",
        pipeline_stage="raw_load",
    )
    event = build_event("pipeline", "Started", "ingestion", context=context)

    assert event["environment"] == "test"
    assert event["pipeline_stage"] == "raw_load"


def test_build_event_includes_metadata_kwargs() -> None:
    event = build_event(
        "pipeline",
        "Started",
        "ingestion",
        source_file="transactions.csv",
        row_count=10,
    )

    assert event["metadata"] == {"source_file": "transactions.csv", "row_count": 10}


def test_normalise_event_dict_accepts_log_event() -> None:
    event = LogEvent(event_type="pipeline", message="Started", component="ingestion")

    assert normalise_event_dict(event)["event_type"] == "pipeline"


def test_normalise_event_dict_accepts_dictionary() -> None:
    event = {"event_type": "pipeline", "message": "Started", "component": "ingestion"}

    assert normalise_event_dict(event) == event


def test_normalise_event_dict_raises_for_unsupported_input() -> None:
    with pytest.raises(TypeError):
        normalise_event_dict("not an event")
