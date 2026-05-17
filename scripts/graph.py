"""CLI for Neo4j graph connection utilities."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.database import create_database_engine, dispose_engine  # noqa: E402
from graph_aml.graph import (  # noqa: E402
    GraphAnalyticsConfig,
    GraphError,
    GraphFeaturePersistenceConfig,
    build_graph_feature_quality_summary,
    close_neo4j_driver,
    collect_graph_counts,
    collect_neo4j_health_summary,
    compute_graph_analytics_features_from_neo4j,
    create_verified_neo4j_driver,
    ensure_graph_constraints,
    generate_graph_analytics_artefacts,
    generate_graph_feature_persistence_artefacts,
    generate_graph_load_artefacts,
    list_graph_constraints,
    load_graph_analytics_config,
    load_graph_from_staged,
    load_neo4j_config,
    neo4j_config_from_mapping,
    persist_graph_features,
    read_graph_feature_summary,
    read_graph_features,
    read_latest_graph_features,
    reconcile_graph_load,
    summarise_graph_constraints,
    summarise_neo4j_health,
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
        get_logger("graph_aml.graph.cli"),
        create_run_context(component="graph", pipeline_stage="neo4j"),
    )


def _safe_config_summary(config_path: str) -> dict[str, object]:
    try:
        config = load_neo4j_config(config_path)
    except GraphError:
        config = neo4j_config_from_mapping({})
        if os.getenv("NEO4J_URI"):
            config = neo4j_config_from_mapping(
                {
                    "uri": os.getenv("NEO4J_URI"),
                    "username": os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER"),
                    "database": os.getenv("NEO4J_DATABASE"),
                    "password": os.getenv("NEO4J_PASSWORD"),
                }
            )
    password_present = bool(getattr(config, "password", None))
    return {
        "uri": config.uri,
        "username": config.username,
        "database": config.database,
        "encrypted": config.encrypted,
        "connection_timeout_seconds": config.connection_timeout_seconds,
        "max_connection_lifetime_seconds": config.max_connection_lifetime_seconds,
        "max_connection_pool_size": config.max_connection_pool_size,
        "password_configured": password_present,
    }


def _print_summary(summary: dict[str, object]) -> None:
    for key, value in summary.items():
        print(f"{key}={value}")


def command_config(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    try:
        summary = _safe_config_summary(args.config)
        log_pipeline_event(
            logger,
            "Graph config requested",
            "graph",
            "neo4j",
            "completed",
            context,
            password_configured=summary["password_configured"],
        )
        _print_summary(summary)
        return 0
    except GraphError as exc:
        return _fail(logger, context, exc)


def command_health(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    driver = None
    try:
        log_pipeline_event(
            logger,
            "Neo4j health check started",
            "graph",
            "neo4j",
            "started",
            context,
        )
        config = load_neo4j_config(args.config)
        database = args.database or config.database
        driver = create_verified_neo4j_driver(config)
        summary = summarise_neo4j_health(collect_neo4j_health_summary(driver, database))
        log_pipeline_event(
            logger,
            "Neo4j health check completed",
            "graph",
            "neo4j",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except GraphError as exc:
        return _fail(logger, context, exc)
    finally:
        close_neo4j_driver(driver)


def command_constraints_list(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    driver = None
    try:
        log_pipeline_event(
            logger,
            "Neo4j constraint listing started",
            "graph",
            "neo4j",
            "started",
            context,
        )
        config = load_neo4j_config(args.config)
        database = args.database or config.database
        driver = create_verified_neo4j_driver(config)
        summary = summarise_graph_constraints(list_graph_constraints(driver, database))
        log_pipeline_event(
            logger,
            "Neo4j constraint listing completed",
            "graph",
            "neo4j",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except GraphError as exc:
        return _fail(logger, context, exc)
    finally:
        close_neo4j_driver(driver)


def command_constraints_ensure(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    driver = None
    try:
        log_pipeline_event(
            logger,
            "Neo4j constraint ensure started",
            "graph",
            "neo4j",
            "started",
            context,
        )
        config = load_neo4j_config(args.config)
        database = args.database or config.database
        driver = create_verified_neo4j_driver(config)
        summary = ensure_graph_constraints(driver, database=database)
        log_pipeline_event(
            logger,
            "Neo4j constraint ensure completed",
            "graph",
            "neo4j",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except GraphError as exc:
        return _fail(logger, context, exc)
    finally:
        close_neo4j_driver(driver)


def command_load(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    postgres_engine = None
    driver = None
    try:
        log_pipeline_event(
            logger,
            "Graph load started",
            "graph",
            "neo4j",
            "started",
            context,
            limit=args.limit,
            include_alerts=not args.no_alerts,
        )
        graph_config = load_neo4j_config(args.config)
        database = args.database or graph_config.database
        postgres_engine = create_database_engine()
        driver = create_verified_neo4j_driver(graph_config)
        result = load_graph_from_staged(
            postgres_engine,
            driver,
            limit=args.limit,
            include_alerts=not args.no_alerts,
            database=database,
            batch_size=args.batch_size,
            ensure_constraints_first=not args.no_constraints,
        )
        log_pipeline_event(
            logger,
            "Graph inputs read",
            "graph",
            "neo4j",
            "completed",
            context,
            limit=args.limit,
        )
        if not args.no_constraints:
            log_pipeline_event(
                logger,
                "Graph constraints ensured",
                "graph",
                "neo4j",
                "completed",
                context,
                constraints_attempted=result.constraints_attempted,
            )
        log_pipeline_event(
            logger,
            "Graph nodes loaded",
            "graph",
            "neo4j",
            "completed",
            context,
            **result.nodes_loaded,
        )
        log_pipeline_event(
            logger,
            "Graph relationships loaded",
            "graph",
            "neo4j",
            "completed",
            context,
            **result.relationships_loaded,
        )
        reconciliation = None
        if not args.no_reconcile:
            reconciliation = reconcile_graph_load(
                result,
                collect_graph_counts(driver, database=database),
            )
            log_pipeline_event(
                logger,
                "Graph reconciliation completed",
                "graph",
                "neo4j",
                "completed",
                context,
                reconciliation_status=reconciliation["status"],
            )
        artefact_paths = {}
        if not args.no_artefacts:
            artefact_paths = generate_graph_load_artefacts(
                result,
                reconciliation,
                output_dir=args.output_dir,
            )
            log_pipeline_event(
                logger,
                "Graph load artefacts written",
                "graph",
                "neo4j",
                "completed",
                context,
                artefact_count=len(artefact_paths),
            )
        summary = {
            **result.summary,
            "reconciliation_status": reconciliation["status"]
            if reconciliation is not None
            else "skipped",
            "artefact_count": len(artefact_paths),
        }
        log_pipeline_event(
            logger,
            "Graph load completed",
            "graph",
            "neo4j",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except GraphError as exc:
        return _fail(logger, context, exc)
    finally:
        if postgres_engine is not None:
            dispose_engine(postgres_engine)
        close_neo4j_driver(driver)


def _analytics_config_from_args(args: argparse.Namespace) -> GraphAnalyticsConfig:
    base = load_graph_analytics_config(args.config)
    return GraphAnalyticsConfig(
        projection_relationship_types=base.projection_relationship_types,
        account_flow_relationship_types=base.account_flow_relationship_types,
        max_shortest_path_depth=(
            args.max_shortest_path_depth
            if args.max_shortest_path_depth is not None
            else base.max_shortest_path_depth
        ),
        pagerank_alpha=(
            args.pagerank_alpha if args.pagerank_alpha is not None else base.pagerank_alpha
        ),
        betweenness_sample_size=(
            args.betweenness_sample_size
            if args.betweenness_sample_size is not None
            else base.betweenness_sample_size
        ),
        community_algorithm=args.community_algorithm or base.community_algorithm,
        include_counterparties=base.include_counterparties and not args.exclude_counterparties,
        include_alert_nodes=base.include_alert_nodes and not args.exclude_alert_nodes,
        include_transaction_nodes=(
            base.include_transaction_nodes and not args.exclude_transaction_nodes
        ),
        cycle_max_hops=args.cycle_max_hops
        if args.cycle_max_hops is not None
        else base.cycle_max_hops,
        high_risk_severities=base.high_risk_severities,
    )


def command_analytics(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    driver = None
    try:
        log_pipeline_event(
            logger,
            "Graph analytics started",
            "graph",
            "neo4j",
            "started",
            context,
        )
        graph_config = load_neo4j_config(args.config)
        database = args.database or graph_config.database
        analytics_config = _analytics_config_from_args(args)
        driver = create_verified_neo4j_driver(graph_config)
        result = compute_graph_analytics_features_from_neo4j(
            driver,
            analytics_config,
            database=database,
        )
        log_pipeline_event(
            logger,
            "Graph projection read",
            "graph",
            "neo4j",
            "completed",
            context,
            **result.metadata.get("projection", {}),
        )
        log_pipeline_event(
            logger,
            "Graph analytics features computed",
            "graph",
            "neo4j",
            "completed",
            context,
            **result.summary,
        )
        artefact_paths = {}
        if not args.no_artefacts:
            artefact_paths = generate_graph_analytics_artefacts(
                result,
                output_dir=args.output_dir,
            )
            log_pipeline_event(
                logger,
                "Graph analytics artefacts written",
                "graph",
                "neo4j",
                "completed",
                context,
                artefact_count=len(artefact_paths),
            )
        summary = {**result.summary, "artefact_count": len(artefact_paths)}
        log_pipeline_event(
            logger,
            "Graph analytics completed",
            "graph",
            "neo4j",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except GraphError as exc:
        log_pipeline_event(
            logger,
            "Graph analytics failed",
            "graph",
            "neo4j",
            "failed",
            context,
            error=str(exc),
        )
        return _fail(logger, context, exc)
    finally:
        close_neo4j_driver(driver)


def _feature_date_from_arg(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def command_features_persist(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    postgres_engine = None
    driver = None
    try:
        log_pipeline_event(
            logger,
            "Graph feature persistence started",
            "graph",
            "features",
            "started",
            context,
        )
        graph_config = load_neo4j_config(args.config)
        database = args.database or graph_config.database
        analytics_config = load_graph_analytics_config(args.config)
        persistence_config = GraphFeaturePersistenceConfig(
            feature_date=_feature_date_from_arg(args.feature_date),
            feature_version=args.feature_version,
            graph_build_id=args.graph_build_id,
            graph_database=database,
            batch_size=args.batch_size,
            write_audit=not args.no_audit,
        )
        postgres_engine = create_database_engine()
        driver = create_verified_neo4j_driver(graph_config)
        analytics_result = compute_graph_analytics_features_from_neo4j(
            driver,
            analytics_config,
            database=database,
        )
        log_pipeline_event(
            logger,
            "Graph analytics features computed",
            "graph",
            "features",
            "completed",
            context,
            **analytics_result.summary,
        )
        persistence_result = persist_graph_features(
            postgres_engine,
            analytics_result.features,
            config=persistence_config,
            analytics_summary=analytics_result.summary,
            analytics_metadata=analytics_result.metadata,
        )
        log_pipeline_event(
            logger,
            "Graph features persisted",
            "graph",
            "features",
            "completed",
            context,
            **persistence_result.summary,
        )
        artefact_paths = {}
        if not args.no_artefacts:
            quality_summary = build_graph_feature_quality_summary(analytics_result.features)
            artefact_paths = generate_graph_feature_persistence_artefacts(
                persistence_result,
                quality_summary,
                output_dir=args.output_dir,
            )
            log_pipeline_event(
                logger,
                "Graph feature persistence artefacts written",
                "graph",
                "features",
                "completed",
                context,
                artefact_count=len(artefact_paths),
            )
        summary = {**persistence_result.summary, "artefact_count": len(artefact_paths)}
        log_pipeline_event(
            logger,
            "Graph feature CLI completed",
            "graph",
            "features",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except (GraphError, ValueError) as exc:
        return _feature_fail(logger, context, exc)
    finally:
        if postgres_engine is not None:
            dispose_engine(postgres_engine)
        close_neo4j_driver(driver)


def command_features_read(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    postgres_engine = None
    try:
        log_pipeline_event(
            logger,
            "Graph feature read started",
            "graph",
            "features",
            "started",
            context,
        )
        postgres_engine = create_database_engine()
        if args.latest:
            frame = read_latest_graph_features(postgres_engine, limit=args.limit)
        else:
            frame = read_graph_features(
                postgres_engine,
                feature_date=args.feature_date,
                feature_version=args.feature_version,
                graph_build_id=args.graph_build_id,
                limit=args.limit,
            )
        summary = {
            "row_count": len(frame),
            "columns": ",".join(str(column) for column in frame.columns[:8]),
        }
        log_pipeline_event(
            logger,
            "Graph feature CLI completed",
            "graph",
            "features",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except GraphError as exc:
        return _feature_fail(logger, context, exc)
    finally:
        if postgres_engine is not None:
            dispose_engine(postgres_engine)


def command_features_summary(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    postgres_engine = None
    try:
        log_pipeline_event(
            logger,
            "Graph feature summary requested",
            "graph",
            "features",
            "started",
            context,
            limit=args.limit,
        )
        postgres_engine = create_database_engine()
        summary = read_graph_feature_summary(postgres_engine)
        if args.limit is not None:
            summary["limit"] = args.limit
        log_pipeline_event(
            logger,
            "Graph feature CLI completed",
            "graph",
            "features",
            "completed",
            context,
            **summary,
        )
        _print_summary(summary)
        return 0
    except GraphError as exc:
        return _feature_fail(logger, context, exc)
    finally:
        if postgres_engine is not None:
            dispose_engine(postgres_engine)


def _feature_fail(logger: object, context: object, exc: Exception) -> int:
    log_pipeline_event(
        logger,
        "Graph feature CLI failed",
        "graph",
        "features",
        "failed",
        context,
        error=str(exc),
    )
    print(f"Graph feature CLI failed: {exc}", file=sys.stderr)
    return 1


def _fail(logger: object, context: object, exc: GraphError) -> int:
    log_pipeline_event(
        logger,
        "Graph CLI failed",
        "graph",
        "neo4j",
        "failed",
        context,
        error=str(exc),
    )
    print(f"Graph CLI failed: {exc}", file=sys.stderr)
    return 1


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default="config/graph.yaml")
    parser.add_argument("--database", default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neo4j graph utility commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("config", help="Print safe Neo4j config summary")
    _add_common_options(config_parser)
    config_parser.set_defaults(handler=command_config)

    health_parser = subparsers.add_parser("health", help="Check Neo4j health")
    _add_common_options(health_parser)
    health_parser.set_defaults(handler=command_health)

    list_parser = subparsers.add_parser("constraints-list", help="List Neo4j constraints")
    _add_common_options(list_parser)
    list_parser.set_defaults(handler=command_constraints_list)

    ensure_parser = subparsers.add_parser("constraints-ensure", help="Ensure Neo4j constraints")
    _add_common_options(ensure_parser)
    ensure_parser.set_defaults(handler=command_constraints_ensure)

    load_parser = subparsers.add_parser("load", help="Load staged PostgreSQL data into Neo4j")
    _add_common_options(load_parser)
    load_parser.add_argument("--limit", type=int, default=None)
    load_parser.add_argument("--no-alerts", action="store_true")
    load_parser.add_argument("--no-constraints", action="store_true")
    load_parser.add_argument("--batch-size", type=int, default=1000)
    load_parser.add_argument("--output-dir", default="reports/model_validation")
    load_parser.add_argument("--no-artefacts", action="store_true")
    load_parser.add_argument("--no-reconcile", action="store_true")
    load_parser.set_defaults(handler=command_load)

    analytics_parser = subparsers.add_parser(
        "analytics",
        help="Compute account-level graph analytics features",
    )
    _add_common_options(analytics_parser)
    analytics_parser.add_argument("--output-dir", default="reports/model_validation")
    analytics_parser.add_argument("--no-artefacts", action="store_true")
    analytics_parser.add_argument("--max-shortest-path-depth", type=int, default=None)
    analytics_parser.add_argument("--pagerank-alpha", type=float, default=None)
    analytics_parser.add_argument("--betweenness-sample-size", type=int, default=None)
    analytics_parser.add_argument(
        "--community-algorithm",
        choices=("connected_components", "greedy_modularity"),
        default=None,
    )
    analytics_parser.add_argument("--cycle-max-hops", type=int, default=None)
    analytics_parser.add_argument("--exclude-counterparties", action="store_true")
    analytics_parser.add_argument("--exclude-alert-nodes", action="store_true")
    analytics_parser.add_argument("--exclude-transaction-nodes", action="store_true")
    analytics_parser.set_defaults(handler=command_analytics)

    persist_parser = subparsers.add_parser(
        "features-persist",
        help="Compute Neo4j graph features and persist them to PostgreSQL",
    )
    _add_common_options(persist_parser)
    persist_parser.add_argument("--feature-date", default=None)
    persist_parser.add_argument("--feature-version", default="graph_features_v1")
    persist_parser.add_argument("--graph-build-id", default=None)
    persist_parser.add_argument("--batch-size", type=int, default=1000)
    persist_parser.add_argument("--no-audit", action="store_true")
    persist_parser.add_argument("--no-artefacts", action="store_true")
    persist_parser.add_argument("--output-dir", default="reports/model_validation")
    persist_parser.set_defaults(handler=command_features_persist)

    read_parser = subparsers.add_parser("features-read", help="Read persisted graph features")
    read_parser.add_argument("--feature-date", default=None)
    read_parser.add_argument("--feature-version", default=None)
    read_parser.add_argument("--graph-build-id", default=None)
    read_parser.add_argument("--latest", action="store_true")
    read_parser.add_argument("--limit", type=int, default=None)
    read_parser.set_defaults(handler=command_features_read)

    summary_parser = subparsers.add_parser(
        "features-summary",
        help="Print persisted graph feature summary",
    )
    summary_parser.add_argument("--limit", type=int, default=None)
    summary_parser.set_defaults(handler=command_features_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
