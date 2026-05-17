"""Exceptions for raw data ingestion utilities."""


class IngestionError(Exception):
    """Base exception for ingestion errors."""


class IngestionSourceError(IngestionError):
    """Raised when an ingestion source is missing, invalid, or unsupported."""


class RawIngestionError(IngestionError):
    """Raised when raw data ingestion fails."""


class IngestionAuditError(IngestionError):
    """Raised when ingestion audit event writing fails."""
