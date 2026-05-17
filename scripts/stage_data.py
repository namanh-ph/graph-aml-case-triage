"""CLI for transforming PostgreSQL raw records into staging tables."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.database import create_database_engine, dispose_engine  # noqa: E402
from graph_aml.observability import (  # noqa: E402
    configure_logging,
    create_run_context,
    get_logger,
    log_pipeline_event,
)
from graph_aml.staging import StagingError  # noqa: E402
from graph_aml.staging.audit import write_staging_audit_event  # noqa: E402
from graph_aml.staging.extract import read_raw_dataset  # noqa: E402
from graph_aml.staging.load import load_staging_dataset  # noqa: E402
from graph_aml.staging.transform import (  # noqa: E402
    transform_raw_dataset,
    validate_staging_dataset,
)


def _configure_logging() -> None:
    config = load_app_config()
    configure_logging(
        log_dir=config.paths.paths.logs_dir,
        enable_console=False,
        enable_file=True,
    )


def _print_row_counts(row_counts: dict[str, int]) -> None:
    for table_name in sorted(row_counts):
        print(f"{table_name}={row_counts[table_name]}")


def command_stage(args: argparse.Namespace) -> int:
    """Run raw-to-staging transformations."""

    _configure_logging()
    logger = get_logger("graph_aml.staging.cli")
    context = create_run_context(component="staging", pipeline_stage="staging_load")
    engine = create_database_engine()
    try:
        log_pipeline_event(
            logger,
            "Staging transformation started",
            "staging",
            "staging_load",
            "started",
            context,
            limit=args.limit,
            validate=not args.no_validate,
        )
        raw_dataset = read_raw_dataset(engine, limit=args.limit)
        log_pipeline_event(
            logger,
            "Raw extraction completed",
            "staging",
            "staging_load",
            "completed",
            context,
            table_count=len(raw_dataset),
        )
        staging_dataset = transform_raw_dataset(raw_dataset)
        if not args.no_validate:
            validate_staging_dataset(staging_dataset)
        log_pipeline_event(
            logger,
            "Staging transformation completed",
            "staging",
            "staging_load",
            "completed",
            context,
            validate=not args.no_validate,
        )
        row_counts = load_staging_dataset(engine, staging_dataset)
        log_pipeline_event(
            logger,
            "Staging load completed",
            "staging",
            "staging_load",
            "completed",
            context,
            row_counts=row_counts,
        )
        if not args.no_audit:
            write_staging_audit_event(
                engine,
                row_counts=row_counts,
                status="completed",
                metadata={"limit": args.limit, "validate": not args.no_validate},
            )
        _print_row_counts(row_counts)
        return 0
    except StagingError as exc:
        log_pipeline_event(
            logger,
            "Staging transformation failed",
            "staging",
            "staging_load",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Staging transformation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log_pipeline_event(
            logger,
            "Staging transformation failed",
            "staging",
            "staging_load",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Staging transformation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    """Build the staging CLI parser."""

    parser = argparse.ArgumentParser(
        description="Transform PostgreSQL raw records into staging tables.",
        epilog="Subcommand options include --limit, --no-validate, and --no-audit.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage = subparsers.add_parser("stage", help="Transform raw records into staging.")
    stage.add_argument("--limit", type=int, default=None, help="Maximum raw rows per table.")
    stage.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip staging validation before load.",
    )
    stage.add_argument("--no-audit", action="store_true", help="Skip governance audit event.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the staging CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "stage":
        return command_stage(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
