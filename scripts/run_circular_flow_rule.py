"""CLI for running the deterministic circular flow AML rule."""

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
    CircularFlowDetectionConfig,
    CircularFlowRuleConfig,
    RuleError,
    read_circular_flow_rule_inputs,
    run_circular_flow_detection_and_alerts,
    write_circular_flow_alerts_json,
    write_circular_flow_detections_csv,
    write_circular_flow_detections_json,
    write_circular_flow_summary_json,
    write_rule_execution_audit_event,
)


def _configure_logging() -> None:
    config = load_app_config()
    configure_logging(
        log_dir=config.paths.paths.logs_dir,
        enable_console=False,
        enable_file=True,
    )


def _build_detection_config(args: argparse.Namespace) -> CircularFlowDetectionConfig:
    return CircularFlowDetectionConfig(
        max_cycle_hops=args.max_cycle_hops,
        min_cycle_hops=args.min_cycle_hops,
        min_total_amount=args.min_total_amount,
        max_time_span_hours=args.max_time_span_hours,
        include_counterparty_edges=args.include_counterparty_edges,
        include_self_loops=args.include_self_loops,
        max_cycles_per_account=args.max_cycles_per_account,
        max_total_cycles=args.max_total_cycles,
    )


def _build_alert_config(
    args: argparse.Namespace,
    detection_config: CircularFlowDetectionConfig,
) -> CircularFlowRuleConfig:
    return CircularFlowRuleConfig(
        severity=args.severity,
        base_risk_score=args.base_risk_score,
        high_amount_risk_score=args.high_amount_risk_score,
        high_amount_threshold=args.high_amount_threshold,
        long_cycle_risk_score=args.long_cycle_risk_score,
        long_cycle_hop_threshold=args.long_cycle_hop_threshold,
        detection_config=detection_config,
    )


def _print_summary(summary: dict[str, object]) -> None:
    for key in (
        "rule_name",
        "cycles_detected",
        "alerts_generated",
        "alerts_persisted",
        "unique_account_count",
        "artefacts_written",
        "persisted",
    ):
        print(f"{key}={summary[key]}")


def command_run(args: argparse.Namespace) -> int:
    """Run circular-flow detection and alert conversion against staged data."""

    _configure_logging()
    logger = get_logger("graph_aml.rules.circular_flow_rule.cli")
    context = create_run_context(component="rules", pipeline_stage="circular_flow_rule")
    engine = create_database_engine()
    try:
        detection_config = _build_detection_config(args)
        alert_config = _build_alert_config(args, detection_config)
        log_pipeline_event(
            logger,
            "Circular flow rule started",
            "rules",
            "circular_flow_rule",
            "started",
            context,
            limit=args.limit,
            persist=args.persist,
            write_artefacts=not args.no_artefacts,
            write_audit=not args.no_audit,
            max_cycle_hops=detection_config.max_cycle_hops,
            max_time_span_hours=detection_config.max_time_span_hours,
        )
        transactions, accounts = read_circular_flow_rule_inputs(engine, limit=args.limit)
        log_pipeline_event(
            logger,
            "Staged inputs read",
            "rules",
            "circular_flow_rule",
            "completed",
            context,
            transaction_rows=len(transactions),
            account_rows=len(accounts),
        )
        result = run_circular_flow_detection_and_alerts(
            transactions,
            accounts,
            detection_config=detection_config,
            alert_config=alert_config,
        )
        detections = result["detections"]
        alerts = result["alerts"]
        detection_summary = result["detection_summary"]
        alert_summary = result["alert_summary"]
        log_pipeline_event(
            logger,
            "Circular flow detections completed",
            "rules",
            "circular_flow_rule",
            "completed",
            context,
            cycles_detected=detection_summary["cycle_count"],
        )
        log_pipeline_event(
            logger,
            "Circular flow alerts built",
            "rules",
            "circular_flow_rule",
            "completed",
            context,
            alerts_generated=len(alerts),
            unique_account_count=alert_summary["unique_account_count"],
        )
        if not args.no_artefacts:
            output_dir = Path(args.output_dir)
            write_circular_flow_detections_json(
                detections,
                output_dir / "circular_flow_detections.json",
            )
            write_circular_flow_detections_csv(
                detections,
                output_dir / "circular_flow_detections.csv",
            )
            write_circular_flow_summary_json(
                detection_summary,
                output_dir / "circular_flow_summary.json",
            )
            write_circular_flow_alerts_json(
                alerts,
                output_dir / "circular_flow_alerts.json",
            )
        alerts_persisted = 0
        if args.persist:
            persistence_summary = persist_alerts(
                engine,
                alerts,
                write_audit=not args.no_audit,
                metadata={"rule_name": alert_config.rule_name, "limit": args.limit},
            )
            alerts_persisted = int(persistence_summary["alerts_upserted"])
            log_pipeline_event(
                logger,
                "Circular flow alerts persisted",
                "rules",
                "circular_flow_rule",
                "completed",
                context,
                alerts_persisted=alerts_persisted,
            )
        if not args.no_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=alert_config.rule_name,
                alerts_generated=len(alerts),
                alerts_persisted=alerts_persisted,
                status="completed",
                metadata={
                    "limit": args.limit,
                    "persisted": args.persist,
                    "cycles_detected": detection_summary["cycle_count"],
                    "artefacts_written": not args.no_artefacts,
                    "max_cycle_hops": detection_config.max_cycle_hops,
                    "min_cycle_hops": detection_config.min_cycle_hops,
                    "min_total_amount": detection_config.min_total_amount,
                    "max_time_span_hours": detection_config.max_time_span_hours,
                    "high_amount_threshold": alert_config.high_amount_threshold,
                    "long_cycle_hop_threshold": alert_config.long_cycle_hop_threshold,
                },
                action="run_circular_flow_rule",
            )
        summary = {
            "rule_name": alert_config.rule_name,
            "cycles_detected": detection_summary["cycle_count"],
            "alerts_generated": len(alerts),
            "alerts_persisted": alerts_persisted,
            "unique_account_count": alert_summary["unique_account_count"],
            "artefacts_written": not args.no_artefacts,
            "persisted": args.persist,
        }
        log_pipeline_event(
            logger,
            "Circular flow rule completed",
            "rules",
            "circular_flow_rule",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except RuleError as exc:
        log_pipeline_event(
            logger,
            "Circular flow rule failed",
            "rules",
            "circular_flow_rule",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Circular flow rule failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic AML circular flow rule")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser(
        "run",
        help="Run circular flow rule from staged data",
    )
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--persist", action="store_true")
    run_parser.add_argument("--no-audit", action="store_true")
    run_parser.add_argument("--output-dir", default="reports/model_validation")
    run_parser.add_argument("--no-artefacts", action="store_true")
    run_parser.add_argument("--max-cycle-hops", type=int, default=4)
    run_parser.add_argument("--min-cycle-hops", type=int, default=2)
    run_parser.add_argument("--min-total-amount", type=float, default=0.0)
    run_parser.add_argument("--max-time-span-hours", type=int, default=168)
    run_parser.add_argument("--include-counterparty-edges", action="store_true")
    run_parser.add_argument("--include-self-loops", action="store_true")
    run_parser.add_argument("--max-cycles-per-account", type=int, default=3)
    run_parser.add_argument("--max-total-cycles", type=int, default=500)
    run_parser.add_argument("--severity", default="high")
    run_parser.add_argument("--base-risk-score", type=float, default=85.0)
    run_parser.add_argument("--high-amount-risk-score", type=float, default=90.0)
    run_parser.add_argument("--high-amount-threshold", type=float, default=50000.0)
    run_parser.add_argument("--long-cycle-risk-score", type=float, default=90.0)
    run_parser.add_argument("--long-cycle-hop-threshold", type=int, default=4)
    run_parser.set_defaults(handler=command_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
