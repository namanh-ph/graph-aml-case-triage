"""Analyst feedback label generation CLI."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import create_dashboard_engine, dispose_dashboard_engine  # noqa: E402
from graph_aml.labels import (  # noqa: E402
    AnalystLabelConfig,
    LabelError,
    LabelPersistenceConfig,
    build_label_datasets_from_inputs,
    build_label_quality_summary,
    generate_label_artefacts,
    load_analyst_label_config,
    persist_label_datasets,
    read_account_labels,
    read_account_supervised_dataset,
    read_case_labels,
    read_case_supervised_dataset,
    read_label_inputs,
    read_label_summary,
)


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _config_with_overrides(args: argparse.Namespace) -> AnalystLabelConfig:
    config = load_analyst_label_config(args.config)
    if getattr(args, "label_version", None):
        config = replace(config, label_version=args.label_version)
    if getattr(args, "dataset_version", None):
        config = replace(config, dataset_version=args.dataset_version)
    return config


def command_build(args: argparse.Namespace) -> int:
    print("label build started", file=sys.stderr)
    engine = None
    try:
        config = _config_with_overrides(args)
        engine = create_dashboard_engine()
        inputs = read_label_inputs(engine, config, limit=args.limit)
        print("label inputs read", file=sys.stderr)
        result = build_label_datasets_from_inputs(inputs, config)
        print("case labels built", file=sys.stderr)
        print("account labels built", file=sys.stderr)
        print("supervised datasets built", file=sys.stderr)
        persistence_result = None
        if args.persist:
            persistence_result = persist_label_datasets(
                engine,
                result,
                LabelPersistenceConfig(
                    label_version=config.label_version,
                    dataset_version=config.dataset_version,
                    write_audit=not args.no_audit,
                ),
            )
            print("label datasets persisted", file=sys.stderr)
        if not args.no_artefacts:
            generate_label_artefacts(result, args.output_dir)
            print("label artefacts written", file=sys.stderr)
        payload = build_label_quality_summary(result, config)
        if persistence_result is not None:
            payload["persistence"] = persistence_result.__dict__
        _print_json(payload)
        return 0
    finally:
        dispose_dashboard_engine(engine)


def command_read(args: argparse.Namespace) -> int:
    print("label read requested", file=sys.stderr)
    engine = None
    try:
        engine = create_dashboard_engine()
        if args.kind == "case-labels":
            frame = read_case_labels(engine, args.label_version, args.label, args.limit)
        elif args.kind == "account-labels":
            frame = read_account_labels(engine, args.label_version, args.label, args.limit)
        elif args.kind == "case-dataset":
            frame = read_case_supervised_dataset(
                engine,
                args.dataset_version,
                args.label,
                args.limit,
            )
        else:
            frame = read_account_supervised_dataset(
                engine,
                args.dataset_version,
                args.label,
                args.limit,
            )
        _print_json(
            {
                "kind": args.kind,
                "row_count": int(len(frame)),
                "columns": list(frame.columns),
            }
        )
        return 0
    finally:
        dispose_dashboard_engine(engine)


def command_summary(_: argparse.Namespace) -> int:
    print("label summary requested", file=sys.stderr)
    engine = None
    try:
        engine = create_dashboard_engine()
        _print_json(read_label_summary(engine))
        return 0
    finally:
        dispose_dashboard_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and read analyst feedback labels")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser_ = subparsers.add_parser("build", help="Build supervised-readiness labels")
    build_parser_.add_argument("--config", default="config/scoring.yaml")
    build_parser_.add_argument("--persist", action="store_true")
    build_parser_.add_argument("--limit", type=int, default=None)
    build_parser_.add_argument("--label-version")
    build_parser_.add_argument("--dataset-version")
    build_parser_.add_argument("--no-audit", action="store_true")
    build_parser_.add_argument("--no-artefacts", action="store_true")
    build_parser_.add_argument("--output-dir", default="reports/model_validation")
    build_parser_.set_defaults(func=command_build)

    read_parser = subparsers.add_parser("read", help="Read persisted labels or datasets")
    read_parser.add_argument(
        "kind",
        choices=("case-labels", "account-labels", "case-dataset", "account-dataset"),
    )
    read_parser.add_argument("--label-version")
    read_parser.add_argument("--dataset-version")
    read_parser.add_argument("--label", type=int, choices=(0, 1), default=None)
    read_parser.add_argument("--limit", type=int, default=None)
    read_parser.set_defaults(func=command_read)

    summary_parser = subparsers.add_parser("summary", help="Read label summary")
    summary_parser.add_argument("--limit", type=int, default=None)
    summary_parser.set_defaults(func=command_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = int(args.func(args))
        print("label CLI completed", file=sys.stderr)
        return result
    except LabelError as exc:
        print(f"label CLI failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
