"""Exceptions for AML rule execution."""


class RuleError(Exception):
    """Base exception for AML rule errors."""


class RuleConfigurationError(RuleError):
    """Raised when rule configuration is invalid."""


class RuleRegistryError(RuleError):
    """Raised when a rule cannot be found or registered."""


class RuleEngineError(RuleError):
    """Raised when the unified AML rule engine cannot complete execution."""


class RuleEngineConfigurationError(RuleConfigurationError):
    """Raised when unified rule engine configuration is invalid."""


class RuleDocumentationError(RuleError):
    """Raised when AML rule documentation cannot be generated or validated."""


class RuleInputError(RuleError):
    """Raised when rule input data is missing or invalid."""


class RuleExecutionError(RuleError):
    """Raised when a rule cannot be executed."""


class RuleAuditError(RuleError):
    """Raised when rule execution audit events cannot be written."""


class RuleDataReadError(RuleError):
    """Raised when staged data cannot be read for rule execution."""
