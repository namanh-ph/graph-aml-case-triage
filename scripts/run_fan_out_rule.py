"""CLI for running the deterministic fan-out AML rule."""

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
    FanOutRuleConfig,
    RuleError,
    read_fan_out_rule_inputs,
    run_fan_out_rule,
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


def _build_config(args: argparse.Namespace) -> FanOutRuleConfig:
    return FanOutRuleConfig(
        min_unique_recipients=args.min_unique_recipients,
        window_days=args.window_days,
        severity=args.severity,
        base_risk_score=args.base_risk_score,
        high_recipient_risk_score=args.high_recipient_risk_score,
        high_recipient_multiplier=args.high_recipient_multiplier,
        min_total_amount=args.min_total_amount,
        include_counterparties=not args.exclude_counterparties,
        include_internal_accounts=not args.exclude_internal_accounts,
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
    """Run the fan-out rule against PostgreSQL staging tables."""

    _configure_logging()
    logger = get_logger("graph_aml.rules.fan_out.cli")
    context = create_run_context(component="rules", pipeline_stage="fan_out")
    engine = create_database_engine()
    try:
        config = _build_config(args)
        log_pipeline_event(
            logger,
            "Fan-out rule started",
            "rules",
            "fan_out",
            "started",
            context,
            limit=args.limit,
            persist=args.persist,
            write_audit=not args.no_audit,
            min_unique_recipients=config.min_unique_recipients,
            window_days=config.window_days,
            min_total_amount=config.min_total_amount,
        )
        transactions, accounts = read_fan_out_rule_inputs(engine, limit=args.limit)
        log_pipeline_event(
            logger,
            "Staged inputs read",
            "rules",
            "fan_out",
            "completed",
            context,
            transaction_rows=len(transactions),
            account_rows=len(accounts),
        )
        alerts = run_fan_out_rule(transactions, accounts, config=config)
        rule_summary = summarise_rule_alerts(alerts)
        log_pipeline_event(
            logger,
            "Fan-out detections completed",
            "rules",
            "fan_out",
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
                    "min_unique_recipients": config.min_unique_recipients,
                    "window_days": config.window_days,
                    "min_total_amount": config.min_total_amount,
                },
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
            log_pipeline_event(
                logger,
                "Alerts persisted",
                "rules",
                "fan_out",
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
                    "min_unique_recipients": config.min_unique_recipients,
                    "window_days": config.window_days,
                    "min_total_amount": config.min_total_amount,
                },
                action="run_fan_out_rule",
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
            "Fan-out rule completed",
            "rules",
            "fan_out",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except RuleError as exc:
        log_pipeline_event(
            logger,
            "Fan-out rule failed",
            "rules",
            "fan_out",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Fan-out rule failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic AML fan-out rule")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run fan-out rule from staged data")
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--persist", action="store_true")
    run_parser.add_argument("--no-audit", action="store_true")
    run_parser.add_argument("--min-unique-recipients", type=int, default=20)
    run_parser.add_argument("--window-days", type=int, default=7)
    run_parser.add_argument("--severity", default="high")
    run_parser.add_argument("--base-risk-score", type=float, default=80.0)
    run_parser.add_argument("--high-recipient-risk-score", type=float, default=90.0)
    run_parser.add_argument("--high-recipient-multiplier", type=float, default=1.5)
    run_parser.add_argument("--min-total-amount", type=float, default=0.0)
    run_parser.add_argument("--exclude-counterparties", action="store_true")
    run_parser.add_argument("--exclude-internal-accounts", action="store_true")
    run_parser.set_defaults(handler=command_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
