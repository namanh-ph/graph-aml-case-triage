"""CLI for the unified deterministic AML rule engine."""

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
    RuleError,
    get_rule_registry,
    load_individual_rule_configs,
    load_rule_engine_run_config,
    run_rule_engine_from_staged,
)


def _configure_logging() -> None:
    config = load_app_config()
    configure_logging(
        log_dir=config.paths.paths.logs_dir,
        enable_console=False,
        enable_file=True,
    )


def _print_engine_summary(summary: dict[str, object]) -> None:
    for key in (
        "rules_run",
        "alerts_generated",
        "alerts_persisted",
        "unique_account_count",
        "persisted",
        "artefact_count",
    ):
        print(f"{key}={summary[key]}")


def command_list(args: argparse.Namespace) -> int:
    """List registered deterministic AML rules without connecting to the database."""

    for definition in get_rule_registry().values():
        print(
            "\t".join(
                (
                    definition.rule_key,
                    definition.rule_name,
                    definition.typology,
                    f"supports_artefacts={definition.supports_artefacts}",
                )
            )
        )
    return 0


def command_run(args: argparse.Namespace) -> int:
    """Run selected deterministic AML rules against staged tables."""

    _configure_logging()
    logger = get_logger("graph_aml.rules.engine.cli")
    context = create_run_context(component="rules", pipeline_stage="rule_engine")
    engine = create_database_engine()
    try:
        log_pipeline_event(
            logger,
            "Rule engine started",
            "rules",
            "rule_engine",
            "started",
            context,
            persist=args.persist,
            limit=args.limit,
        )
        registry = get_rule_registry()
        log_pipeline_event(
            logger,
            "Rule registry loaded",
            "rules",
            "rule_engine",
            "completed",
            context,
            registered_rule_count=len(registry),
        )
        run_config = load_rule_engine_run_config(
            config_path=args.config,
            requested_rule_keys=args.rules,
            disabled_rule_keys=args.exclude_rules,
            persist_alerts=args.persist,
            write_audit=not args.no_audit,
            write_artefacts=not args.no_artefacts,
            output_dir=args.output_dir,
            limit=args.limit,
        )
        rule_configs = load_individual_rule_configs(
            config_path=args.config,
            rule_keys=run_config.enabled_rules,
        )
        log_pipeline_event(
            logger,
            "Rule engine config loaded",
            "rules",
            "rule_engine",
            "completed",
            context,
            rules=list(run_config.enabled_rules),
        )
        result = run_rule_engine_from_staged(
            engine,
            run_config=run_config,
            rule_configs=rule_configs,
            write_engine_audit=not args.no_engine_audit and not args.no_audit,
        )
        log_pipeline_event(
            logger,
            "Staged rule execution completed",
            "rules",
            "rule_engine",
            "completed",
            context,
            **result.summary,
        )
        log_pipeline_event(
            logger,
            "Rule engine completed",
            "rules",
            "rule_engine",
            "completed",
            context,
            **result.summary,
        )
        _print_engine_summary(result.summary)
        return 0
    except RuleError as exc:
        log_pipeline_event(
            logger,
            "Rule engine failed",
            "rules",
            "rule_engine",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Rule engine failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic AML rules")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="List registered AML rules")
    list_parser.set_defaults(handler=command_list)
    run_parser = subparsers.add_parser("run", help="Run AML rules from staged data")
    run_parser.add_argument("--rules", nargs="+", default=None)
    run_parser.add_argument("--exclude-rules", nargs="+", default=None)
    run_parser.add_argument("--persist", action="store_true")
    run_parser.add_argument("--no-audit", action="store_true")
    run_parser.add_argument("--no-engine-audit", action="store_true")
    run_parser.add_argument("--no-artefacts", action="store_true")
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--output-dir", default="reports/model_validation")
    run_parser.add_argument("--config", default="config/rules.yaml")
    run_parser.set_defaults(handler=command_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
