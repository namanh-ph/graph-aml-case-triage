"""Safe dashboard smoke CLI for configuration and read-only health checks."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import (  # noqa: E402
    DashboardError,
    build_account_profile_metrics,
    build_graph_view_frames,
    build_model_metrics_summary,
    build_validation_report_index,
    check_dashboard_database_health,
    create_dashboard_engine,
    dispose_dashboard_engine,
    load_dashboard_config,
    read_account_profile,
    read_dashboard_audit_summary,
    read_dashboard_model_metric_bundle,
    read_dashboard_overview_counts,
    read_graph_view_context,
    summarise_graph_view,
)


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def command_config(args: argparse.Namespace) -> int:
    config = load_dashboard_config(args.config)
    payload = asdict(config)
    _print_json(
        {
            "title": payload["title"],
            "layout": payload["layout"],
            "default_page_size": payload["default_page_size"],
            "max_page_size": payload["max_page_size"],
            "enable_lifecycle_actions": payload["enable_lifecycle_actions"],
            "enable_case_evidence_preview": payload["enable_case_evidence_preview"],
        }
    )
    return 0


def command_health(_: argparse.Namespace) -> int:
    engine = None
    try:
        engine = create_dashboard_engine()
        _print_json(check_dashboard_database_health(engine))
        return 0
    finally:
        dispose_dashboard_engine(engine)


def command_summary(_: argparse.Namespace) -> int:
    engine = None
    try:
        engine = create_dashboard_engine()
        _print_json(read_dashboard_overview_counts(engine))
        return 0
    finally:
        dispose_dashboard_engine(engine)


def command_graph_summary(args: argparse.Namespace) -> int:
    engine = None
    try:
        config = load_dashboard_config()
        if args.max_hops is not None:
            config = replace(
                config,
                graph_view=replace(config.graph_view, max_hops=args.max_hops),
            )
        engine = create_dashboard_engine()
        context = read_graph_view_context(
            engine,
            account_id=args.account_id,
            case_id=args.case_id,
            community_id=args.community_id,
            risk_band=args.risk_band,
            config=config,
        )
        frames = build_graph_view_frames(context, config)
        _print_json(summarise_graph_view(frames["nodes"], frames["edges"]))
        return 0
    finally:
        dispose_dashboard_engine(engine)


def command_account_summary(args: argparse.Namespace) -> int:
    engine = None
    try:
        config = load_dashboard_config()
        engine = create_dashboard_engine()
        profile = read_account_profile(engine, args.account_id, config)
        _print_json(build_account_profile_metrics(profile))
        return 0
    finally:
        dispose_dashboard_engine(engine)


def command_model_summary(_: argparse.Namespace) -> int:
    engine = None
    try:
        config = load_dashboard_config()
        engine = create_dashboard_engine()
        _print_json(build_model_metrics_summary(read_dashboard_model_metric_bundle(engine, config)))
        return 0
    finally:
        dispose_dashboard_engine(engine)


def command_audit_summary(_: argparse.Namespace) -> int:
    engine = None
    try:
        engine = create_dashboard_engine()
        _print_json(read_dashboard_audit_summary(engine))
        return 0
    finally:
        dispose_dashboard_engine(engine)


def command_validation_index(_: argparse.Namespace) -> int:
    config = load_dashboard_config()
    _print_json(
        build_validation_report_index(
            config.validation_report.report_dir,
            config.validation_report.allowed_extensions,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dashboard configuration and read-only smoke checks"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("config", help="Print safe dashboard config summary")
    config_parser.add_argument("--config", default="config/dashboard.yaml")
    config_parser.set_defaults(func=command_config)

    health_parser = subparsers.add_parser("health", help="Run dashboard database health check")
    health_parser.set_defaults(func=command_health)

    summary_parser = subparsers.add_parser("summary", help="Read dashboard overview summary")
    summary_parser.set_defaults(func=command_summary)

    graph_parser = subparsers.add_parser("graph-summary", help="Read graph view summary")
    graph_parser.add_argument("--account-id")
    graph_parser.add_argument("--case-id")
    graph_parser.add_argument("--community-id")
    graph_parser.add_argument("--risk-band")
    graph_parser.add_argument("--max-hops", type=int, default=None)
    graph_parser.set_defaults(func=command_graph_summary)

    account_parser = subparsers.add_parser("account-summary", help="Read account profile summary")
    account_parser.add_argument("--account-id", required=True)
    account_parser.set_defaults(func=command_account_summary)

    model_parser = subparsers.add_parser("model-summary", help="Read model metric summary")
    model_parser.set_defaults(func=command_model_summary)

    audit_parser = subparsers.add_parser("audit-summary", help="Read audit event summary")
    audit_parser.set_defaults(func=command_audit_summary)

    validation_parser = subparsers.add_parser(
        "validation-index",
        help="Read local validation artefact index",
    )
    validation_parser.set_defaults(func=command_validation_index)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except DashboardError as exc:
        print(f"dashboard CLI failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
