"""CLI for running the deterministic fan-in AML rule."""

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
    FanInRuleConfig,
    RuleError,
    read_fan_in_rule_inputs,
    run_fan_in_rule,
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


def _build_config(args: argparse.Namespace) -> FanInRuleConfig:
    return FanInRuleConfig(
        min_unique_senders=args.min_unique_senders,
        window_days=args.window_days,
        severity=args.severity,
        base_risk_score=args.base_risk_score,
        high_sender_risk_score=args.high_sender_risk_score,
        high_sender_multiplier=args.high_sender_multiplier,
        min_total_amount=args.min_total_amount,
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
    """Run the fan-in rule against PostgreSQL staging tables."""

    _configure_logging()
    logger = get_logger("graph_aml.rules.fan_in.cli")
    context = create_run_context(component="rules", pipeline_stage="fan_in")
    engine = create_database_engine()
    try:
        config = _build_config(args)
        log_pipeline_event(
            logger,
            "Fan-in rule started",
            "rules",
            "fan_in",
            "started",
            context,
            limit=args.limit,
            persist=args.persist,
            write_audit=not args.no_audit,
            min_unique_senders=config.min_unique_senders,
            window_days=config.window_days,
            min_total_amount=config.min_total_amount,
        )
        transactions, accounts = read_fan_in_rule_inputs(engine, limit=args.limit)
        log_pipeline_event(
            logger,
            "Staged inputs read",
            "rules",
            "fan_in",
            "completed",
            context,
            transaction_rows=len(transactions),
            account_rows=len(accounts),
        )
        alerts = run_fan_in_rule(transactions, accounts, config=config)
        rule_summary = summarise_rule_alerts(alerts)
        log_pipeline_event(
            logger,
            "Fan-in detections completed",
            "rules",
            "fan_in",
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
                    "min_unique_senders": config.min_unique_senders,
                    "window_days": config.window_days,
                    "min_total_amount": config.min_total_amount,
                },
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
            log_pipeline_event(
                logger,
                "Alerts persisted",
                "rules",
                "fan_in",
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
                    "min_unique_senders": config.min_unique_senders,
                    "window_days": config.window_days,
                    "min_total_amount": config.min_total_amount,
                },
                action="run_fan_in_rule",
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
            "Fan-in rule completed",
            "rules",
            "fan_in",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except RuleError as exc:
        log_pipeline_event(
            logger,
            "Fan-in rule failed",
            "rules",
            "fan_in",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Fan-in rule failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log_pipeline_event(
            logger,
            "Fan-in rule failed",
            "rules",
            "fan_in",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Fan-in rule failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    """Build the fan-in rule CLI parser."""

    parser = argparse.ArgumentParser(
        description="Run the deterministic AML fan-in rule.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Run fan-in detection on staged data.")
    run.add_argument("--limit", type=int, default=None, help="Maximum transactions to read.")
    run.add_argument("--persist", action="store_true", help="Persist generated alerts.")
    run.add_argument("--no-audit", action="store_true", help="Skip rule and alert audit events.")
    run.add_argument(
        "--min-unique-senders",
        type=int,
        default=15,
        help="Minimum unique sending accounts in a detection window.",
    )
    run.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="Rolling detection window size in days.",
    )
    run.add_argument("--severity", default="high", help="Alert severity.")
    run.add_argument(
        "--base-risk-score",
        type=float,
        default=80.0,
        help="Rule score for normal fan-in detections.",
    )
    run.add_argument(
        "--high-sender-risk-score",
        type=float,
        default=90.0,
        help="Rule score for high-sender fan-in detections.",
    )
    run.add_argument(
        "--high-sender-multiplier",
        type=float,
        default=1.5,
        help="Unique-sender multiplier for high-sender risk scoring.",
    )
    run.add_argument(
        "--min-total-amount",
        type=float,
        default=0.0,
        help="Minimum total received amount in the detection window.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the fan-in rule CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "run":
        return command_run(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
