"""Tests for logging configuration and structured event wrappers."""

import json
import logging
from pathlib import Path

import pytest

from graph_aml.config import load_app_config
from graph_aml.observability import create_run_context
from graph_aml.observability.logging_config import (
    configure_logging,
    configure_logging_from_config,
    get_logger,
    log_case_event,
    log_event,
    log_model_event,
    log_pipeline_event,
    log_rule_event,
    log_validation_event,
)


def flush_handlers(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        handler.flush()


def read_json_lines(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_configure_logging_returns_logger(tmp_path: Path) -> None:
    logger = configure_logging(log_dir=tmp_path, enable_console=False, force=True)

    assert isinstance(logger, logging.Logger)
    assert logger.name == "graph_aml"


def test_file_logging_creates_requested_log_directory(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"

    configure_logging(log_dir=log_dir, enable_console=False, force=True)

    assert log_dir.is_dir()


def test_structured_event_is_written_to_log_file(tmp_path: Path) -> None:
    log_file_name = "events.log"
    logger = configure_logging(
        log_dir=tmp_path,
        log_file_name=log_file_name,
        enable_console=False,
        force=True,
    )

    log_event(logger, "INFO", "pipeline", "Started", "ingestion", row_count=12)
    flush_handlers(logger)

    payload = read_json_lines(tmp_path / log_file_name)[0]
    assert payload["event"]["event_type"] == "pipeline"
    assert payload["event"]["metadata"]["row_count"] == 12


def test_repeated_calls_do_not_duplicate_handlers_when_force_false(tmp_path: Path) -> None:
    logger = configure_logging(log_dir=tmp_path, enable_file=False, force=True)
    handler_count = len(logger.handlers)

    same_logger = configure_logging(log_dir=tmp_path, enable_file=False, force=False)

    assert same_logger is logger
    assert len(logger.handlers) == handler_count


def test_force_true_resets_handlers(tmp_path: Path) -> None:
    logger = configure_logging(log_dir=tmp_path, enable_file=True, force=True)
    first_handlers = list(logger.handlers)

    configure_logging(log_dir=tmp_path / "other", enable_console=False, force=True)

    assert logger.handlers != first_handlers
    assert len(logger.handlers) == 1


def test_get_logger_returns_requested_name() -> None:
    logger = get_logger("graph_aml.pipeline")

    assert logger.name == "graph_aml.pipeline"


def test_log_event_supports_allowed_levels(tmp_path: Path) -> None:
    logger = configure_logging(
        level="DEBUG",
        log_dir=tmp_path,
        log_file_name="levels.log",
        enable_console=False,
        force=True,
    )

    for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        log_event(logger, level, "pipeline", f"{level} event", "ingestion")

    flush_handlers(logger)
    assert len(read_json_lines(tmp_path / "levels.log")) == 5


def test_log_event_raises_for_invalid_level(tmp_path: Path) -> None:
    logger = configure_logging(log_dir=tmp_path, enable_console=False, force=True)

    with pytest.raises(ValueError):
        log_event(logger, "NOTICE", "pipeline", "Started", "ingestion")


def test_convenience_wrappers_produce_expected_event_types(tmp_path: Path) -> None:
    logger = configure_logging(
        log_dir=tmp_path,
        log_file_name="wrappers.log",
        enable_console=False,
        force=True,
    )
    context = create_run_context(component="ingestion", pipeline_stage="raw_load")

    log_pipeline_event(logger, "Pipeline started", "ingestion", "raw_load", "started", context)
    log_validation_event(logger, "Validation passed", "passed", context)
    log_rule_event(logger, "Rule executed", "structuring", "completed", context)
    log_model_event(logger, "Model trained", "completed", context)
    log_case_event(logger, "Case created", "CA001", "created", context)
    flush_handlers(logger)

    payloads = read_json_lines(tmp_path / "wrappers.log")
    event_types = [payload["event"]["event_type"] for payload in payloads]
    assert event_types == ["pipeline", "validation", "rule_execution", "model", "case"]


def test_configure_logging_from_config_returns_configured_logger(tmp_path: Path) -> None:
    configure_logging(log_dir=tmp_path, enable_console=False, enable_file=False, force=True)
    config = load_app_config()
    config.paths.paths.logs_dir = str(tmp_path)

    logger = configure_logging_from_config(config)

    assert logger.name == "graph_aml"
    assert tmp_path.is_dir()
