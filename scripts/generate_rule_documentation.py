"""CLI for AML rule documentation generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.observability import (  # noqa: E402
    configure_logging,
    create_run_context,
    get_logger,
    log_pipeline_event,
)
from graph_aml.rules import (  # noqa: E402
    RuleDocumentationError,
    build_all_rule_documentation,
    check_rule_documentation_coverage,
    generate_rule_documentation_artefacts,
    validate_rule_documentation,
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
        get_logger("graph_aml.rules.documentation.cli"),
        create_run_context(component="rules", pipeline_stage="rule_documentation"),
    )


def _print_coverage(summary: dict[str, object]) -> None:
    for key in (
        "rule_count",
        "rules_documented",
        "missing_rules",
        "threshold_count",
        "evidence_doc_count",
        "limitation_count",
    ):
        print(f"{key}={summary[key]}")


def command_list(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    try:
        docs = build_all_rule_documentation(args.rules)
        log_pipeline_event(
            logger,
            "Rule documentation list requested",
            "rules",
            "rule_documentation",
            "completed",
            context,
            rule_count=len(docs),
        )
        for documentation in docs:
            validate_rule_documentation(documentation)
            print(
                "\t".join(
                    (
                        documentation.rule_key,
                        documentation.rule_name,
                        documentation.typology,
                        "coverage=complete",
                    )
                )
            )
        return 0
    except RuleDocumentationError as exc:
        log_pipeline_event(
            logger,
            "Rule documentation CLI failed",
            "rules",
            "rule_documentation",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Rule documentation failed: {exc}", file=sys.stderr)
        return 1


def command_validate(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    try:
        log_pipeline_event(
            logger,
            "Rule documentation validation started",
            "rules",
            "rule_documentation",
            "started",
            context,
        )
        docs = build_all_rule_documentation(args.rules)
        for documentation in docs:
            validate_rule_documentation(documentation)
        coverage = check_rule_documentation_coverage(docs)
        log_pipeline_event(
            logger,
            "Rule documentation validation completed",
            "rules",
            "rule_documentation",
            "completed",
            context,
            **coverage,
        )
        _print_coverage(coverage)
        return 0
    except RuleDocumentationError as exc:
        log_pipeline_event(
            logger,
            "Rule documentation CLI failed",
            "rules",
            "rule_documentation",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Rule documentation failed: {exc}", file=sys.stderr)
        return 1


def command_generate(args: argparse.Namespace) -> int:
    logger, context = _logger_context()
    try:
        log_pipeline_event(
            logger,
            "Rule documentation generation started",
            "rules",
            "rule_documentation",
            "started",
            context,
            docs_output_dir=args.docs_output_dir,
            reports_output_dir=args.reports_output_dir,
        )
        artefacts = generate_rule_documentation_artefacts(
            rule_keys=args.rules,
            docs_output_dir=args.docs_output_dir,
            reports_output_dir=args.reports_output_dir,
        )
        log_pipeline_event(
            logger,
            "Rule documentation artefacts written",
            "rules",
            "rule_documentation",
            "completed",
            context,
            artefact_count=len(artefacts),
        )
        for name, path in artefacts.items():
            print(f"{name}={path}")
        return 0
    except RuleDocumentationError as exc:
        log_pipeline_event(
            logger,
            "Rule documentation CLI failed",
            "rules",
            "rule_documentation",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Rule documentation failed: {exc}", file=sys.stderr)
        return 1


def _add_rule_selection_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--rules",
        nargs="+",
        default=None,
        help="Optional rule keys or aliases to document.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate AML rule documentation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List documented AML rules")
    _add_rule_selection_argument(list_parser)
    list_parser.set_defaults(handler=command_list)

    validate_parser = subparsers.add_parser("validate", help="Validate rule documentation")
    _add_rule_selection_argument(validate_parser)
    validate_parser.set_defaults(handler=command_validate)

    generate_parser = subparsers.add_parser("generate", help="Generate documentation artefacts")
    _add_rule_selection_argument(generate_parser)
    generate_parser.add_argument("--docs-output-dir", default="docs/rules")
    generate_parser.add_argument("--reports-output-dir", default="reports/model_validation")
    generate_parser.set_defaults(handler=command_generate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
