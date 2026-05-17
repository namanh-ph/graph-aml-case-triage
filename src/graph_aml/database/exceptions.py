"""Custom exceptions for database utilities."""


class DatabaseError(Exception):
    """Base exception for database utility errors."""


class DatabaseConnectionError(DatabaseError):
    """Raised when a database connection cannot be established."""


class DatabaseExecutionError(DatabaseError):
    """Raised when SQL execution fails."""


class DatabaseInitialisationError(DatabaseError):
    """Raised when database initialisation fails."""


class DatabaseResetRefusedError(DatabaseError):
    """Raised when a destructive database reset is requested without explicit confirmation."""


class DatabaseSeedError(DatabaseError):
    """Raised when deterministic seed data cannot be inserted."""
