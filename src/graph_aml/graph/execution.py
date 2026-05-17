"""Parameterized Cypher execution helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, cast

from neo4j import Driver

from graph_aml.graph.exceptions import GraphExecutionError


def run_cypher_read(
    driver: Driver,
    query: str,
    parameters: dict[str, object] | None = None,
    database: str | None = None,
) -> list[dict[str, object]]:
    """Run a read-only Cypher query and return plain dictionaries."""

    return _run_cypher(driver, query, parameters, database, mode="read")


def run_cypher_write(
    driver: Driver,
    query: str,
    parameters: dict[str, object] | None = None,
    database: str | None = None,
) -> list[dict[str, object]]:
    """Run a write Cypher query and return plain dictionaries."""

    return _run_cypher(driver, query, parameters, database, mode="write")


def run_cypher_scalar(
    driver: Driver,
    query: str,
    parameters: dict[str, object] | None = None,
    database: str | None = None,
) -> object | None:
    """Return the first value from the first Cypher result row."""

    rows = run_cypher_read(driver, query, parameters, database)
    if not rows:
        return None
    first_row = rows[0]
    if not first_row:
        return None
    return next(iter(first_row.values()))


def run_cypher_batch(
    driver: Driver,
    query: str,
    rows: list[dict[str, object]],
    batch_size: int = 1000,
    database: str | None = None,
) -> int:
    """Execute a write query repeatedly with batches supplied as the `rows` parameter."""

    _validate_query(query)
    if batch_size <= 0:
        raise GraphExecutionError("Cypher batch size must be positive")
    if not rows:
        return 0
    attempted = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        run_cypher_write(driver, query, {"rows": batch}, database)
        attempted += len(batch)
    return attempted


def _run_cypher(
    driver: Driver,
    query: str,
    parameters: dict[str, object] | None,
    database: str | None,
    mode: str,
) -> list[dict[str, object]]:
    _validate_query(query)
    try:
        session = driver.session(database=database) if database else driver.session()
        with session:
            runner = session.execute_read if mode == "read" else session.execute_write
            return list(runner(_execute_query, query, parameters or {}))
    except GraphExecutionError:
        raise
    except Exception as exc:
        raise GraphExecutionError(f"Cypher {mode} execution failed: {exc}") from exc


def _execute_query(
    tx: Any,
    query: str,
    parameters: dict[str, object],
) -> list[dict[str, object]]:
    result = tx.run(query, parameters)
    return [_record_to_dict(record) for record in result]


def _record_to_dict(record: object) -> dict[str, object]:
    data: Callable[[], dict[str, object]] | None = getattr(record, "data", None)
    if callable(data):
        return dict(data())
    if isinstance(record, dict):
        return dict(record)
    if isinstance(record, Mapping):
        return {str(key): value for key, value in record.items()}
    return dict(cast(Iterable[tuple[str, object]], record))


def _validate_query(query: str) -> None:
    if not str(query).strip():
        raise GraphExecutionError("Cypher query must be non-empty")
