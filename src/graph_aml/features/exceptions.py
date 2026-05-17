"""Exceptions for account feature engineering."""


class FeatureEngineeringError(Exception):
    """Base exception for feature engineering errors."""


class AccountFeatureError(FeatureEngineeringError):
    """Raised when account-level features cannot be computed."""


class FeatureInputError(FeatureEngineeringError):
    """Raised when feature input data is missing or invalid."""


class FeatureArtefactError(FeatureEngineeringError):
    """Raised when feature artefacts cannot be written."""


class StagedFeatureReadError(FeatureEngineeringError):
    """Raised when staged PostgreSQL data cannot be read for feature engineering."""


class FeaturePersistenceError(FeatureEngineeringError):
    """Raised when account features cannot be persisted to PostgreSQL."""


class FeatureAuditError(FeatureEngineeringError):
    """Raised when feature persistence audit events cannot be written."""


class MartFeatureReadError(FeatureEngineeringError):
    """Raised when persisted mart features cannot be read."""
