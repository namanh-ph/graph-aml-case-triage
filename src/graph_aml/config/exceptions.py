"""Custom exceptions for configuration loading and validation."""


class ConfigError(Exception):
    """Base exception for configuration errors."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when a required configuration file is missing."""


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""


class EnvironmentVariableError(ConfigError):
    """Raised when a required environment variable cannot be resolved."""
