"""CLI for deterministic circular flow detection."""

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
from graph_aml.rules import (  # noqa: E402
    CircularFlowDetectionConfig,
    RuleError,
    detect_circular_flows,
    read_circular_flow_detection_inputs,
    summarise_circular_flow_detections,
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


def _build_config(args: argparse.Namespace) -> CircularFlowDetectionConfig:
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


def _print_summary(summary: dict[str, object]) -> None:
    for key in (
        "rule_name",
        "cycles_detected",
        "unique_primary_account_count",
        "artefacts_written",
        "persisted",
    ):
        print(f"{key}={summary[key]}")


def command_run(args: argparse.Namespace) -> int:
    """Run circular flow detection against PostgreSQL staging tables."""

    _configure_logging()
    logger = get_logger("graph_aml.rules.circular_flow.cli")
    context = create_run_context(component="rules", pipeline_stage="circular_flow")
    engine = create_database_engine()
    try:
        config = _build_config(args)
        log_pipeline_event(
            logger,
            "Circular flow detection started",
            "rules",
            "circular_flow",
            "started",
            context,
            limit=args.limit,
            output_dir=str(args.output_dir),
            write_artefacts=not args.no_artefacts,
            write_audit=not args.no_audit,
            max_cycle_hops=config.max_cycle_hops,
            max_time_span_hours=config.max_time_span_hours,
        )
        transactions = read_circular_flow_detection_inputs(engine, limit=args.limit)
        log_pipeline_event(
            logger,
            "Staged transactions read",
            "rules",
            "circular_flow",
            "completed",
            context,
            transaction_rows=len(transactions),
        )
        detections = detect_circular_flows(transactions, config)
        detection_summary = summarise_circular_flow_detections(detections)
        log_pipeline_event(
            logger,
            "Circular flow detection completed",
            "rules",
            "circular_flow",
            "completed",
            context,
            cycles_detected=detection_summary["cycle_count"],
            unique_primary_account_count=detection_summary["unique_primary_account_count"],
        )
        artefact_paths: dict[str, Path] = {}
        if not args.no_artefacts:
            output_dir = Path(args.output_dir)
            artefact_paths = {
                "detections_json": write_circular_flow_detections_json(
                    detections,
                    output_dir / "circular_flow_detections.json",
                ),
                "detections_csv": write_circular_flow_detections_csv(
                    detections,
                    output_dir / "circular_flow_detections.csv",
                ),
                "summary_json": write_circular_flow_summary_json(
                    detection_summary,
                    output_dir / "circular_flow_summary.json",
                ),
            }
            log_pipeline_event(
                logger,
                "Circular flow artefacts written",
                "rules",
                "circular_flow",
                "completed",
                context,
                artefact_paths={key: str(path) for key, path in artefact_paths.items()},
            )
        if not args.no_audit:
            write_rule_execution_audit_event(
                engine,
                rule_name=config.rule_name,
                alerts_generated=0,
                alerts_persisted=0,
                status="completed",
                metadata={
                    "limit": args.limit,
                    "cycles_detected": detection_summary["cycle_count"],
                    "artefacts_written": not args.no_artefacts,
                    "artefact_paths": {key: str(path) for key, path in artefact_paths.items()},
                    "max_cycle_hops": config.max_cycle_hops,
                    "min_cycle_hops": config.min_cycle_hops,
                    "min_total_amount": config.min_total_amount,
                    "max_time_span_hours": config.max_time_span_hours,
                },
                action="detect_circular_flows",
            )
        summary = {
            "rule_name": config.rule_name,
            "cycles_detected": detection_summary["cycle_count"],
            "unique_primary_account_count": detection_summary["unique_primary_account_count"],
            "artefacts_written": not args.no_artefacts,
            "persisted": False,
        }
        _print_summary(summary)
        return 0
    except RuleError as exc:
        log_pipeline_event(
            logger,
            "Circular flow detection failed",
            "rules",
            "circular_flow",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Circular flow detection failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic circular flow detection")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser(
        "run",
        help="Detect circular flows from staged transactions",
    )
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--output-dir", default="reports/model_validation")
    run_parser.add_argument("--no-artefacts", action="store_true")
    run_parser.add_argument("--no-audit", action="store_true")
    run_parser.add_argument("--max-cycle-hops", type=int, default=4)
    run_parser.add_argument("--min-cycle-hops", type=int, default=2)
    run_parser.add_argument("--min-total-amount", type=float, default=0.0)
    run_parser.add_argument("--max-time-span-hours", type=int, default=168)
    run_parser.add_argument("--include-counterparty-edges", action="store_true")
    run_parser.add_argument("--include-self-loops", action="store_true")
    run_parser.add_argument("--max-cycles-per-account", type=int, default=3)
    run_parser.add_argument("--max-total-cycles", type=int, default=500)
    run_parser.set_defaults(handler=command_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
