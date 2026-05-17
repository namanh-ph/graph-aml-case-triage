"""CLI for running the deterministic structuring AML rule."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.alerts import persist_alerts  # noqa: E402
from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.database import create_database_engine, dispose_engine  # noqa: E402
from graph_aml.observability import (  # noqa: E402
    configure_logging,
    create_run_context,
    get_logger,
    log_pipeline_event,
)
from graph_aml.rules import (  # noqa: E402
    RuleError,
    StructuringRuleConfig,
    read_structuring_rule_inputs,
    run_structuring_rule,
    summarise_rule_alerts,
    write_rule_execution_audit_event,
)


def _configure_logging() -> None:
    config = load_app_config()
    configure_logging(
        log_dir=config.paths.paths.logs_dir,
        enable_console=False,
        enable_file=True,
    )


def _build_config(args: argparse.Namespace) -> StructuringRuleConfig:
    return StructuringRuleConfig(
        reporting_threshold=args.reporting_threshold,
        below_threshold_margin=args.below_threshold_margin,
        min_transaction_count=args.min_transaction_count,
        window_hours=args.window_hours,
        severity=args.severity,
        base_risk_score=args.base_risk_score,
        high_count_risk_score=args.high_count_risk_score,
    )


def _print_summary(summary: dict[str, object]) -> None:
    for key in (
        "rule_name",
        "alerts_generated",
        "alerts_persisted",
        "unique_account_count",
        "persisted",
    ):
        print(f"{key}={summary[key]}")


def command_run(args: argparse.Namespace) -> int:
    """Run the structuring rule against PostgreSQL staging tables."""

    _configure_logging()
    logger = get_logger("graph_aml.rules.structuring.cli")
    context = create_run_context(component="rules", pipeline_stage="structuring")
    engine = create_database_engine()
    try:
        config = _build_config(args)
        log_pipeline_event(
            logger,
            "Structuring rule started",
            "rules",
            "structuring",
            "started",
            context,
            limit=args.limit,
            persist=args.persist,
            write_audit=not args.no_audit,
            reporting_threshold=config.reporting_threshold,
            below_threshold_margin=config.below_threshold_margin,
            min_transaction_count=config.min_transaction_count,
            window_hours=config.window_hours,
        )
        transactions, accounts = read_structuring_rule_inputs(engine, limit=args.limit)
        log_pipeline_event(
            logger,
            "Staged inputs read",
            "rules",
            "structuring",
            "completed",
            context,
            transaction_rows=len(transactions),
            account_rows=len(accounts),
        )
        alerts = run_structuring_rule(transactions, accounts, config=config)
        rule_summary = summarise_rule_alerts(alerts)
        log_pipeline_event(
            logger,
            "Structuring detections completed",
            "rules",
            "structuring",
            "completed",
            context,
            alerts_generated=len(alerts),
            unique_account_count=rule_summary["unique_account_count"],
        )
        alerts_persisted = 0
        if args.persist:
            persistence_summary = persist_alerts(
                engine,
                alerts,
                write_audit=not args.no_audit,
                metadata={
                    "rule_name": config.rule_name,
                    "limit": args.limit,
                    "reporting_threshold": config.reporting_threshold,
                    "below_threshold_margin": config.below_threshold_margin,
                    "min_transaction_count": config.min_transaction_count,
                    "window_hours": config.window_hours,
                },
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
            log_pipeline_event(
                logger,
                "Alerts persisted",
                "rules",
                "structuring",
                "completed",
                context,
                alerts_persisted=alerts_persisted,
            )
        if not args.no_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=config.rule_name,
                alerts_generated=len(alerts),
                alerts_persisted=alerts_persisted,
                status="completed",
                metadata={
                    "limit": args.limit,
                    "persisted": args.persist,
                    "reporting_threshold": config.reporting_threshold,
                    "below_threshold_margin": config.below_threshold_margin,
                    "min_transaction_count": config.min_transaction_count,
                    "window_hours": config.window_hours,
                },
            )
        summary = {
            "rule_name": config.rule_name,
            "alerts_generated": len(alerts),
            "alerts_persisted": alerts_persisted,
            "unique_account_count": rule_summary["unique_account_count"],
            "persisted": args.persist,
        }
        log_pipeline_event(
            logger,
            "Structuring rule completed",
            "rules",
            "structuring",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except RuleError as exc:
        log_pipeline_event(
            logger,
            "Structuring rule failed",
            "rules",
            "structuring",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Structuring rule failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log_pipeline_event(
            logger,
            "Structuring rule failed",
            "rules",
            "structuring",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Structuring rule failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    """Build the structuring rule CLI parser."""

    parser = argparse.ArgumentParser(
        description="Run the deterministic AML structuring rule.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Run structuring detection on staged data.")
    run.add_argument("--limit", type=int, default=None, help="Maximum transactions to read.")
    run.add_argument("--persist", action="store_true", help="Persist generated alerts.")
    run.add_argument("--no-audit", action="store_true", help="Skip rule and alert audit events.")
    run.add_argument(
        "--reporting-threshold",
        type=float,
        default=10000.0,
        help="Reporting threshold amount.",
    )
    run.add_argument(
        "--below-threshold-margin",
        type=float,
        default=0.90,
        help="Lower margin for below-threshold amounts.",
    )
    run.add_argument(
        "--min-transaction-count",
        type=int,
        default=8,
        help="Minimum candidate transactions in a detection window.",
    )
    run.add_argument(
        "--window-hours",
        type=int,
        default=24,
        help="Rolling detection window size in hours.",
    )
    run.add_argument("--severity", default="high", help="Alert severity.")
    run.add_argument(
        "--base-risk-score",
        type=float,
        default=80.0,
        help="Rule score for normal structuring detections.",
    )
    run.add_argument(
        "--high-count-risk-score",
        type=float,
        default=90.0,
        help="Rule score for high-count structuring detections.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the structuring rule CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "run":
        return command_run(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
