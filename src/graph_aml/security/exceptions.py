"""Exceptions for security controls and privacy safeguards."""


class SecurityControlError(Exception):
    """Base exception for security control errors."""


class SecurityConfigurationError(SecurityControlError):
    """Raised when security configuration is invalid."""


class SensitiveFieldError(SecurityControlError):
    """Raised when sensitive field inventory cannot be built or validated."""


class DataMaskingError(SecurityControlError):
    """Raised when data masking fails."""


class PermissionPolicyError(SecurityControlError):
    """Raised when permission policy checks fail."""


class ExportControlError(SecurityControlError):
    """Raised when export control checks fail."""


class SecretsScanError(SecurityControlError):
    """Raised when local secrets scanning fails."""


class AuditIntegrityError(SecurityControlError):
    """Raised when audit integrity checks fail."""


class SecurityPersistenceError(SecurityControlError):
    """Raised when security controls cannot be persisted or read back."""
