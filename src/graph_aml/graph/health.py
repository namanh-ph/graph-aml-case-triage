"""Neo4j health check utilities."""

from __future__ import annotations

from neo4j import Driver

from graph_aml.graph.connection import get_neo4j_server_info, verify_neo4j_connectivity
from graph_aml.graph.exceptions import GraphHealthCheckError
from graph_aml.graph.execution import run_cypher_scalar


def check_neo4j_health(
    driver: Driver,
    database: str | None = None,
) -> dict[str, object]:
    """Verify Neo4j connectivity and simple query execution."""

    try:
        verify_neo4j_connectivity(driver)
        ok = run_cypher_scalar(driver, "RETURN 1 AS ok", database=database)
        if ok != 1:
            raise GraphHealthCheckError(f"Neo4j health query returned {ok!r}")
        return {
            "status": "ok",
            "database": database,
            "connectivity_verified": True,
            "query_ok": True,
            "server_info": get_neo4j_server_info(driver),
        }
    except GraphHealthCheckError:
        raise
    except Exception as exc:
        raise GraphHealthCheckError(f"Neo4j health check failed: {exc}") from exc


def check_neo4j_database_access(
    driver: Driver,
    database: str | None = None,
) -> dict[str, object]:
    """Check simple Cypher query access to a Neo4j database."""

    try:
        ok = run_cypher_scalar(driver, "RETURN 1 AS ok", database=database)
        if ok != 1:
            raise GraphHealthCheckError(f"Neo4j database access returned {ok!r}")
        return {
            "status": "ok",
            "database": database,
            "query_ok": True,
        }
    except GraphHealthCheckError:
        raise
    except Exception as exc:
        raise GraphHealthCheckError(f"Neo4j database access check failed: {exc}") from exc


def collect_neo4j_health_summary(
    driver: Driver,
    database: str | None = None,
) -> dict[str, object]:
    """Collect a compact Neo4j health summary."""

    health = check_neo4j_health(driver, database)
    access = check_neo4j_database_access(driver, database)
    return {
        "status": "ok",
        "database": database,
        "connectivity_verified": health["connectivity_verified"],
        "query_ok": bool(health["query_ok"]) and bool(access["query_ok"]),
        "server_info": health.get("server_info", {}),
    }
