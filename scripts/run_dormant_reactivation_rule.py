"""CLI for running the deterministic dormant reactivation AML rule."""

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
    DormantReactivationRuleConfig,
    RuleError,
    read_dormant_reactivation_rule_inputs,
    run_dormant_reactivation_rule,
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


def _build_config(args: argparse.Namespace) -> DormantReactivationRuleConfig:
    return DormantReactivationRuleConfig(
        dormant_days_threshold=args.dormant_days_threshold,
        reactivation_window_days=args.reactivation_window_days,
        min_outbound_amount=args.min_outbound_amount,
        min_total_outbound_amount=args.min_total_outbound_amount,
        min_outbound_transaction_count=args.min_outbound_transaction_count,
        severity=args.severity,
        base_risk_score=args.base_risk_score,
        high_value_risk_score=args.high_value_risk_score,
        high_value_multiplier=args.high_value_multiplier,
        include_counterparty_outflows=not args.exclude_counterparty_outflows,
        include_internal_account_outflows=not args.exclude_internal_account_outflows,
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
    """Run the dormant reactivation rule against PostgreSQL staging tables."""

    _configure_logging()
    logger = get_logger("graph_aml.rules.dormant_reactivation.cli")
    context = create_run_context(component="rules", pipeline_stage="dormant_reactivation")
    engine = create_database_engine()
    try:
        config = _build_config(args)
        log_pipeline_event(
            logger,
            "Dormant reactivation rule started",
            "rules",
            "dormant_reactivation",
            "started",
            context,
            limit=args.limit,
            persist=args.persist,
            write_audit=not args.no_audit,
            dormant_days_threshold=config.dormant_days_threshold,
            min_total_outbound_amount=config.min_total_outbound_amount,
        )
        transactions, accounts = read_dormant_reactivation_rule_inputs(
            engine,
            limit=args.limit,
        )
        log_pipeline_event(
            logger,
            "Staged inputs read",
            "rules",
            "dormant_reactivation",
            "completed",
            context,
            transaction_rows=len(transactions),
            account_rows=len(accounts),
        )
        alerts = run_dormant_reactivation_rule(transactions, accounts, config=config)
        rule_summary = summarise_rule_alerts(alerts)
        log_pipeline_event(
            logger,
            "Dormant reactivation detections completed",
            "rules",
            "dormant_reactivation",
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
                    "dormant_days_threshold": config.dormant_days_threshold,
                    "reactivation_window_days": config.reactivation_window_days,
                    "min_total_outbound_amount": config.min_total_outbound_amount,
                },
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
            log_pipeline_event(
                logger,
                "Alerts persisted",
                "rules",
                "dormant_reactivation",
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
                    "dormant_days_threshold": config.dormant_days_threshold,
                    "reactivation_window_days": config.reactivation_window_days,
                    "min_outbound_amount": config.min_outbound_amount,
                    "min_total_outbound_amount": config.min_total_outbound_amount,
                    "min_outbound_transaction_count": (config.min_outbound_transaction_count),
                },
                action="run_dormant_reactivation_rule",
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
            "Dormant reactivation rule completed",
            "rules",
            "dormant_reactivation",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except RuleError as exc:
        log_pipeline_event(
            logger,
            "Dormant reactivation rule failed",
            "rules",
            "dormant_reactivation",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Dormant reactivation rule failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic AML dormant reactivation rule")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser(
        "run",
        help="Run dormant reactivation rule from staged data",
    )
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--persist", action="store_true")
    run_parser.add_argument("--no-audit", action="store_true")
    run_parser.add_argument("--dormant-days-threshold", type=int, default=120)
    run_parser.add_argument("--reactivation-window-days", type=int, default=7)
    run_parser.add_argument("--min-outbound-amount", type=float, default=10000.0)
    run_parser.add_argument("--min-total-outbound-amount", type=float, default=10000.0)
    run_parser.add_argument("--min-outbound-transaction-count", type=int, default=1)
    run_parser.add_argument("--severity", default="high")
    run_parser.add_argument("--base-risk-score", type=float, default=80.0)
    run_parser.add_argument("--high-value-risk-score", type=float, default=90.0)
    run_parser.add_argument("--high-value-multiplier", type=float, default=2.0)
    run_parser.add_argument("--exclude-counterparty-outflows", action="store_true")
    run_parser.add_argument("--exclude-internal-account-outflows", action="store_true")
    run_parser.set_defaults(handler=command_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
