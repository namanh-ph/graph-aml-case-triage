"""CLI for composite account risk scoring and score readback."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import date
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
from graph_aml.scoring import (  # noqa: E402
    AccountRiskScorePersistenceConfig,
    ScoringError,
    build_account_risk_score_quality_summary,
    compute_account_risk_scores_from_inputs,
    generate_account_risk_score_artefacts,
    load_account_risk_scoring_config,
    persist_account_risk_scores,
    read_account_risk_score_summary,
    read_account_risk_scores,
    read_latest_account_risk_scores,
    read_scoring_feature_inputs,
)


def _configure_logging() -> None:
    config = load_app_config()
    configure_logging(
        log_dir=config.paths.paths.logs_dir,
        enable_console=False,
        enable_file=True,
    )


def _logger_context() -> tuple[object, object]:
    _configure_logging()
    return (
        get_logger("graph_aml.scoring.cli"),
        create_run_context(component="scoring", pipeline_stage="account_risk_scoring"),
    )


def _print_summary(summary: dict[str, object]) -> None:
    for key, value in summary.items():
        print(f"{key}={value}")


def _parse_date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


def _apply_score_overrides(config, args: argparse.Namespace):
    values: dict[str, object] = {}
    if args.score_version:
        values["score_version"] = args.score_version
    if args.score_date:
        values["feature_date"] = _parse_date(args.score_date)
    if args.output_dir:
        values["artefact_output_dir"] = args.output_dir
    return replace(config, **values)


def command_account_risk_score(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Account risk scoring started",
            "scoring",
            "account_risk_scoring",
            "started",
            context,
            persist=args.persist,
            limit=args.limit,
        )
        config = _apply_score_overrides(load_account_risk_scoring_config(args.config), args)
        engine = create_database_engine()
        inputs = read_scoring_feature_inputs(engine, config, limit=args.limit)
        log_pipeline_event(
            logger,
            "Scoring inputs read",
            "scoring",
            "account_risk_scoring",
            "completed",
            context,
            account_rows=len(inputs["accounts"]),
            alert_rows=len(inputs["alerts"]),
        )
        scoring_result = compute_account_risk_scores_from_inputs(
            inputs,
            config,
            score_date=config.feature_date,
        )
        log_pipeline_event(
            logger,
            "Account risk scores computed",
            "scoring",
            "account_risk_scoring",
            "completed",
            context,
            **scoring_result.summary,
        )
        persistence_result = None
        if args.persist:
            persistence_config = AccountRiskScorePersistenceConfig(
                score_date=config.feature_date,
                score_name=config.score_name,
                score_version=config.score_version,
                write_audit=not args.no_audit,
            )
            persistence_result = persist_account_risk_scores(
                engine,
                scoring_result,
                persistence_config,
            )
            log_pipeline_event(
                logger,
                "Account risk scores persisted",
                "scoring",
                "account_risk_scoring",
                "completed",
                context,
                **persistence_result.summary,
            )
        if not args.no_artefacts:
            paths = generate_account_risk_score_artefacts(
                scoring_result,
                persistence_result,
                output_dir=args.output_dir or config.artefact_output_dir,
            )
            log_pipeline_event(
                logger,
                "Risk scoring artefacts written",
                "scoring",
                "account_risk_scoring",
                "completed",
                context,
                artefact_count=len(paths),
            )
        summary = {
            **scoring_result.summary,
            "score_name": config.score_name,
            "score_version": config.score_version,
            "persisted": bool(persistence_result and persistence_result.persisted),
        }
        log_pipeline_event(
            logger,
            "Scoring CLI completed",
            "scoring",
            "account_risk_scoring",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except ScoringError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_account_risk_read(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Account risk score read started",
            "scoring",
            "account_risk_scoring",
            "started",
            context,
            latest=args.latest,
        )
        engine = create_database_engine()
        if args.latest:
            frame = read_latest_account_risk_scores(engine, limit=args.limit)
        else:
            frame = read_account_risk_scores(
                engine,
                score_date=args.score_date,
                score_name=args.score_name,
                score_version=args.score_version,
                risk_band=args.risk_band,
                limit=args.limit,
            )
        _print_summary(build_account_risk_score_quality_summary(frame))
        return 0
    except ScoringError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_account_risk_summary(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Account risk score summary requested",
            "scoring",
            "account_risk_scoring",
            "started",
            context,
            limit=args.limit,
        )
        engine = create_database_engine()
        _print_summary(read_account_risk_score_summary(engine))
        return 0
    except ScoringError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def _fail(logger: object, context: object, exc: Exception) -> int:
    log_pipeline_event(
        logger,
        "Scoring CLI failed",
        "scoring",
        "account_risk_scoring",
        "failed",
        context,
        error=str(exc),
    )
    print(f"error={exc}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Composite account risk scoring utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    account_risk = subparsers.add_parser("account-risk", help="Account risk score utilities")
    account_subparsers = account_risk.add_subparsers(dest="account_command", required=True)

    score = account_subparsers.add_parser("score", help="Compute account risk scores")
    score.add_argument("--config", default="config/scoring.yaml")
    score.add_argument("--persist", action="store_true")
    score.add_argument("--limit", type=int)
    score.add_argument("--score-version")
    score.add_argument("--score-date")
    score.add_argument("--no-audit", action="store_true")
    score.add_argument("--no-artefacts", action="store_true")
    score.add_argument("--output-dir", default=None)
    score.set_defaults(func=command_account_risk_score)

    read = account_subparsers.add_parser("read", help="Read account risk scores")
    read.add_argument("--latest", action="store_true")
    read.add_argument("--score-date")
    read.add_argument("--score-name")
    read.add_argument("--score-version")
    read.add_argument("--risk-band", choices=["low", "medium", "high", "critical"])
    read.add_argument("--limit", type=int)
    read.set_defaults(func=command_account_risk_read)

    summary = account_subparsers.add_parser("summary", help="Summarise account risk scores")
    summary.add_argument("--limit", type=int)
    summary.set_defaults(func=command_account_risk_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
