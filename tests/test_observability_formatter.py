"""Tests for the structured JSON log formatter."""

import json
import logging
import sys
from pathlib import Path
from typing import Any

from graph_aml.observability.formatters import StructuredLogFormatter


def make_record(
    message: str = "Started",
    event: dict[str, Any] | None = None,
    exc_info: tuple[type[BaseException], BaseException, Any] | None = None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="graph_aml.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg=message,
        args=(),
        exc_info=exc_info,
        func="test_function",
    )
    if event is not None:
        record.event = event
    return record


def test_structured_log_formatter_returns_valid_json() -> None:
    formatted = StructuredLogFormatter().format(make_record())

    assert isinstance(json.loads(formatted), dict)


def test_structured_log_formatter_includes_base_fields() -> None:
    payload = json.loads(StructuredLogFormatter().format(make_record()))

    assert {
        "timestamp",
        "level",
        "logger",
        "message",
        "module",
        "function",
        "line",
    } <= set(payload)


def test_structured_event_fields_are_nested_under_event() -> None:
    event = {"event_type": "pipeline", "message": "Started", "component": "ingestion"}
    payload = json.loads(StructuredLogFormatter().format(make_record(event=event)))

    assert payload["event"]["event_type"] == "pipeline"


def test_exception_information_is_included() -> None:
    try:
        raise ValueError("bad value")
    except ValueError:
        payload = json.loads(StructuredLogFormatter().format(make_record(exc_info=sys.exc_info())))

    assert payload["exception"]["type"] == "ValueError"
    assert payload["exception"]["message"] == "bad value"
    assert "traceback" in payload["exception"]


def test_non_json_native_values_are_serialised() -> None:
    event = {
        "event_type": "pipeline",
        "message": "Started",
        "component": "ingestion",
        "metadata": {"path": Path("transactions.csv")},
    }
    payload = json.loads(StructuredLogFormatter().format(make_record(event=event)))

    assert payload["event"]["metadata"]["path"] == "transactions.csv"
