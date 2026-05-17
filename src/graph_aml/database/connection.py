"""SQLAlchemy connection and session helpers."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from graph_aml.config import AppConfig, build_postgres_dsn, load_app_config


def build_database_url(config: AppConfig | None = None) -> str:
    """Build the PostgreSQL SQLAlchemy database URL from typed config."""

    app_config = load_app_config() if config is None else config
    return build_postgres_dsn(app_config)


def create_database_engine(
    config: AppConfig | None = None,
    echo: bool = False,
    pool_pre_ping: bool = True,
) -> Engine:
    """Create a SQLAlchemy engine without opening a connection immediately."""

    app_config = load_app_config() if config is None else config
    pool = app_config.database.postgres.pool
    return create_engine(
        build_database_url(app_config),
        echo=echo,
        max_overflow=pool.max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool.pool_recycle_seconds,
        pool_size=pool.pool_size,
        pool_timeout=pool.pool_timeout_seconds,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory bound to an engine."""

    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional session scope."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine(engine: Engine) -> None:
    """Dispose an engine and its connection pool."""

    engine.dispose()
