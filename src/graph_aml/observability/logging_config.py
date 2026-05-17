"""Logging configuration helpers for structured project events."""

import logging
from pathlib import Path
from typing import Any

from graph_aml.config.schemas import AppConfig
from graph_aml.observability.context import RunContext
from graph_aml.observability.events import build_event
from graph_aml.observability.formatters import StructuredLogFormatter

LOGGER_NAME = "graph_aml"
SUPPORTED_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _normalise_level(level: str) -> int:
    normalised_level = level.upper()
    if normalised_level not in SUPPORTED_LEVELS:
        raise ValueError(f"Unsupported log level: {level}")
    return int(getattr(logging, normalised_level))


def _clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def configure_logging(
    level: str = "INFO",
    log_dir: Path | str = "logs",
    log_file_name: str = "graph_aml.log",
    enable_console: bool = True,
    enable_file: bool = True,
    force: bool = False,
) -> logging.Logger:
    """Configure and return the root project logger."""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(_normalise_level(level))
    logger.propagate = False

    if force:
        _clear_handlers(logger)
    elif logger.handlers:
        return logger

    formatter = StructuredLogFormatter()

    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logger.level)
        logger.addHandler(console_handler)

    if enable_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path / log_file_name, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logger.level)
        logger.addHandler(file_handler)

    return logger


def configure_logging_from_config(config: AppConfig) -> logging.Logger:
    """Configure logging using typed application configuration."""

    return configure_logging(log_dir=config.paths.paths.logs_dir, level="INFO")


def get_logger(name: str) -> logging.Logger:
    """Return a standard library logger by name."""

    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    level: str,
    event_type: str,
    message: str,
    component: str,
    context: RunContext | None = None,
    **kwargs: Any,
) -> None:
    """Build and emit one structured log event."""

    level_number = _normalise_level(level)
    event = build_event(
        event_type=event_type,
        message=message,
        component=component,
        context=context,
        **kwargs,
    )
    logger.log(level_number, message, extra={"event": event})


def log_pipeline_event(
    logger: logging.Logger,
    message: str,
    component: str,
    stage: str,
    status: str,
    context: RunContext | None = None,
    **metadata: Any,
) -> None:
    """Log a pipeline-stage event."""

    log_event(
        logger=logger,
        level="INFO",
        event_type="pipeline",
        message=message,
        component=component,
        context=context,
        pipeline_stage=stage,
        status=status,
        **metadata,
    )


def log_validation_event(
    logger: logging.Logger,
    message: str,
    status: str,
    context: RunContext | None = None,
    **metadata: Any,
) -> None:
    """Log a data validation event."""

    log_event(
        logger=logger,
        level="INFO",
        event_type="validation",
        message=message,
        component="validation",
        context=context,
        status=status,
        **metadata,
    )


def log_rule_event(
    logger: logging.Logger,
    message: str,
    rule_name: str,
    status: str,
    context: RunContext | None = None,
    **metadata: Any,
) -> None:
    """Log an AML rule execution event."""

    log_event(
        logger=logger,
        level="INFO",
        event_type="rule_execution",
        message=message,
        component="rules",
        context=context,
        status=status,
        rule_name=rule_name,
        **metadata,
    )


def log_model_event(
    logger: logging.Logger,
    message: str,
    status: str,
    context: RunContext | None = None,
    **metadata: Any,
) -> None:
    """Log a model workflow event."""

    log_event(
        logger=logger,
        level="INFO",
        event_type="model",
        message=message,
        component="models",
        context=context,
        status=status,
        **metadata,
    )


def log_case_event(
    logger: logging.Logger,
    message: str,
    case_id: str,
    status: str,
    context: RunContext | None = None,
    **metadata: Any,
) -> None:
    """Log a case lifecycle event."""

    log_event(
        logger=logger,
        level="INFO",
        event_type="case",
        message=message,
        component="cases",
        context=context,
        case_id=case_id,
        entity_type="case",
        entity_id=case_id,
        status=status,
        **metadata,
    )
