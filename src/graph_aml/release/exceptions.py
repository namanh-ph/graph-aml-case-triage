"""Exceptions for release readiness and portfolio evidence tooling."""


class ReleaseReadinessError(Exception):
    """Base exception for release readiness errors."""


class ReleaseConfigurationError(ReleaseReadinessError):
    """Raised when release readiness configuration is invalid."""


class ReleaseInputError(ReleaseReadinessError):
    """Raised when release readiness inputs are missing or malformed."""


class RepositoryCheckError(ReleaseReadinessError):
    """Raised when repository checks fail unexpectedly."""


class ArtefactCheckError(ReleaseReadinessError):
    """Raised when artefact checks fail unexpectedly."""


class DocumentationCheckError(ReleaseReadinessError):
    """Raised when documentation checks fail unexpectedly."""


class DemoEvidenceError(ReleaseReadinessError):
    """Raised when demo evidence cannot be built."""


class ReleasePersistenceError(ReleaseReadinessError):
    """Raised when release outputs cannot be persisted or read back."""


class ReleaseValidationError(ReleaseReadinessError):
    """Raised when release readiness validation fails."""
