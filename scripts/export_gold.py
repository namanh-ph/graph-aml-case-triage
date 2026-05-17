"""Export populated PostgreSQL mart/aml/governance tables to gold-layer Parquet.

After the analytics pipeline has populated the ``mart.*``, ``aml.*``, and
``governance.*`` schemas, this script materialises each table as a Parquet file
under ``data/gold/`` for portable, PG-free consumption (dashboards, MLflow
inputs, downstream analysis).

Usage:
    python scripts/export_gold.py
    python scripts/export_gold.py --gold-dir data/gold --skip-missing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

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

DEFAULT_GOLD_DIR = PROJECT_ROOT / "data" / "gold"

# Mapping of gold-layer parquet filename -> qualified PostgreSQL source table.
GOLD_EXPORTS: dict[str, str] = {
    # mart.* (account features and scores)
    "features_account_daily": "mart.features_account_daily",
    "graph_features": "mart.graph_features",
    "account_anomaly_scores": "mart.account_anomaly_scores",
    "account_risk_scores": "mart.account_risk_scores",
    # aml.* (alerts, cases, evidence, lifecycle)
    "alerts": "aml.alerts",
    "cases": "aml.cases",
    "case_alerts": "aml.case_alerts",
    "case_entities": "aml.case_entities",
    "case_risk_scores": "aml.case_risk_scores",
    "case_evidence_packs": "aml.case_evidence_packs",
    "case_explanations": "aml.case_explanations",
    "case_lifecycle_events": "aml.case_lifecycle_events",
    "case_assignments": "aml.case_assignments",
    # governance.* (audit + provenance)
    "audit_events": "governance.audit_events",
    "model_runs": "governance.model_runs",
    "validation_reports": "governance.validation_reports",
}


def _configure_logging() -> None:
    config = load_app_config()
    configure_logging(
        log_dir=config.paths.paths.logs_dir,
        enable_console=False,
        enable_file=True,
    )


def export_table_to_parquet(
    engine: Engine,
    qualified_table: str,
    output_path: Path,
) -> int:
    """Read a table from PostgreSQL and write it as a Parquet file."""

    frame = pd.read_sql_query(text(f"SELECT * FROM {qualified_table}"), engine)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, compression="snappy")
    return len(frame)


def export_gold(
    engine: Engine,
    gold_dir: Path,
    skip_missing: bool = True,
) -> dict[str, int]:
    """Export every configured mart/aml/governance table to ``gold_dir``."""

    gold_dir.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}
    total_rows = 0
    print(f"Gold dir: {gold_dir}")
    print()
    for parquet_name, qualified_table in GOLD_EXPORTS.items():
        output_path = gold_dir / f"{parquet_name}.parquet"
        try:
            rows = export_table_to_parquet(engine, qualified_table, output_path)
        except Exception as exc:
            if skip_missing:
                print(f"  {parquet_name:30s} SKIP  ({exc.__class__.__name__})")
                row_counts[parquet_name] = -1
                continue
            raise
        size_kb = output_path.stat().st_size / 1024
        print(f"  {parquet_name:30s} {rows:>9,} rows   {size_kb:>9.1f} KB")
        row_counts[parquet_name] = rows
        total_rows += rows
    print()
    print(f"  TOTAL                          {total_rows:>9,} rows across {sum(1 for c in row_counts.values() if c >= 0)} tables")
    return row_counts


def command_export(args: argparse.Namespace) -> int:
    """Run the gold export end-to-end."""

    _configure_logging()
    logger = get_logger("graph_aml.export.cli")
    context = create_run_context(component="export", pipeline_stage="gold_export")
    engine = create_database_engine()
    try:
        log_pipeline_event(
            logger,
            "Gold export started",
            "export",
            "gold_export",
            "started",
            context,
            gold_dir=str(args.gold_dir),
        )
        row_counts = export_gold(
            engine,
            gold_dir=args.gold_dir,
            skip_missing=not args.strict,
        )
        log_pipeline_event(
            logger,
            "Gold export completed",
            "export",
            "gold_export",
            "completed",
            context,
            row_counts=row_counts,
        )
        return 0
    except Exception as exc:
        log_pipeline_event(
            logger,
            "Gold export failed",
            "export",
            "gold_export",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Gold export failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    """Build the gold export CLI parser."""

    parser = argparse.ArgumentParser(
        description="Export PG mart/aml/governance tables to gold-layer Parquet.",
    )
    parser.add_argument(
        "--gold-dir",
        type=Path,
        default=DEFAULT_GOLD_DIR,
        help="Output directory for gold parquet files (default: data/gold).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any missing source table instead of skipping.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the gold export CLI."""

    args = build_parser().parse_args(argv)
    return command_export(args)


if __name__ == "__main__":
    raise SystemExit(main())
