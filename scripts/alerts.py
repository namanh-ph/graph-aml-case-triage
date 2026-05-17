"""CLI smoke utilities for the common AML alert schema."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.alerts import (  # noqa: E402
    ALERT_COLUMNS,
    ALERT_SEVERITIES,
    ALERT_STATUSES,
    AML_ALERTS_TABLE,
    AlertError,
    read_alerts,
    summarise_alerts,
)
from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.database import create_database_engine, dispose_engine  # noqa: E402
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


def command_schema_info(args: argparse.Namespace) -> int:
    """Print common alert schema metadata."""

    _configure_logging()
    logger = get_logger("graph_aml.alerts.cli")
    context = create_run_context(component="alerts", pipeline_stage="schema_info")
    log_pipeline_event(
        logger,
        "Alert schema info requested",
        "alerts",
        "schema_info",
        "completed",
        context,
    )
    print(f"target_table={AML_ALERTS_TABLE}")
    print("columns=" + ",".join(ALERT_COLUMNS))
    print("severities=" + ",".join(ALERT_SEVERITIES))
    print("statuses=" + ",".join(ALERT_STATUSES))
    return 0


def command_read(args: argparse.Namespace) -> int:
    """Read alerts from PostgreSQL and print a compact summary."""

    _configure_logging()
    logger = get_logger("graph_aml.alerts.cli")
    context = create_run_context(component="alerts", pipeline_stage="read")
    engine = create_database_engine()
    try:
        log_pipeline_event(
            logger,
            "Alert read started",
            "alerts",
            "read",
            "started",
            context,
            rule_name=args.rule_name,
            severity=args.severity,
            status=args.status,
            limit=args.limit,
        )
        frame = read_alerts(
            engine,
            rule_name=args.rule_name,
            severity=args.severity,
            alert_status=args.status,
            limit=args.limit,
        )
        summary = summarise_alerts(frame)
        log_pipeline_event(
            logger,
            "Alert read completed",
            "alerts",
            "read",
            "completed",
            context,
            alert_count=summary["alert_count"],
        )
        for key in (
            "alert_count",
            "unique_account_count",
            "unique_customer_count",
            "mean_rule_score",
            "max_rule_score",
        ):
            print(f"{key}={summary[key]}")
        return 0
    except AlertError as exc:
        log_pipeline_event(
            logger,
            "Alert CLI failed",
            "alerts",
            "read",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Alert CLI failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log_pipeline_event(
            logger,
            "Alert CLI failed",
            "alerts",
            "read",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Alert CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    """Build the alert CLI parser."""

    parser = argparse.ArgumentParser(
        description="Inspect the common AML alert schema and stored alert rows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("schema-info", help="Print common alert schema metadata.")

    read = subparsers.add_parser("read", help="Read stored AML alerts.")
    read.add_argument("--rule-name", default=None, help="Filter by rule name.")
    read.add_argument("--severity", default=None, help="Filter by severity.")
    read.add_argument("--status", default=None, help="Filter by alert status.")
    read.add_argument("--limit", type=int, default=None, help="Maximum alerts to read.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the alert CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "schema-info":
        return command_schema_info(args)
    if args.command == "read":
        return command_read(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
