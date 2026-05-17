"""Exceptions for AML alert schema and persistence utilities."""


class AlertError(Exception):
    """Base exception for alert schema and persistence errors."""


class AlertValidationError(AlertError):
    """Raised when an alert record fails validation."""


class AlertPersistenceError(AlertError):
    """Raised when alerts cannot be persisted to PostgreSQL."""


class AlertAuditError(AlertError):
    """Raised when alert audit events cannot be written."""


class AlertDataFrameError(AlertError):
    """Raised when alert DataFrame conversion fails."""
