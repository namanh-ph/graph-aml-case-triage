"""Controlled end-to-end local demo orchestration CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import create_dashboard_engine, dispose_dashboard_engine  # noqa: E402
from graph_aml.demo import (  # noqa: E402
    DemoError,
    build_demo_artefact_index,
    build_demo_readiness_summary,
    build_demo_steps,
    build_demo_validation_summary,
    demo_run_result_to_dict,
    generate_demo_readiness_artefacts,
    load_demo_orchestration_config,
    run_demo_pipeline,
    write_demo_artefact_index_json,
    write_demo_readiness_report_json,
    write_demo_validation_summary_json,
)


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def command_plan(args: argparse.Namespace) -> int:
    print("demo plan requested", file=sys.stderr)
    config = load_demo_orchestration_config(args.config)
    steps = build_demo_steps(config, include_reset=args.include_reset)
    _print_json(
        {
            "demo_name": config.demo.name,
            "demo_version": config.demo.version,
            "include_reset": args.include_reset,
            "steps": [
                {
                    "name": step.name,
                    "command": step.command,
                    "destructive": step.destructive,
                    "required": step.required,
                }
                for step in steps
            ],
        }
    )
    return 0


def command_readiness(args: argparse.Namespace) -> int:
    print("demo readiness checks started", file=sys.stderr)
    config = load_demo_orchestration_config(args.config)
    readiness = build_demo_readiness_summary(config)
    if args.write_artefacts:
        write_demo_readiness_report_json(
            readiness,
            Path(args.output_dir) / "demo_readiness_report.json",
        )
        write_demo_artefact_index_json(
            build_demo_artefact_index(args.output_dir),
            Path(args.output_dir) / "demo_artefact_index.json",
        )
        print("demo artefact index built", file=sys.stderr)
    _print_json(readiness)
    return 0


def command_run(args: argparse.Namespace) -> int:
    print("demo run started", file=sys.stderr)
    config = load_demo_orchestration_config(args.config)
    result = run_demo_pipeline(
        config,
        include_reset=args.include_reset,
        dry_run=args.dry_run,
        stop_on_failure=args.stop_on_failure,
        timeout_seconds=args.timeout_seconds,
    )
    for step_result in result.steps:
        if step_result.status == "failed":
            print(f"demo step failed: {step_result.name}", file=sys.stderr)
        else:
            print(f"demo step completed: {step_result.name}", file=sys.stderr)
    if args.write_artefacts:
        generate_demo_readiness_artefacts(
            run_result=result,
            output_dir=args.output_dir,
        )
        print("demo artefact index built", file=sys.stderr)
    _print_json(demo_run_result_to_dict(result))
    return 0 if result.status in {"planned", "success"} else 1


def command_validate(args: argparse.Namespace) -> int:
    print("demo validation started", file=sys.stderr)
    config = load_demo_orchestration_config(args.config)
    engine = None
    try:
        engine = create_dashboard_engine()
        validation_summary = build_demo_validation_summary(engine, config)
    finally:
        dispose_dashboard_engine(engine)
    if args.write_artefacts:
        write_demo_validation_summary_json(
            validation_summary,
            Path(args.output_dir) / "demo_validation_summary.json",
        )
        write_demo_artefact_index_json(
            build_demo_artefact_index(args.output_dir),
            Path(args.output_dir) / "demo_artefact_index.json",
        )
        print("demo artefact index built", file=sys.stderr)
    _print_json(validation_summary)
    return 0


def command_artefacts(args: argparse.Namespace) -> int:
    config = load_demo_orchestration_config(args.config)
    report_dir = args.report_dir or config.demo.artefact_output_dir
    artefact_index = build_demo_artefact_index(report_dir)
    write_demo_artefact_index_json(
        artefact_index,
        Path(args.output_dir) / "demo_artefact_index.json",
    )
    print("demo artefact index built", file=sys.stderr)
    _print_json(artefact_index)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="End-to-end local demo orchestration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Print ordered demo steps")
    plan_parser.add_argument("--config", default="config/demo.yaml")
    plan_parser.add_argument("--include-reset", action="store_true")
    plan_parser.set_defaults(func=command_plan)

    readiness_parser = subparsers.add_parser("readiness", help="Run local readiness checks")
    readiness_parser.add_argument("--config", default="config/demo.yaml")
    readiness_parser.add_argument("--output-dir", default="reports/model_validation")
    readiness_parser.add_argument("--write-artefacts", action="store_true")
    readiness_parser.set_defaults(func=command_readiness)

    run_parser = subparsers.add_parser("run", help="Run controlled demo pipeline")
    run_parser.add_argument("--config", default="config/demo.yaml")
    run_parser.add_argument("--include-reset", action="store_true")
    run_parser.add_argument("--dry-run", action="store_true")
    failure_group = run_parser.add_mutually_exclusive_group()
    failure_group.add_argument("--stop-on-failure", dest="stop_on_failure", action="store_true")
    failure_group.add_argument(
        "--continue-on-failure",
        dest="stop_on_failure",
        action="store_false",
    )
    run_parser.set_defaults(stop_on_failure=True)
    run_parser.add_argument("--timeout-seconds", type=int, default=None)
    run_parser.add_argument("--output-dir", default="reports/model_validation")
    run_parser.add_argument("--write-artefacts", action="store_true")
    run_parser.set_defaults(func=command_run)

    validate_parser = subparsers.add_parser("validate", help="Validate demo database counts")
    validate_parser.add_argument("--config", default="config/demo.yaml")
    validate_parser.add_argument("--output-dir", default="reports/model_validation")
    validate_parser.add_argument("--write-artefacts", action="store_true")
    validate_parser.set_defaults(func=command_validate)

    artefacts_parser = subparsers.add_parser("artefacts", help="Build demo artefact index")
    artefacts_parser.add_argument("--config", default="config/demo.yaml")
    artefacts_parser.add_argument("--report-dir", default=None)
    artefacts_parser.add_argument("--output-dir", default="reports/model_validation")
    artefacts_parser.set_defaults(func=command_artefacts)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = int(args.func(args))
        print("demo CLI completed", file=sys.stderr)
        return result
    except DemoError as exc:
        print(f"demo CLI failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
