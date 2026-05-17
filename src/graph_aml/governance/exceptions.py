"""Exceptions for governance inventory workflows."""

from __future__ import annotations


class GovernanceInventoryError(Exception):
    """Base exception for governance inventory errors."""


class GovernanceInventoryConfigurationError(GovernanceInventoryError):
    """Raised when governance inventory configuration is invalid."""


class GovernanceInventoryInputError(GovernanceInventoryError):
    """Raised when governance inventory inputs are missing or malformed."""


class LineageBuildError(GovernanceInventoryError):
    """Raised when lineage records cannot be built."""


class ArtefactRegistryError(GovernanceInventoryError):
    """Raised when artefact registry records cannot be built."""


class GovernanceInventoryPersistenceError(GovernanceInventoryError):
    """Raised when governance inventory persistence or readback fails."""


class GovernanceInventoryValidationError(GovernanceInventoryError):
    """Raised when governance inventory validation fails."""
