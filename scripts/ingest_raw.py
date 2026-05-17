"""CLI for loading silver-layer parquet datasets into PostgreSQL raw tables."""

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
from graph_aml.ingestion import (  # noqa: E402
    DEFAULT_SILVER_DIR,
    DEFAULT_SOURCE_SYSTEM,
    IngestionError,
    ingest_silver_to_raw,
)
from graph_aml.observability import (  # noqa: E402
    configure_logging,
    create_run_context,
    get_logger,
    log_pipeline_event,
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


def command_ingest(args: argparse.Namespace) -> int:
    """Ingest silver-layer parquet into raw PG tables."""

    _configure_logging()
    logger = get_logger("graph_aml.ingestion.cli")
    context = create_run_context(component="ingestion", pipeline_stage="raw_load")
    engine = create_database_engine()
    try:
        log_pipeline_event(
            logger,
            "Raw ingestion started",
            "ingestion",
            "raw_load",
            "started",
            context,
            silver_dir=str(args.silver_dir),
        )
        row_counts = ingest_silver_to_raw(
            engine,
            silver_dir=args.silver_dir,
            source_system=args.source_system,
            write_audit=not args.no_audit,
        )
        log_pipeline_event(
            logger,
            "Raw ingestion completed",
            "ingestion",
            "raw_load",
            "completed",
            context,
            row_counts=row_counts,
        )
        _print_row_counts(row_counts)
        return 0
    except IngestionError as exc:
        log_pipeline_event(
            logger,
            "Raw ingestion failed",
            "ingestion",
            "raw_load",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Raw ingestion failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log_pipeline_event(
            logger,
            "Raw ingestion failed",
            "ingestion",
            "raw_load",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Raw ingestion failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    """Build the raw ingestion CLI parser."""

    parser = argparse.ArgumentParser(
        description="Load silver-layer parquet datasets into PostgreSQL raw tables.",
    )
    parser.add_argument(
        "--silver-dir",
        type=Path,
        default=PROJECT_ROOT / DEFAULT_SILVER_DIR,
        help="Silver layer directory containing parquet files (default: data/silver).",
    )
    parser.add_argument(
        "--source-system",
        default=DEFAULT_SOURCE_SYSTEM,
        help=f"Source system label (default: {DEFAULT_SOURCE_SYSTEM}).",
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip governance audit event.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the raw ingestion CLI."""

    args = build_parser().parse_args(argv)
    return command_ingest(args)


if __name__ == "__main__":
    raise SystemExit(main())
