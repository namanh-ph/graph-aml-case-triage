"""Exceptions for AML case generation."""


class CaseError(Exception):
    """Base exception for case generation errors."""


class CaseConfigurationError(CaseError):
    """Raised when case generation configuration is invalid."""


class CaseInputError(CaseError):
    """Raised when case inputs are missing or malformed."""


class CaseGroupingError(CaseError):
    """Raised when alerts cannot be grouped into cases."""


class CaseGenerationError(CaseError):
    """Raised when case records cannot be generated."""


class CasePersistenceError(CaseError):
    """Raised when case persistence or readback fails."""


class CaseValidationError(CaseError):
    """Raised when case validation fails."""


class CaseRiskConfigurationError(CaseError):
    """Raised when case risk scoring configuration is invalid."""


class CaseRiskInputError(CaseError):
    """Raised when case risk scoring inputs are missing or malformed."""


class CaseRiskComputationError(CaseError):
    """Raised when case risk score computation fails."""


class CaseRiskPersistenceError(CaseError):
    """Raised when case risk score persistence or readback fails."""


class CaseRiskValidationError(CaseError):
    """Raised when case risk score validation fails."""


class CaseEvidenceConfigurationError(CaseError):
    """Raised when case evidence configuration is invalid."""


class CaseEvidenceInputError(CaseError):
    """Raised when case evidence inputs are missing or malformed."""


class CaseEvidenceBuildError(CaseError):
    """Raised when case evidence packs cannot be built."""


class CaseEvidencePersistenceError(CaseError):
    """Raised when case evidence persistence or readback fails."""


class CaseEvidenceValidationError(CaseError):
    """Raised when case evidence validation fails."""


class CaseLifecycleConfigurationError(CaseError):
    """Raised when case lifecycle configuration is invalid."""


class CaseLifecycleTransitionError(CaseError):
    """Raised when a case status transition is invalid."""


class CaseLifecyclePersistenceError(CaseError):
    """Raised when case lifecycle persistence or readback fails."""


class CaseLifecycleValidationError(CaseError):
    """Raised when lifecycle records fail validation."""
