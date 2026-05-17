"""CLI for AML case generation and case readback."""

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

from graph_aml.cases import (  # noqa: E402
    CaseError,
    CaseEvidencePersistenceConfig,
    CaseLifecyclePersistenceConfig,
    CasePersistenceConfig,
    CaseRiskScorePersistenceConfig,
    apply_case_lifecycle_action,
    build_assignment_action,
    build_case_evidence_packs,
    build_case_generation_quality_summary,
    build_case_risk_score_quality_summary,
    build_comment_action,
    build_status_change_action,
    compute_case_risk_scores_from_inputs,
    generate_case_evidence_artefacts,
    generate_case_generation_artefacts,
    generate_case_lifecycle_artefacts,
    generate_case_risk_score_artefacts,
    generate_cases_from_inputs,
    load_case_evidence_config,
    load_case_generation_config,
    load_case_lifecycle_config,
    load_case_risk_scoring_config,
    persist_case_evidence,
    persist_case_risk_scores,
    persist_cases,
    read_case_assignments,
    read_case_current_status,
    read_case_detail,
    read_case_evidence_inputs,
    read_case_evidence_packs,
    read_case_evidence_summary,
    read_case_explanations,
    read_case_inputs,
    read_case_lifecycle_events,
    read_case_lifecycle_summary,
    read_case_risk_inputs,
    read_case_risk_score_summary,
    read_case_risk_scores,
    read_case_summary,
    read_cases,
    read_latest_case_risk_scores,
)
from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.database import create_database_engine, dispose_engine  # noqa: E402
from graph_aml.observability import (  # noqa: E402
    configure_logging,
    create_run_context,
    get_logger,
    log_pipeline_event,
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
        get_logger("graph_aml.cases.cli"),
        create_run_context(component="cases", pipeline_stage="case_generation"),
    )


def _print_summary(summary: dict[str, object]) -> None:
    for key, value in summary.items():
        print(f"{key}={value}")


def _apply_generate_overrides(config, args: argparse.Namespace):
    values: dict[str, object] = {}
    if args.case_version:
        values["case_version"] = args.case_version
    if args.output_dir:
        values["artefact_output_dir"] = args.output_dir
    return replace(config, **values)


def _parse_date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


def _apply_risk_overrides(config, args: argparse.Namespace):
    values: dict[str, object] = {}
    if args.score_version:
        values["score_version"] = args.score_version
    if args.output_dir:
        values["artefact_output_dir"] = args.output_dir
    return replace(config, **values)


def _apply_evidence_overrides(config, args: argparse.Namespace):
    values: dict[str, object] = {}
    if args.evidence_version:
        values["evidence_version"] = args.evidence_version
    if args.explanation_version:
        values["explanation_version"] = args.explanation_version
    if args.output_dir:
        values["artefact_output_dir"] = args.output_dir
    return replace(config, **values)


def command_generate(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case generation started",
            "cases",
            "case_generation",
            "started",
            context,
            persist=args.persist,
            limit=args.limit,
        )
        config = _apply_generate_overrides(load_case_generation_config(args.config), args)
        engine = create_database_engine()
        inputs = read_case_inputs(engine, config, limit=args.limit)
        log_pipeline_event(
            logger,
            "Case inputs read",
            "cases",
            "case_generation",
            "completed",
            context,
            alert_rows=len(inputs["alerts"]),
        )
        generation_result = generate_cases_from_inputs(inputs, config)
        log_pipeline_event(
            logger,
            "Cases generated",
            "cases",
            "case_generation",
            "completed",
            context,
            **generation_result.summary,
        )
        persistence_result = None
        if args.persist:
            persistence_result = persist_cases(
                engine,
                generation_result,
                CasePersistenceConfig(
                    case_version=config.case_version,
                    write_audit=not args.no_audit,
                ),
            )
            log_pipeline_event(
                logger,
                "Cases persisted",
                "cases",
                "case_generation",
                "completed",
                context,
                **persistence_result.summary,
            )
        if not args.no_artefacts:
            paths = generate_case_generation_artefacts(
                generation_result,
                persistence_result,
                output_dir=args.output_dir or config.artefact_output_dir,
            )
            log_pipeline_event(
                logger,
                "Case generation artefacts written",
                "cases",
                "case_generation",
                "completed",
                context,
                artefact_count=len(paths),
            )
        summary = {
            **generation_result.summary,
            "case_version": config.case_version,
            "persisted": bool(persistence_result and persistence_result.persisted),
        }
        log_pipeline_event(
            logger,
            "Case CLI completed",
            "cases",
            "case_generation",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_read(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case read started",
            "cases",
            "case_generation",
            "started",
            context,
        )
        engine = create_database_engine()
        frame = read_cases(
            engine,
            status=args.status,
            severity=args.severity,
            case_version=args.case_version,
            account_id=args.account_id,
            customer_id=args.customer_id,
            limit=args.limit,
        )
        _print_summary(
            build_case_generation_quality_summary(
                type("CaseRows", (), {"cases": frame, "case_alerts": frame})()
            )
        )
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_detail(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case detail requested",
            "cases",
            "case_generation",
            "started",
            context,
            case_id=args.case_id,
        )
        engine = create_database_engine()
        detail = read_case_detail(engine, args.case_id)
        _print_summary(
            {
                "case_rows": len(detail["case"]),
                "case_alert_links": len(detail["alerts"]),
                "case_entity_links": len(detail["entities"]),
            }
        )
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_summary(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case summary requested",
            "cases",
            "case_generation",
            "started",
            context,
            limit=args.limit,
        )
        engine = create_database_engine()
        _print_summary(read_case_summary(engine))
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_risk_score(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case risk scoring started",
            "cases",
            "case_risk_scoring",
            "started",
            context,
            persist=args.persist,
            limit=args.limit,
        )
        config = _apply_risk_overrides(load_case_risk_scoring_config(args.config), args)
        engine = create_database_engine()
        inputs = read_case_risk_inputs(engine, config, limit=args.limit)
        log_pipeline_event(
            logger,
            "Case risk inputs read",
            "cases",
            "case_risk_scoring",
            "completed",
            context,
            case_rows=len(inputs["cases"]),
        )
        scoring_result = compute_case_risk_scores_from_inputs(
            inputs,
            config,
            score_date=_parse_date(args.score_date),
        )
        log_pipeline_event(
            logger,
            "Case risk scores computed",
            "cases",
            "case_risk_scoring",
            "completed",
            context,
            **scoring_result.summary,
        )
        persistence_result = None
        if args.persist:
            persistence_result = persist_case_risk_scores(
                engine,
                scoring_result,
                CaseRiskScorePersistenceConfig(
                    score_date=_parse_date(args.score_date),
                    score_name=config.score_name,
                    score_version=config.score_version,
                    write_audit=not args.no_audit,
                    update_case_snapshot=not args.no_case_snapshot,
                ),
            )
            log_pipeline_event(
                logger,
                "Case risk scores persisted",
                "cases",
                "case_risk_scoring",
                "completed",
                context,
                **persistence_result.summary,
            )
        if not args.no_artefacts:
            paths = generate_case_risk_score_artefacts(
                scoring_result,
                persistence_result,
                output_dir=args.output_dir or config.artefact_output_dir,
            )
            log_pipeline_event(
                logger,
                "Case risk scoring artefacts written",
                "cases",
                "case_risk_scoring",
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
            "Case CLI completed",
            "cases",
            "case_risk_scoring",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_risk_read(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case risk score read started",
            "cases",
            "case_risk_scoring",
            "started",
            context,
            latest=args.latest,
        )
        engine = create_database_engine()
        if args.latest:
            frame = read_latest_case_risk_scores(engine, limit=args.limit)
        else:
            frame = read_case_risk_scores(
                engine,
                score_date=args.score_date,
                score_name=args.score_name,
                score_version=args.score_version,
                risk_band=args.risk_band,
                limit=args.limit,
            )
        _print_summary(build_case_risk_score_quality_summary(frame))
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_risk_summary(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case risk score summary requested",
            "cases",
            "case_risk_scoring",
            "started",
            context,
            limit=args.limit,
        )
        engine = create_database_engine()
        _print_summary(read_case_risk_score_summary(engine))
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_evidence_build(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case evidence build started",
            "cases",
            "case_evidence",
            "started",
            context,
            persist=args.persist,
            limit=args.limit,
            case_id=args.case_id,
        )
        config = _apply_evidence_overrides(load_case_evidence_config(args.config), args)
        engine = create_database_engine()
        case_ids = (args.case_id,) if args.case_id else None
        inputs = read_case_evidence_inputs(engine, config, case_ids=case_ids, limit=args.limit)
        log_pipeline_event(
            logger,
            "Case evidence inputs read",
            "cases",
            "case_evidence",
            "completed",
            context,
            case_rows=len(inputs["cases"]),
        )
        build_result = build_case_evidence_packs(inputs, config)
        log_pipeline_event(
            logger,
            "Case evidence packs built",
            "cases",
            "case_evidence",
            "completed",
            context,
            **build_result.summary,
        )
        persistence_result = None
        if args.persist:
            persistence_result = persist_case_evidence(
                engine,
                build_result,
                CaseEvidencePersistenceConfig(
                    evidence_version=config.evidence_version,
                    explanation_version=config.explanation_version,
                    write_audit=not args.no_audit,
                ),
            )
            log_pipeline_event(
                logger,
                "Case evidence persisted",
                "cases",
                "case_evidence",
                "completed",
                context,
                **persistence_result.summary,
            )
        if not args.no_artefacts:
            paths = generate_case_evidence_artefacts(
                build_result,
                persistence_result,
                output_dir=args.output_dir or config.artefact_output_dir,
            )
            log_pipeline_event(
                logger,
                "Case evidence artefacts written",
                "cases",
                "case_evidence",
                "completed",
                context,
                artefact_count=len(paths),
            )
        summary = {
            **build_result.summary,
            "evidence_version": config.evidence_version,
            "explanation_version": config.explanation_version,
            "persisted": bool(persistence_result and persistence_result.persisted),
        }
        _print_summary(summary)
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_evidence_read(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case evidence read started",
            "cases",
            "case_evidence",
            "started",
            context,
            case_id=args.case_id,
        )
        engine = create_database_engine()
        packs = read_case_evidence_packs(
            engine,
            case_id=args.case_id,
            evidence_version=args.evidence_version,
            limit=args.limit,
        )
        explanations = read_case_explanations(
            engine,
            case_id=args.case_id,
            explanation_version=args.explanation_version,
            limit=args.limit,
        )
        _print_summary(
            {
                "evidence_pack_count": len(packs),
                "explanation_count": len(explanations),
            }
        )
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_evidence_summary(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case evidence summary requested",
            "cases",
            "case_evidence",
            "started",
            context,
            limit=args.limit,
        )
        engine = create_database_engine()
        _print_summary(read_case_evidence_summary(engine))
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def _lifecycle_persistence_config(args: argparse.Namespace) -> CaseLifecyclePersistenceConfig:
    config = load_case_lifecycle_config(args.config)
    return CaseLifecyclePersistenceConfig(
        lifecycle_version=config.lifecycle_version,
        write_audit=not args.no_audit,
    )


def command_lifecycle_status(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case lifecycle action started",
            "cases",
            "case_lifecycle",
            "started",
            context,
            case_id=args.case_id,
            to_status=args.to_status,
        )
        config = load_case_lifecycle_config(args.config)
        persistence_config = _lifecycle_persistence_config(args)
        engine = create_database_engine()
        current_status = read_case_current_status(engine, args.case_id)
        if current_status is None:
            raise CaseError(f"case_id not found: {args.case_id}")
        action = build_status_change_action(
            args.case_id,
            current_status,
            args.to_status,
            analyst_id=args.analyst_id,
            decision_reason=args.decision_reason,
            comment=args.comment,
            config=config,
        )
        result = apply_case_lifecycle_action(
            engine,
            action,
            config,
            persistence_config,
        )
        log_pipeline_event(
            logger,
            "Case lifecycle action persisted",
            "cases",
            "case_lifecycle",
            "completed",
            context,
            action_id=result.action_id,
        )
        _print_summary(result.__dict__)
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_lifecycle_assign(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case lifecycle action started",
            "cases",
            "case_lifecycle",
            "started",
            context,
            case_id=args.case_id,
            assigned_to=args.assigned_to,
        )
        config = load_case_lifecycle_config(args.config)
        persistence_config = _lifecycle_persistence_config(args)
        engine = create_database_engine()
        action = build_assignment_action(
            args.case_id,
            args.assigned_to,
            analyst_id=args.analyst_id,
            queue=args.queue,
            comment=args.comment,
            config=config,
        )
        result = apply_case_lifecycle_action(engine, action, config, persistence_config)
        _print_summary(result.__dict__)
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_lifecycle_comment(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case lifecycle action started",
            "cases",
            "case_lifecycle",
            "started",
            context,
            case_id=args.case_id,
        )
        config = load_case_lifecycle_config(args.config)
        persistence_config = _lifecycle_persistence_config(args)
        engine = create_database_engine()
        action = build_comment_action(
            args.case_id,
            analyst_id=args.analyst_id,
            comment=args.comment,
            config=config,
        )
        result = apply_case_lifecycle_action(engine, action, config, persistence_config)
        _print_summary(result.__dict__)
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_lifecycle_events(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case lifecycle events requested",
            "cases",
            "case_lifecycle",
            "started",
            context,
        )
        engine = create_database_engine()
        events = read_case_lifecycle_events(
            engine,
            case_id=args.case_id,
            analyst_id=args.analyst_id,
            action_type=args.action_type,
            limit=args.limit,
        )
        if args.write_artefacts:
            generate_case_lifecycle_artefacts(events, output_dir=args.output_dir)
        _print_summary({"event_count": len(events)})
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_lifecycle_assignments(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case lifecycle assignments requested",
            "cases",
            "case_lifecycle",
            "started",
            context,
        )
        engine = create_database_engine()
        assignments = read_case_assignments(
            engine,
            assigned_to=args.assigned_to,
            queue=args.queue,
            limit=args.limit,
        )
        if args.write_artefacts:
            generate_case_lifecycle_artefacts(
                read_case_lifecycle_events(engine, limit=0),
                assignments,
                output_dir=args.output_dir,
            )
        _print_summary({"assignment_count": len(assignments)})
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_lifecycle_summary(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Case lifecycle summary requested",
            "cases",
            "case_lifecycle",
            "started",
            context,
        )
        engine = create_database_engine()
        summary = read_case_lifecycle_summary(engine)
        if args.write_artefacts:
            generate_case_lifecycle_artefacts(
                read_case_lifecycle_events(engine, limit=0),
                summary=summary,
                output_dir=args.output_dir,
            )
        _print_summary(summary)
        return 0
    except CaseError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def _fail(logger: object, context: object, exc: Exception) -> int:
    log_pipeline_event(
        logger,
        "Case CLI failed",
        "cases",
        "case_generation",
        "failed",
        context,
        error=str(exc),
    )
    print(f"error={exc}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AML case generation utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate AML investigation cases")
    generate.add_argument("--config", default="config/scoring.yaml")
    generate.add_argument("--persist", action="store_true")
    generate.add_argument("--limit", type=int)
    generate.add_argument("--case-version")
    generate.add_argument("--no-audit", action="store_true")
    generate.add_argument("--no-artefacts", action="store_true")
    generate.add_argument("--output-dir", default=None)
    generate.set_defaults(func=command_generate)

    read = subparsers.add_parser("read", help="Read generated cases")
    read.add_argument("--status")
    read.add_argument("--severity")
    read.add_argument("--case-version")
    read.add_argument("--account-id")
    read.add_argument("--customer-id")
    read.add_argument("--limit", type=int)
    read.set_defaults(func=command_read)

    detail = subparsers.add_parser("detail", help="Read one case detail bundle")
    detail.add_argument("--case-id", required=True)
    detail.set_defaults(func=command_detail)

    summary = subparsers.add_parser("summary", help="Summarise generated cases")
    summary.add_argument("--limit", type=int)
    summary.set_defaults(func=command_summary)

    risk_score = subparsers.add_parser("risk-score", help="Compute case risk scores")
    risk_score.add_argument("--config", default="config/scoring.yaml")
    risk_score.add_argument("--persist", action="store_true")
    risk_score.add_argument("--limit", type=int)
    risk_score.add_argument("--score-version")
    risk_score.add_argument("--score-date")
    risk_score.add_argument("--no-audit", action="store_true")
    risk_score.add_argument("--no-artefacts", action="store_true")
    risk_score.add_argument("--no-case-snapshot", action="store_true")
    risk_score.add_argument("--output-dir", default=None)
    risk_score.set_defaults(func=command_risk_score)

    risk_read = subparsers.add_parser("risk-read", help="Read case risk scores")
    risk_read.add_argument("--latest", action="store_true")
    risk_read.add_argument("--score-date")
    risk_read.add_argument("--score-name")
    risk_read.add_argument("--score-version")
    risk_read.add_argument("--risk-band", choices=["low", "medium", "high", "critical"])
    risk_read.add_argument("--limit", type=int)
    risk_read.set_defaults(func=command_risk_read)

    risk_summary = subparsers.add_parser("risk-summary", help="Summarise case risk scores")
    risk_summary.add_argument("--limit", type=int)
    risk_summary.set_defaults(func=command_risk_summary)

    evidence_build = subparsers.add_parser("evidence-build", help="Build case evidence packs")
    evidence_build.add_argument("--config", default="config/scoring.yaml")
    evidence_build.add_argument("--persist", action="store_true")
    evidence_build.add_argument("--case-id")
    evidence_build.add_argument("--limit", type=int)
    evidence_build.add_argument("--evidence-version")
    evidence_build.add_argument("--explanation-version")
    evidence_build.add_argument("--no-audit", action="store_true")
    evidence_build.add_argument("--no-artefacts", action="store_true")
    evidence_build.add_argument("--output-dir", default=None)
    evidence_build.set_defaults(func=command_evidence_build)

    evidence_read = subparsers.add_parser("evidence-read", help="Read case evidence packs")
    evidence_read.add_argument("--case-id")
    evidence_read.add_argument("--evidence-version")
    evidence_read.add_argument("--explanation-version")
    evidence_read.add_argument("--limit", type=int)
    evidence_read.set_defaults(func=command_evidence_read)

    evidence_summary = subparsers.add_parser("evidence-summary", help="Summarise case evidence")
    evidence_summary.add_argument("--limit", type=int)
    evidence_summary.set_defaults(func=command_evidence_summary)

    lifecycle = subparsers.add_parser("lifecycle", help="Manage case lifecycle actions")
    lifecycle_subparsers = lifecycle.add_subparsers(dest="lifecycle_command", required=True)

    lifecycle_status = lifecycle_subparsers.add_parser("status", help="Change case status")
    lifecycle_status.add_argument("--config", default="config/scoring.yaml")
    lifecycle_status.add_argument("--case-id", required=True)
    lifecycle_status.add_argument("--to-status", required=True)
    lifecycle_status.add_argument("--analyst-id")
    lifecycle_status.add_argument("--decision-reason")
    lifecycle_status.add_argument("--comment")
    lifecycle_status.add_argument("--no-audit", action="store_true")
    lifecycle_status.set_defaults(func=command_lifecycle_status)

    lifecycle_assign = lifecycle_subparsers.add_parser("assign", help="Assign a case")
    lifecycle_assign.add_argument("--config", default="config/scoring.yaml")
    lifecycle_assign.add_argument("--case-id", required=True)
    lifecycle_assign.add_argument("--assigned-to", required=True)
    lifecycle_assign.add_argument("--analyst-id")
    lifecycle_assign.add_argument("--queue")
    lifecycle_assign.add_argument("--comment")
    lifecycle_assign.add_argument("--no-audit", action="store_true")
    lifecycle_assign.set_defaults(func=command_lifecycle_assign)

    lifecycle_comment = lifecycle_subparsers.add_parser("comment", help="Add a case comment")
    lifecycle_comment.add_argument("--config", default="config/scoring.yaml")
    lifecycle_comment.add_argument("--case-id", required=True)
    lifecycle_comment.add_argument("--analyst-id")
    lifecycle_comment.add_argument("--comment", required=True)
    lifecycle_comment.add_argument("--no-audit", action="store_true")
    lifecycle_comment.set_defaults(func=command_lifecycle_comment)

    lifecycle_events = lifecycle_subparsers.add_parser("events", help="Read lifecycle events")
    lifecycle_events.add_argument("--case-id")
    lifecycle_events.add_argument("--analyst-id")
    lifecycle_events.add_argument("--action-type")
    lifecycle_events.add_argument("--limit", type=int)
    lifecycle_events.add_argument("--output-dir", default="reports/model_validation")
    lifecycle_events.add_argument("--write-artefacts", action="store_true")
    lifecycle_events.set_defaults(func=command_lifecycle_events)

    lifecycle_assignments = lifecycle_subparsers.add_parser(
        "assignments", help="Read case assignments"
    )
    lifecycle_assignments.add_argument("--assigned-to")
    lifecycle_assignments.add_argument("--queue")
    lifecycle_assignments.add_argument("--limit", type=int)
    lifecycle_assignments.add_argument("--output-dir", default="reports/model_validation")
    lifecycle_assignments.add_argument("--write-artefacts", action="store_true")
    lifecycle_assignments.set_defaults(func=command_lifecycle_assignments)

    lifecycle_summary = lifecycle_subparsers.add_parser("summary", help="Summarise lifecycle")
    lifecycle_summary.add_argument("--output-dir", default="reports/model_validation")
    lifecycle_summary.add_argument("--write-artefacts", action="store_true")
    lifecycle_summary.set_defaults(func=command_lifecycle_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
