"""Exceptions for model training, scoring, and persistence utilities."""


class ModelError(Exception):
    """Base exception for model utility errors."""


class ModelConfigurationError(ModelError):
    """Raised when model configuration is invalid."""


class ModelFeatureInputError(ModelError):
    """Raised when model feature inputs are missing or malformed."""


class ModelTrainingError(ModelError):
    """Raised when model training or scoring fails."""


class ModelPersistenceError(ModelError):
    """Raised when model persistence or readback fails."""


class ModelValidationError(ModelError):
    """Raised when model validation checks fail."""
