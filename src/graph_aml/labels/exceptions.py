"""Exceptions for analyst feedback labels."""

from __future__ import annotations


class LabelError(Exception):
    """Base exception for analyst feedback label errors."""


class LabelConfigurationError(LabelError):
    """Raised when label configuration is invalid."""


class LabelInputError(LabelError):
    """Raised when label inputs are missing or malformed."""


class LabelMappingError(LabelError):
    """Raised when analyst decisions cannot be mapped to labels."""


class LabelDatasetError(LabelError):
    """Raised when supervised label datasets cannot be built."""


class LabelPersistenceError(LabelError):
    """Raised when labels cannot be persisted or read back."""


class LabelValidationError(LabelError):
    """Raised when label quality checks fail."""
