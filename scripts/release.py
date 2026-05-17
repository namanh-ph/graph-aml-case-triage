"""CLI for release readiness and portfolio evidence packaging."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from sqlalchemy import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.database import create_database_engine, dispose_engine  # noqa: E402
from graph_aml.release import (  # noqa: E402
    ReleaseReadinessConfig,
    ReleaseReadinessError,
    load_release_readiness_config,
    read_release_artefact_checks,
    read_release_evidence_index,
    read_release_portfolio_pack,
    read_release_readiness_runs,
    read_release_readiness_summary,
    read_release_repository_checks,
    run_and_persist_release_readiness,
)
from graph_aml.release.persistence import ReleasePersistenceConfig  # noqa: E402


def _print_summary(summary: dict[str, object]) -> None:
    for key, value in summary.items():
        print(f"{key}={value}")


def _apply_run_overrides(
    config: ReleaseReadinessConfig,
    args: argparse.Namespace,
) -> ReleaseReadinessConfig:
    persistence = replace(
        config.persistence,
        write_database=bool(args.persist),
        write_artefacts=not args.no_artefacts,
        artefact_output_dir=args.output_dir or config.persistence.artefact_output_dir,
    )
    if args.release_version:
        return replace(config, release_version=args.release_version, persistence=persistence)
    return replace(config, persistence=persistence)


def command_readiness_run(args: argparse.Namespace) -> int:
    engine: Engine | None = None
    try:
        print("release readiness started")
        config = _apply_run_overrides(load_release_readiness_config(args.config), args)
        persistence = ReleasePersistenceConfig(
            release_name=config.release_name,
            release_version=config.release_version,
            write_audit=args.persist and config.persistence.write_audit,
        )
        if not args.local_only:
            engine = create_database_engine()
        result, persisted = run_and_persist_release_readiness(
            engine,
            config,
            persistence,
            write_artefacts=not args.no_artefacts,
        )
        print("release CLI completed")
        _print_summary(
            {
                **result.summary,
                "persisted": bool(args.persist and persisted and persisted.persisted),
                "release_run_id": result.release_run_id,
            }
        )
        return 0
    except ReleaseReadinessError as exc:
        print(f"release CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            dispose_engine(engine)


def _read_frame_command(args: argparse.Namespace, reader: object, **kwargs: object) -> int:
    engine: Engine | None = None
    try:
        print("release read requested")
        engine = create_database_engine()
        frame = reader(engine, limit=args.limit, **kwargs)  # type: ignore[operator]
        _print_summary({"row_count": int(len(frame)), "columns": list(frame.columns)})
        return 0
    except ReleaseReadinessError as exc:
        print(f"release CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            dispose_engine(engine)


def command_read_runs(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_release_readiness_runs,
        release_version=args.release_version,
    )


def command_read_checks(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_release_repository_checks,
        release_run_id=args.release_run_id,
        status=args.status,
    )


def command_read_artefacts(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_release_artefact_checks,
        release_run_id=args.release_run_id,
        status=args.status,
    )


def command_read_evidence(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_release_evidence_index,
        release_run_id=args.release_run_id,
        evidence_type=args.evidence_type,
    )


def command_read_portfolio(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_release_portfolio_pack,
        release_run_id=args.release_run_id,
    )


def command_summary(args: argparse.Namespace) -> int:
    engine: Engine | None = None
    try:
        print("release summary requested")
        engine = create_database_engine()
        _print_summary(read_release_readiness_summary(engine))
        return 0
    except ReleaseReadinessError as exc:
        print(f"release CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Release readiness utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    readiness = subparsers.add_parser("readiness", help="Release readiness")
    readiness_sub = readiness.add_subparsers(dest="readiness_command", required=True)

    run = readiness_sub.add_parser("run", help="Run release readiness checks")
    run.add_argument("--config", default="config/release.yaml")
    run.add_argument("--persist", action="store_true")
    run.add_argument("--release-version")
    run.add_argument("--no-artefacts", action="store_true")
    run.add_argument("--output-dir")
    run.add_argument("--local-only", action="store_true")
    run.set_defaults(func=command_readiness_run)

    read_runs = readiness_sub.add_parser("read-runs", help="Read release readiness runs")
    read_runs.add_argument("--release-version")
    read_runs.add_argument("--limit", type=int)
    read_runs.set_defaults(func=command_read_runs)

    read_checks = readiness_sub.add_parser("read-checks", help="Read release check rows")
    read_checks.add_argument("--release-run-id")
    read_checks.add_argument("--status")
    read_checks.add_argument("--limit", type=int)
    read_checks.set_defaults(func=command_read_checks)

    read_artefacts = readiness_sub.add_parser("read-artefacts", help="Read release artefacts")
    read_artefacts.add_argument("--release-run-id")
    read_artefacts.add_argument("--status")
    read_artefacts.add_argument("--limit", type=int)
    read_artefacts.set_defaults(func=command_read_artefacts)

    read_evidence = readiness_sub.add_parser("read-evidence", help="Read release evidence index")
    read_evidence.add_argument("--release-run-id")
    read_evidence.add_argument("--evidence-type")
    read_evidence.add_argument("--limit", type=int)
    read_evidence.set_defaults(func=command_read_evidence)

    read_portfolio = readiness_sub.add_parser("read-portfolio", help="Read portfolio pack")
    read_portfolio.add_argument("--release-run-id")
    read_portfolio.add_argument("--limit", type=int)
    read_portfolio.set_defaults(func=command_read_portfolio)

    summary = readiness_sub.add_parser("summary", help="Read release summary")
    summary.add_argument("--limit", type=int)
    summary.set_defaults(func=command_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
