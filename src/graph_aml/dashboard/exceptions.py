"""Dashboard exception hierarchy."""


class DashboardError(Exception):
    """Base exception for dashboard errors."""


class DashboardConfigurationError(DashboardError):
    """Raised when dashboard configuration is invalid."""


class DashboardDataError(DashboardError):
    """Raised when dashboard data cannot be read or prepared."""


class DashboardRenderError(DashboardError):
    """Raised when dashboard components cannot be rendered."""


class DashboardActionError(DashboardError):
    """Raised when dashboard actions cannot be applied."""
