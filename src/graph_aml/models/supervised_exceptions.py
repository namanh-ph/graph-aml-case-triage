"""Exceptions for supervised AML model training."""


class SupervisedModelError(Exception):
    """Base exception for supervised AML model errors."""


class SupervisedModelConfigurationError(SupervisedModelError):
    """Raised when supervised model configuration is invalid."""


class SupervisedModelInputError(SupervisedModelError):
    """Raised when supervised model inputs are missing or malformed."""


class SupervisedFeatureError(SupervisedModelError):
    """Raised when supervised feature matrices cannot be built."""


class SupervisedTrainingError(SupervisedModelError):
    """Raised when supervised model training fails."""


class SupervisedScoringError(SupervisedModelError):
    """Raised when supervised model scoring fails."""


class SupervisedPersistenceError(SupervisedModelError):
    """Raised when supervised model persistence or readback fails."""


class SupervisedValidationError(SupervisedModelError):
    """Raised when supervised model validation fails."""
