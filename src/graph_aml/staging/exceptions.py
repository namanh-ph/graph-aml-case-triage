"""Exceptions for raw-to-staging transformations."""


class StagingError(Exception):
    """Base exception for staging transformation errors."""


class RawExtractionError(StagingError):
    """Raised when raw records cannot be extracted."""


class StagingTransformationError(StagingError):
    """Raised when raw records cannot be transformed into staging records."""


class StagingLoadError(StagingError):
    """Raised when staging records cannot be loaded into PostgreSQL."""


class StagingAuditError(StagingError):
    """Raised when staging audit event writing fails."""
