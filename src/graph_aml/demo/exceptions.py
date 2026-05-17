"""Exceptions for local demo orchestration."""

from __future__ import annotations


class DemoError(Exception):
    """Base exception for demo orchestration errors."""


class DemoConfigurationError(DemoError):
    """Raised when demo configuration is invalid."""


class DemoStepError(DemoError):
    """Raised when demo step construction or execution fails."""


class DemoValidationError(DemoError):
    """Raised when demo validation checks fail."""


class DemoArtefactError(DemoError):
    """Raised when demo artefacts cannot be generated or read."""
