"""CLI for generating account-level feature artefacts."""

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
from graph_aml.features import (  # noqa: E402
    AccountFeatureConfig,
    FeatureEngineeringError,
    calculate_account_features,
    calculate_and_persist_account_features_from_staged,
    calculate_extended_account_features,
    get_mart_account_feature_date_range,
    get_mart_account_feature_versions,
    persist_account_features,
    read_mart_account_features,
    read_staged_extended_feature_inputs,
    read_staged_feature_inputs,
    summarise_account_features,
    validate_account_features,
    validate_extended_account_features,
    write_account_feature_summary_json,
    write_account_features_csv,
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


def _feature_config(args: argparse.Namespace) -> AccountFeatureConfig:
    return AccountFeatureConfig(
        feature_version=args.feature_version,
        min_feature_date=args.min_feature_date,
        max_feature_date=args.max_feature_date,
        include_all_accounts=not args.active_only,
        reporting_threshold=args.reporting_threshold,
        below_threshold_margin=args.below_threshold_margin,
        entropy_window_days=args.entropy_window_days,
        jurisdiction_window_days=args.jurisdiction_window_days,
    )


def _print_paths(paths: dict[str, Path]) -> None:
    for name in sorted(paths):
        print(f"{name}={paths[name]}")


def _print_summary(summary: dict[str, object]) -> None:
    for key in (
        "feature_row_count",
        "account_count",
        "min_feature_date",
        "max_feature_date",
        "mean_txn_count_7d",
        "max_txn_count_7d",
    ):
        print(f"{key}={summary[key]}")


def _print_persistence_summary(summary: dict[str, int]) -> None:
    for key in (
        "feature_rows_upserted",
        "account_count",
        "feature_date_count",
        "feature_version_count",
    ):
        print(f"{key}={summary[key]}")


def _print_mart_summary(
    features,
    versions: tuple[str, ...],
    date_range: dict[str, str | None],
) -> None:
    print(f"mart_feature_rows={len(features)}")
    print(f"feature_versions={','.join(versions)}")
    print(f"min_feature_date={date_range['min_feature_date']}")
    print(f"max_feature_date={date_range['max_feature_date']}")


def command_staged(args: argparse.Namespace) -> int:
    """Generate account features from PostgreSQL staging tables."""

    _configure_logging()
    logger = get_logger("graph_aml.features.cli")
    context = create_run_context(component="features", pipeline_stage="account_features")
    engine = create_database_engine()
    try:
        if args.read_mart:
            log_pipeline_event(
                logger,
                "Feature calculation started",
                "features",
                "account_features",
                "started",
                context,
                read_mart=True,
                feature_version_filter=args.feature_version_filter,
                limit=args.limit,
            )
            features = read_mart_account_features(
                engine,
                feature_version=args.feature_version_filter,
                limit=args.limit,
            )
            versions = get_mart_account_feature_versions(engine)
            date_range = get_mart_account_feature_date_range(
                engine,
                feature_version=args.feature_version_filter,
            )
            log_pipeline_event(
                logger,
                "Mart feature read completed",
                "features",
                "account_features",
                "completed",
                context,
                feature_rows=len(features),
            )
            _print_mart_summary(features, versions, date_range)
            return 0

        config = _feature_config(args)
        log_pipeline_event(
            logger,
            "Feature calculation started",
            "features",
            "account_features",
            "started",
            context,
            limit=args.limit,
            output_dir=args.output_dir,
            feature_version=config.feature_version,
            extended=args.extended,
            persist=args.persist,
        )
        if args.extended:
            accounts, transactions, countries = read_staged_extended_feature_inputs(
                engine,
                limit=args.limit,
            )
        else:
            accounts, transactions = read_staged_feature_inputs(engine, limit=args.limit)
            countries = None
        log_pipeline_event(
            logger,
            "Staged feature inputs read",
            "features",
            "account_features",
            "completed",
            context,
            account_rows=len(accounts),
            transaction_rows=len(transactions),
            country_rows=None if countries is None else len(countries),
        )
        if args.extended:
            features = calculate_extended_account_features(
                accounts,
                transactions,
                countries,
                config=config,
            )
            validate_extended_account_features(features)
            feature_mode = "extended"
        else:
            features = calculate_account_features(accounts, transactions, config=config)
            validate_account_features(features)
            feature_mode = "base"
        summary = summarise_account_features(features)
        log_pipeline_event(
            logger,
            "Account features calculated",
            "features",
            "account_features",
            "completed",
            context,
            feature_rows=len(features),
            account_count=summary["account_count"],
            feature_mode=feature_mode,
        )
        output_dir = Path(args.output_dir)
        paths = {
            "features_csv": write_account_features_csv(
                features,
                output_dir / "account_features.csv",
            ),
            "summary_json": write_account_feature_summary_json(
                summary,
                output_dir / "account_feature_summary.json",
            ),
        }
        log_pipeline_event(
            logger,
            "Feature artefacts written",
            "features",
            "account_features",
            "completed",
            context,
            artefact_count=len(paths),
        )
        _print_paths(paths)
        print(f"feature_mode={feature_mode}")
        _print_summary(summary)
        if args.persist:
            log_pipeline_event(
                logger,
                "Feature persistence started",
                "features",
                "account_features",
                "started",
                context,
                write_audit=not args.no_audit,
                feature_mode=feature_mode,
            )
            if args.extended:
                persistence_summary = persist_account_features(
                    engine,
                    features,
                    write_audit=not args.no_audit,
                    metadata={
                        "feature_mode": feature_mode,
                        "limit": args.limit,
                        "output_dir": str(output_dir),
                    },
                )
            else:
                persistence_summary = calculate_and_persist_account_features_from_staged(
                    engine,
                    config=config,
                    limit=args.limit,
                    extended=False,
                    write_audit=not args.no_audit,
                )
            log_pipeline_event(
                logger,
                "Feature persistence completed",
                "features",
                "account_features",
                "completed",
                context,
                **persistence_summary,
            )
            _print_persistence_summary(persistence_summary)
        return 0
    except FeatureEngineeringError as exc:
        log_pipeline_event(
            logger,
            "Feature workflow failed",
            "features",
            "account_features",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Account feature generation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log_pipeline_event(
            logger,
            "Feature workflow failed",
            "features",
            "account_features",
            "failed",
            context,
            error=str(exc),
        )
        print(f"Account feature generation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    """Build the account feature CLI parser."""

    parser = argparse.ArgumentParser(
        description="Generate account-level feature artefacts from staging tables.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Subcommand options include:\n"
            "  --limit\n"
            "  --output-dir\n"
            "  --feature-version\n"
            "  --min-feature-date\n"
            "  --max-feature-date\n"
            "  --active-only\n"
            "  --extended\n"
            "  --reporting-threshold\n"
            "  --below-threshold-margin\n"
            "  --entropy-window-days\n"
            "  --jurisdiction-window-days\n"
            "  --persist\n"
            "  --no-audit\n"
            "  --read-mart\n"
            "  --feature-version-filter"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    staged = subparsers.add_parser("staged", help="Generate features from staging tables.")
    staged.add_argument("--limit", type=int, default=None, help="Maximum staged transactions.")
    staged.add_argument(
        "--output-dir",
        default="reports/model_validation",
        help="Output directory for account feature artefacts.",
    )
    staged.add_argument(
        "--feature-version",
        default="account_features_v1",
        help="Feature version label written to every row.",
    )
    staged.add_argument("--min-feature-date", default=None, help="Minimum feature date.")
    staged.add_argument("--max-feature-date", default=None, help="Maximum feature date.")
    staged.add_argument(
        "--active-only",
        action="store_true",
        help="Only include accounts observed as transaction senders or receivers.",
    )
    staged.add_argument(
        "--extended",
        action="store_true",
        help="Generate behavioural and jurisdiction features in addition to base features.",
    )
    staged.add_argument(
        "--reporting-threshold",
        type=float,
        default=10000.0,
        help="Reporting threshold for below-threshold activity features.",
    )
    staged.add_argument(
        "--below-threshold-margin",
        type=float,
        default=0.95,
        help="Lower bound multiplier for below-threshold activity features.",
    )
    staged.add_argument(
        "--entropy-window-days",
        type=int,
        default=30,
        help="Rolling window days for counterparty entropy.",
    )
    staged.add_argument(
        "--jurisdiction-window-days",
        type=int,
        default=30,
        help="Rolling window days for jurisdiction features.",
    )
    staged.add_argument(
        "--persist",
        action="store_true",
        help="Persist generated features into mart.features_account_daily.",
    )
    staged.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip governance audit event writing when --persist is supplied.",
    )
    staged.add_argument(
        "--read-mart",
        action="store_true",
        help="Read persisted mart account features instead of recalculating.",
    )
    staged.add_argument(
        "--feature-version-filter",
        default=None,
        help="Feature version filter for --read-mart.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the account feature CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "staged":
        return command_staged(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
