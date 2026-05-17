"""Tests for SQLAlchemy database connection helpers."""

from unittest.mock import Mock

import pytest
from sqlalchemy import Engine

from graph_aml.config import load_app_config
from graph_aml.database.connection import (
    build_database_url,
    create_database_engine,
    create_session_factory,
    dispose_engine,
    session_scope,
)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_build_database_url_returns_postgres_dsn() -> None:
    dsn = build_database_url(load_app_config())

    assert dsn.startswith("postgresql+psycopg2://")
    assert "graph_aml" in dsn


def test_create_database_engine_returns_engine() -> None:
    engine = create_database_engine(load_app_config())
    try:
        assert isinstance(engine, Engine)
    finally:
        engine.dispose()


def test_create_database_engine_uses_configured_pool_settings() -> None:
    config = load_app_config()
    engine = create_database_engine(config)
    try:
        assert engine.pool.size() == config.database.postgres.pool.pool_size
        assert engine.pool._max_overflow == config.database.postgres.pool.max_overflow
        assert engine.pool._timeout == config.database.postgres.pool.pool_timeout_seconds
        assert engine.pool._recycle == config.database.postgres.pool.pool_recycle_seconds
    finally:
        engine.dispose()


def test_create_session_factory_returns_callable_factory() -> None:
    engine = create_database_engine(load_app_config())
    try:
        session_factory = create_session_factory(engine)
        assert callable(session_factory)
    finally:
        engine.dispose()


def test_session_scope_commits_on_success() -> None:
    session = FakeSession()

    with session_scope(lambda: session):
        pass

    assert session.committed
    assert not session.rolled_back
    assert session.closed


def test_session_scope_rolls_back_and_closes_on_exception() -> None:
    session = FakeSession()

    with pytest.raises(RuntimeError), session_scope(lambda: session):
        raise RuntimeError("failure")

    assert not session.committed
    assert session.rolled_back
    assert session.closed


def test_dispose_engine_calls_dispose() -> None:
    engine = Mock()

    dispose_engine(engine)

    engine.dispose.assert_called_once_with()


def test_module_import_does_not_attempt_connection() -> None:
    engine = create_database_engine(load_app_config())
    try:
        assert isinstance(engine, Engine)
    finally:
        engine.dispose()
