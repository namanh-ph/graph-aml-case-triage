"""CLI for local PostgreSQL database utilities."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.database import (  # noqa: E402
    DatabaseError,
    check_database_connection,
    create_database_engine,
    delete_smoke_seed_data,
    dispose_engine,
    get_database_server_version,
    get_existing_schemas,
    get_existing_tables,
    initialise_database,
    reset_database,
    seed_smoke_data,
)
from graph_aml.observability import (  # noqa: E402
    configure_logging_from_config,
    create_run_context,
    get_logger,
    log_pipeline_event,
)


def run_with_engine(command: Callable[[object], int]) -> int:
    """Create an engine for one CLI command and dispose it before exit."""

    config = load_app_config()
    configure_logging_from_config(config)
    engine = create_database_engine(config)
    try:
        return command(engine)
    except DatabaseError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def command_check(engine: object) -> int:
    """Check database connectivity."""

    logger = get_logger("graph_aml.database.cli")
    context = create_run_context(component="database", pipeline_stage="db_check")
    log_pipeline_event(
        logger,
        "Database connection check started",
        "database",
        "db_check",
        "started",
        context,
    )
    check_database_connection(engine)  # type: ignore[arg-type]
    log_pipeline_event(
        logger,
        "Database connection check completed",
        "database",
        "db_check",
        "completed",
        context,
    )
    print("Database connection check: OK")
    return 0


def command_version(engine: object) -> int:
    """Print database server version."""

    print(get_database_server_version(engine))  # type: ignore[arg-type]
    return 0


def command_list_schemas(engine: object) -> int:
    """Print existing schemas."""

    for schema_name in get_existing_schemas(engine):  # type: ignore[arg-type]
        print(schema_name)
    return 0


def command_list_tables(engine: object, schema: str) -> int:
    """Print existing tables for one schema."""

    for table_name in get_existing_tables(engine, schema):  # type: ignore[arg-type]
        print(table_name)
    return 0


def command_init(engine: object) -> int:
    """Initialise schemas and core tables."""

    logger = get_logger("graph_aml.database.cli")
    context = create_run_context(component="database", pipeline_stage="db_init")
    log_pipeline_event(
        logger,
        "Schema initialisation started",
        "database",
        "db_init",
        "started",
        context,
    )
    summary = initialise_database(engine)  # type: ignore[arg-type]
    log_pipeline_event(
        logger,
        "Table initialisation completed",
        "database",
        "db_init",
        "completed",
        context,
        **summary,
    )
    print(f"schema_statements_executed={summary['schema_statements_executed']}")
    print(f"table_statements_executed={summary['table_statements_executed']}")
    return 0


def command_reset(engine: object) -> int:
    """Reset project schemas and core tables."""

    logger = get_logger("graph_aml.database.cli")
    context = create_run_context(component="database", pipeline_stage="db_reset")
    log_pipeline_event(
        logger,
        "Database reset started",
        "database",
        "db_reset",
        "started",
        context,
    )
    summary = reset_database(engine, confirm=True)  # type: ignore[arg-type]
    log_pipeline_event(
        logger,
        "Database reset completed",
        "database",
        "db_reset",
        "completed",
        context,
        **summary,
    )
    for key, value in summary.items():
        print(f"{key}={value}")
    return 0


def command_seed_smoke(engine: object) -> int:
    """Insert deterministic smoke seed data."""

    logger = get_logger("graph_aml.database.cli")
    context = create_run_context(component="database", pipeline_stage="db_seed_smoke")
    log_pipeline_event(
        logger,
        "Smoke seed started",
        "database",
        "db_seed_smoke",
        "started",
        context,
    )
    summary = seed_smoke_data(engine)  # type: ignore[arg-type]
    log_pipeline_event(
        logger,
        "Smoke seed completed",
        "database",
        "db_seed_smoke",
        "completed",
        context,
        **summary,
    )
    for key, value in summary.items():
        print(f"{key}={value}")
    return 0


def command_delete_smoke_seed(engine: object) -> int:
    """Delete deterministic smoke seed data."""

    logger = get_logger("graph_aml.database.cli")
    context = create_run_context(component="database", pipeline_stage="db_delete_smoke_seed")
    log_pipeline_event(
        logger,
        "Smoke seed deletion started",
        "database",
        "db_delete_smoke_seed",
        "started",
        context,
    )
    summary = delete_smoke_seed_data(engine, confirm=True)  # type: ignore[arg-type]
    log_pipeline_event(
        logger,
        "Smoke seed deletion completed",
        "database",
        "db_delete_smoke_seed",
        "completed",
        context,
        **summary,
    )
    for key, value in summary.items():
        print(f"{key}={value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the database CLI parser."""

    parser = argparse.ArgumentParser(description="Local PostgreSQL database utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Check PostgreSQL connectivity.")
    subparsers.add_parser("version", help="Print PostgreSQL server version.")
    subparsers.add_parser("list-schemas", help="List existing database schemas.")
    list_tables = subparsers.add_parser("list-tables", help="List tables in a schema.")
    list_tables.add_argument("--schema", required=True, help="Schema name to inspect.")
    subparsers.add_parser("init", help="Create schemas and core tables.")
    reset = subparsers.add_parser("reset", help="Drop and recreate project schemas and tables.")
    reset.add_argument("--yes", action="store_true", help="Confirm destructive database reset.")
    subparsers.add_parser("seed-smoke", help="Insert deterministic smoke seed data.")
    delete_seed = subparsers.add_parser(
        "delete-smoke-seed",
        help="Delete deterministic smoke seed data.",
    )
    delete_seed.add_argument("--yes", action="store_true", help="Confirm smoke seed deletion.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the database CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "check":
        return run_with_engine(command_check)
    if args.command == "version":
        return run_with_engine(command_version)
    if args.command == "list-schemas":
        return run_with_engine(command_list_schemas)
    if args.command == "list-tables":
        return run_with_engine(lambda engine: command_list_tables(engine, args.schema))
    if args.command == "init":
        return run_with_engine(command_init)
    if args.command == "reset":
        if not args.yes:
            print(
                "Database reset refused. Re-run with --yes to confirm destructive reset.",
                file=sys.stderr,
            )
            return 2
        return run_with_engine(command_reset)
    if args.command == "seed-smoke":
        return run_with_engine(command_seed_smoke)
    if args.command == "delete-smoke-seed":
        if not args.yes:
            print(
                "Smoke seed deletion refused. Re-run with --yes to confirm deletion.",
                file=sys.stderr,
            )
            return 2
        return run_with_engine(command_delete_smoke_seed)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
