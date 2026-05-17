"""CLI for generating data dictionary artefacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.config import load_app_config  # noqa: E402
from graph_aml.documentation import (  # noqa: E402
    DocumentationError,
    generate_data_dictionary_artefacts,
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


def command_generate(args: argparse.Namespace) -> int:
    """Generate data dictionary artefacts."""

    _configure_logging()
    logger = get_logger("graph_aml.documentation.cli")
    context = create_run_context(component="documentation", pipeline_stage="data_dictionary")
    try:
        log_pipeline_event(
            logger,
            "Data dictionary generation started",
            "documentation",
            "data_dictionary",
            "started",
            context,
            output_dir=args.output_dir,
        )
        paths = generate_data_dictionary_artefacts(args.output_dir)
        log_pipeline_event(
            logger,
            "Data dictionary generation completed",
            "documentation",
            "data_dictionary",
            "completed",
            context,
            artefact_count=len(paths),
        )
        for name in sorted(paths):
            print(f"{name}={paths[name]}")
        return 0
    except DocumentationError as exc:
        log_pipeline_event(
            logger,
            "Data dictionary generation failed",
            "documentation",
            "data_dictionary",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Data dictionary generation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log_pipeline_event(
            logger,
            "Data dictionary generation failed",
            "documentation",
            "data_dictionary",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Data dictionary generation failed: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the data dictionary CLI parser."""

    parser = argparse.ArgumentParser(
        description="Generate data dictionary documentation artefacts.",
        epilog="Subcommand options include --output-dir.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate data dictionary artefacts.")
    generate.add_argument(
        "--output-dir",
        default="reports/model_validation",
        help="Output directory for Markdown, JSON, and CSV artefacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the data dictionary CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "generate":
        return command_generate(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
