"""Exceptions for composite account risk scoring."""


class ScoringError(Exception):
    """Base exception for account risk scoring errors."""


class ScoringConfigurationError(ScoringError):
    """Raised when scoring configuration is invalid."""


class ScoringInputError(ScoringError):
    """Raised when scoring inputs are missing or malformed."""


class ScoringComputationError(ScoringError):
    """Raised when risk score computation fails."""


class ScoringPersistenceError(ScoringError):
    """Raised when risk score persistence or readback fails."""


class ScoringValidationError(ScoringError):
    """Raised when risk score validation fails."""
