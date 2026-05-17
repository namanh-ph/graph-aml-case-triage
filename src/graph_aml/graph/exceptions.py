"""Exceptions for Neo4j graph utility operations."""


class GraphError(Exception):
    """Base exception for Neo4j graph utility errors."""


class GraphConfigurationError(GraphError):
    """Raised when Neo4j configuration is missing or invalid."""


class GraphConnectionError(GraphError):
    """Raised when Neo4j driver creation or connectivity fails."""


class GraphExecutionError(GraphError):
    """Raised when Cypher execution fails."""


class GraphHealthCheckError(GraphError):
    """Raised when Neo4j health checks fail."""


class GraphConstraintError(GraphError):
    """Raised when Neo4j constraint operations fail."""


class GraphSchemaError(GraphError):
    """Raised when graph schema metadata or Cypher definitions are invalid."""


class GraphMappingError(GraphError):
    """Raised when relational data cannot be mapped into graph rows."""


class GraphLoadError(GraphError):
    """Raised when graph loading cannot complete."""


class GraphReconciliationError(GraphError):
    """Raised when graph load reconciliation fails."""


class GraphAnalyticsConfigurationError(GraphError):
    """Raised when graph analytics configuration is invalid."""


class GraphProjectionError(GraphError):
    """Raised when Neo4j graph data cannot be projected for analytics."""


class GraphAnalyticsError(GraphError):
    """Raised when graph analytics feature computation fails."""


class GraphFeaturePersistenceError(GraphError):
    """Raised when graph feature persistence fails."""


class GraphFeatureValidationError(GraphError):
    """Raised when graph feature validation fails."""
