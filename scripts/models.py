"""CLI for model training, anomaly scoring, and score readback."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.database import create_database_engine, dispose_engine  # noqa: E402
from graph_aml.models import (  # noqa: E402
    AnomalyScorePersistenceConfig,
    IsolationForestModelConfig,
    ModelError,
    SupervisedModelConfig,
    SupervisedModelError,
    SupervisedModelPersistenceConfig,
    build_anomaly_score_quality_summary,
    build_model_feature_frame,
    build_supervised_model_quality_summary,
    generate_isolation_forest_artefacts,
    load_isolation_forest_config,
    load_supervised_model_config,
    log_isolation_forest_mlflow_run,
    persist_anomaly_scores,
    read_anomaly_score_summary,
    read_anomaly_scores,
    read_latest_anomaly_scores,
    read_model_feature_inputs,
    read_supervised_model_runs,
    read_supervised_model_scores,
    read_supervised_model_summary,
    train_and_persist_supervised_model,
    train_and_score_isolation_forest,
)
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
        get_logger("graph_aml.models.cli"),
        create_run_context(component="models", pipeline_stage="anomaly_scoring"),
    )


def _print_summary(summary: dict[str, object]) -> None:
    for key, value in summary.items():
        print(f"{key}={value}")


def _apply_train_score_overrides(
    config: IsolationForestModelConfig,
    args: argparse.Namespace,
) -> IsolationForestModelConfig:
    values: dict[str, object] = {}
    if args.model_version:
        values["model_version"] = args.model_version
    if args.contamination is not None:
        values["contamination"] = (
            "auto" if args.contamination == "auto" else float(args.contamination)
        )
    if args.n_estimators is not None:
        values["n_estimators"] = args.n_estimators
    if args.score_percentile_high is not None:
        values["score_percentile_high"] = args.score_percentile_high
    if args.score_percentile_medium is not None:
        values["score_percentile_medium"] = args.score_percentile_medium
    if args.no_graph_features:
        values["use_graph_features"] = False
    if args.no_behavioural_features:
        values["use_behavioural_features"] = False
    if args.no_jurisdiction_features:
        values["use_jurisdiction_features"] = False
    if args.no_mlflow:
        values["mlflow_enabled"] = False
    if args.output_dir:
        values["artefact_output_dir"] = args.output_dir
    return replace(config, **values)


def command_isolation_forest_train_score(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Isolation forest training started",
            "models",
            "anomaly_scoring",
            "started",
            context,
            persist=args.persist,
            limit=args.limit,
        )
        config = _apply_train_score_overrides(load_isolation_forest_config(args.config), args)
        engine = create_database_engine()
        inputs = read_model_feature_inputs(engine, config, limit=args.limit)
        log_pipeline_event(
            logger,
            "Model feature inputs read",
            "models",
            "anomaly_scoring",
            "completed",
            context,
            account_rows=len(inputs["account_features"]),
            graph_rows=len(inputs["graph_features"]),
        )
        feature_frame = build_model_feature_frame(
            inputs["account_features"],
            inputs.get("graph_features"),
            config,
        )
        training_result, score_result = train_and_score_isolation_forest(feature_frame, config)
        log_pipeline_event(
            logger,
            "Isolation forest scoring completed",
            "models",
            "anomaly_scoring",
            "completed",
            context,
            **score_result.summary,
        )
        persistence_result = None
        if args.persist:
            persistence_config = AnomalyScorePersistenceConfig(
                score_date=config.feature_date,
                model_name=config.model_name,
                model_version=config.model_version,
                feature_date=config.feature_date,
                account_feature_version=config.account_feature_version,
                graph_feature_version=config.graph_feature_version,
                graph_build_id=config.graph_build_id,
                write_audit=not args.no_audit,
            )
            persistence_result = persist_anomaly_scores(
                engine,
                score_result,
                training_result,
                persistence_config,
            )
            log_pipeline_event(
                logger,
                "Anomaly scores persisted",
                "models",
                "anomaly_scoring",
                "completed",
                context,
                **persistence_result.summary,
            )
        artefact_paths = {}
        if not args.no_artefacts:
            artefact_paths = generate_isolation_forest_artefacts(
                training_result,
                score_result,
                persistence_result,
                output_dir=args.output_dir or config.artefact_output_dir,
            )
            log_pipeline_event(
                logger,
                "Model artefacts written",
                "models",
                "anomaly_scoring",
                "completed",
                context,
                artefact_count=len(artefact_paths),
            )
        if config.mlflow_enabled:
            run_id = log_isolation_forest_mlflow_run(
                training_result,
                score_result,
                config,
                artefact_paths=artefact_paths,
            )
            log_pipeline_event(
                logger,
                "MLflow run logged",
                "models",
                "anomaly_scoring",
                "completed",
                context,
                mlflow_run_id=run_id,
            )
        summary = {
            **score_result.summary,
            "model_name": training_result.model_name,
            "model_version": training_result.model_version,
            "training_row_count": training_result.training_row_count,
            "feature_count": len(training_result.feature_names),
            "persisted": bool(persistence_result and persistence_result.persisted),
        }
        log_pipeline_event(
            logger,
            "Model CLI completed",
            "models",
            "anomaly_scoring",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except ModelError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_anomaly_scores_read(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Anomaly score read started",
            "models",
            "anomaly_scoring",
            "started",
            context,
            latest=args.latest,
        )
        engine = create_database_engine()
        if args.latest:
            frame = read_latest_anomaly_scores(engine, limit=args.limit)
        else:
            frame = read_anomaly_scores(
                engine,
                score_date=args.score_date,
                model_name=args.model_name,
                model_version=args.model_version,
                model_run_id=args.model_run_id,
                risk_band=args.risk_band,
                limit=args.limit,
            )
        summary = build_anomaly_score_quality_summary(frame)
        _print_summary(summary)
        return 0
    except ModelError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_anomaly_scores_summary(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "Anomaly score summary requested",
            "models",
            "anomaly_scoring",
            "started",
            context,
            limit=args.limit,
        )
        engine = create_database_engine()
        _print_summary(read_anomaly_score_summary(engine))
        return 0
    except ModelError as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def _apply_supervised_overrides(
    config: SupervisedModelConfig,
    args: argparse.Namespace,
) -> SupervisedModelConfig:
    dataset = config.dataset
    persistence = config.persistence
    values: dict[str, object] = {}
    if args.model_family:
        values["model_family"] = args.model_family
    if args.model_version:
        values["model_version"] = args.model_version
    if args.dataset_level or args.dataset_version:
        dataset_level = args.dataset_level or dataset.level
        dataset = replace(
            dataset,
            level=dataset_level,
            dataset_version=args.dataset_version or dataset.dataset_version,
            label_column="account_label" if dataset_level == "account" else "case_label",
            id_column="account_id" if dataset_level == "account" else "case_id",
        )
    if args.no_mlflow or args.output_dir:
        persistence = replace(
            persistence,
            write_mlflow=not args.no_mlflow,
            artefact_output_dir=args.output_dir or persistence.artefact_output_dir,
        )
    return replace(config, dataset=dataset, persistence=persistence, **values)


def command_supervised_train(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "supervised model training started",
            "models",
            "supervised_training",
            "started",
            context,
            persist=args.persist,
            limit=args.limit,
        )
        config = _apply_supervised_overrides(load_supervised_model_config(args.config), args)
        engine = create_database_engine()
        persistence = SupervisedModelPersistenceConfig(
            model_name=config.model_name,
            model_version=config.model_version,
            dataset_version=config.dataset.dataset_version,
            write_scores=args.persist,
            write_model_run=args.persist,
            write_audit=args.persist,
            artefact_output_dir=args.output_dir or config.persistence.artefact_output_dir,
        )
        result, scores, persisted = train_and_persist_supervised_model(
            engine,
            config,
            persistence,
            limit=args.limit,
            write_artefacts=not args.no_artefacts,
        )
        summary = build_supervised_model_quality_summary(result, scores)
        summary["persisted"] = bool(args.persist and persisted.persisted)
        log_pipeline_event(
            logger,
            "supervised CLI completed",
            "models",
            "supervised_training",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except (ModelError, SupervisedModelError) as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_supervised_read_scores(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "supervised model read requested",
            "models",
            "supervised_training",
            "started",
            context,
        )
        engine = create_database_engine()
        frame = read_supervised_model_scores(
            engine,
            entity_level=args.entity_level,
            model_version=args.model_version,
            dataset_version=args.dataset_version,
            predicted_label=args.predicted_label,
            limit=args.limit,
        )
        _print_summary({"row_count": int(len(frame)), "columns": list(frame.columns)})
        return 0
    except (ModelError, SupervisedModelError) as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_supervised_read_runs(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        engine = create_database_engine()
        frame = read_supervised_model_runs(
            engine,
            model_version=args.model_version,
            entity_level=args.entity_level,
            limit=args.limit,
        )
        _print_summary({"row_count": int(len(frame)), "columns": list(frame.columns)})
        return 0
    except (ModelError, SupervisedModelError) as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def command_supervised_summary(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    engine = None
    try:
        log_pipeline_event(
            logger,
            "supervised model summary requested",
            "models",
            "supervised_training",
            "started",
            context,
            limit=args.limit,
        )
        engine = create_database_engine()
        _print_summary(read_supervised_model_summary(engine))
        return 0
    except (ModelError, SupervisedModelError) as exc:
        return _fail(logger, context, exc)
    finally:
        dispose_engine(engine)


def _fail(logger: object, context: object, exc: Exception) -> int:
    log_pipeline_event(
        logger,
        "Model CLI failed",
        "models",
        "anomaly_scoring",
        "failed",
        context,
        error=str(exc),
    )
    print(f"error={exc}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Model training and anomaly score utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    isolation = subparsers.add_parser("isolation-forest", help="Isolation Forest utilities")
    isolation_subparsers = isolation.add_subparsers(dest="isolation_command", required=True)
    train_score = isolation_subparsers.add_parser(
        "train-score",
        help="Train and score account Isolation Forest model",
    )
    train_score.add_argument("--config", default="config/model.yaml")
    train_score.add_argument("--persist", action="store_true")
    train_score.add_argument("--limit", type=int)
    train_score.add_argument("--model-version")
    train_score.add_argument("--contamination")
    train_score.add_argument("--n-estimators", type=int)
    train_score.add_argument("--score-percentile-high", type=float)
    train_score.add_argument("--score-percentile-medium", type=float)
    train_score.add_argument("--no-graph-features", action="store_true")
    train_score.add_argument("--no-behavioural-features", action="store_true")
    train_score.add_argument("--no-jurisdiction-features", action="store_true")
    train_score.add_argument("--no-mlflow", action="store_true")
    train_score.add_argument("--no-audit", action="store_true")
    train_score.add_argument("--no-artefacts", action="store_true")
    train_score.add_argument("--output-dir", default=None)
    train_score.set_defaults(func=command_isolation_forest_train_score)

    anomaly = subparsers.add_parser("anomaly-scores", help="Anomaly score readback utilities")
    anomaly_subparsers = anomaly.add_subparsers(dest="anomaly_command", required=True)
    read = anomaly_subparsers.add_parser("read", help="Read anomaly scores")
    read.add_argument("--latest", action="store_true")
    read.add_argument("--score-date")
    read.add_argument("--model-name")
    read.add_argument("--model-version")
    read.add_argument("--model-run-id")
    read.add_argument("--risk-band", choices=["low", "medium", "high"])
    read.add_argument("--limit", type=int)
    read.set_defaults(func=command_anomaly_scores_read)

    summary = anomaly_subparsers.add_parser("summary", help="Summarise anomaly scores")
    summary.add_argument("--limit", type=int)
    summary.set_defaults(func=command_anomaly_scores_summary)

    supervised = subparsers.add_parser("supervised", help="Supervised AML model utilities")
    supervised_subparsers = supervised.add_subparsers(dest="supervised_command", required=True)
    supervised_train = supervised_subparsers.add_parser(
        "train",
        help="Train supervised AML baseline model",
    )
    supervised_train.add_argument("--config", default="config/model.yaml")
    supervised_train.add_argument("--persist", action="store_true")
    supervised_train.add_argument("--limit", type=int)
    supervised_train.add_argument(
        "--model-family",
        choices=["logistic_regression", "random_forest"],
    )
    supervised_train.add_argument("--model-version")
    supervised_train.add_argument("--dataset-level", choices=["case", "account"])
    supervised_train.add_argument("--dataset-version")
    supervised_train.add_argument("--no-mlflow", action="store_true")
    supervised_train.add_argument("--no-artefacts", action="store_true")
    supervised_train.add_argument("--output-dir", default=None)
    supervised_train.set_defaults(func=command_supervised_train)

    read_scores = supervised_subparsers.add_parser("read-scores", help="Read supervised scores")
    read_scores.add_argument("--entity-level", choices=["case", "account"])
    read_scores.add_argument("--model-version")
    read_scores.add_argument("--dataset-version")
    read_scores.add_argument("--predicted-label", type=int, choices=[0, 1])
    read_scores.add_argument("--limit", type=int)
    read_scores.set_defaults(func=command_supervised_read_scores)

    read_runs = supervised_subparsers.add_parser("read-runs", help="Read supervised model runs")
    read_runs.add_argument("--model-version")
    read_runs.add_argument("--entity-level", choices=["case", "account"])
    read_runs.add_argument("--limit", type=int)
    read_runs.set_defaults(func=command_supervised_read_runs)

    supervised_summary = supervised_subparsers.add_parser(
        "summary",
        help="Summarise supervised model outputs",
    )
    supervised_summary.add_argument("--limit", type=int)
    supervised_summary.set_defaults(func=command_supervised_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
