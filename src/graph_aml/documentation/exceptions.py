"""Exceptions for generated documentation artefacts."""


class DocumentationError(Exception):
    """Base exception for documentation artefact errors."""


class DataDictionaryError(DocumentationError):
    """Raised when the data dictionary cannot be generated."""


class DocumentationWriteError(DocumentationError):
    """Raised when a documentation artefact cannot be written."""
