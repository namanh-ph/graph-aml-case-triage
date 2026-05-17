"""CLI for security controls and privacy safeguards."""

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
from graph_aml.security import (  # noqa: E402
    SecurityControlConfig,
    SecurityControlError,
    SecurityControlPersistenceConfig,
    build_masking_preview,
    build_sensitive_field_inventory,
    load_security_control_config,
    read_audit_integrity_checks,
    read_permission_matrix,
    read_secrets_scan_findings,
    read_security_control_runs,
    read_security_control_summary,
    read_security_sample_table,
    read_security_table_columns,
    read_sensitive_field_inventory,
    run_and_persist_security_controls,
)


def _print_summary(summary: dict[str, object]) -> None:
    for key, value in summary.items():
        print(f"{key}={value}")


def _apply_run_overrides(
    config: SecurityControlConfig,
    args: argparse.Namespace,
) -> SecurityControlConfig:
    persistence = replace(
        config.persistence,
        write_database=bool(args.persist),
        write_artefacts=not args.no_artefacts,
        artefact_output_dir=args.output_dir or config.persistence.artefact_output_dir,
    )
    if args.security_version:
        return replace(
            config,
            security_version=args.security_version,
            persistence=persistence,
        )
    return replace(config, persistence=persistence)


def command_controls_run(args: argparse.Namespace) -> int:
    engine: Engine | None = None
    try:
        print("security controls started")
        config = _apply_run_overrides(load_security_control_config(args.config), args)
        persistence = SecurityControlPersistenceConfig(
            security_name=config.security_name,
            security_version=config.security_version,
            write_audit=args.persist and config.persistence.write_audit,
        )
        engine = create_database_engine()
        result, persisted = run_and_persist_security_controls(
            engine,
            config,
            persistence,
            limit=args.limit,
            write_artefacts=not args.no_artefacts,
        )
        print("security CLI completed")
        _print_summary(
            {
                **result.summary,
                "persisted": bool(args.persist and persisted.persisted),
                "security_run_id": result.security_run_id,
            }
        )
        return 0
    except SecurityControlError as exc:
        print(f"security CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            dispose_engine(engine)


def _read_frame_command(args: argparse.Namespace, reader: object, **kwargs: object) -> int:
    engine: Engine | None = None
    try:
        print("security read requested")
        engine = create_database_engine()
        frame = reader(engine, limit=args.limit, **kwargs)  # type: ignore[operator]
        _print_summary({"row_count": int(len(frame)), "columns": list(frame.columns)})
        return 0
    except SecurityControlError as exc:
        print(f"security CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            dispose_engine(engine)


def command_read_runs(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args, read_security_control_runs, security_version=args.security_version
    )


def command_read_fields(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_sensitive_field_inventory,
        security_run_id=args.security_run_id,
        classification=args.classification,
    )


def command_read_permissions(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_permission_matrix,
        security_run_id=args.security_run_id,
        role=args.role,
    )


def command_read_secrets(args: argparse.Namespace) -> int:
    allowed = None if args.allowed is None else args.allowed.lower() == "true"
    return _read_frame_command(
        args,
        read_secrets_scan_findings,
        security_run_id=args.security_run_id,
        allowed=allowed,
    )


def command_read_audit_integrity(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_audit_integrity_checks,
        security_run_id=args.security_run_id,
        status=args.status,
    )


def command_summary(args: argparse.Namespace) -> int:
    engine: Engine | None = None
    try:
        print("security controls summary requested")
        engine = create_database_engine()
        _print_summary(read_security_control_summary(engine))
        return 0
    except SecurityControlError as exc:
        print(f"security CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            dispose_engine(engine)


def command_mask_preview(args: argparse.Namespace) -> int:
    engine: Engine | None = None
    try:
        print("mask preview requested")
        config = load_security_control_config(args.config)
        engine = create_database_engine()
        table_columns = read_security_table_columns(engine)
        sample = read_security_sample_table(engine, args.schema, args.table, args.limit)
        fields = build_sensitive_field_inventory(table_columns, config, "preview")
        selected = fields[
            (fields["schema_name"].astype(str) == args.schema)
            & (fields["table_name"].astype(str) == args.table)
        ]
        preview = build_masking_preview(sample, selected, config, max_rows=args.limit)
        _print_summary({"row_count": int(len(preview)), "columns": list(preview.columns)})
        if not preview.empty:
            print(preview.head(args.limit).to_string(index=False))
        print("security CLI completed")
        return 0
    except SecurityControlError as exc:
        print(f"security CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Security control utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    controls = subparsers.add_parser("controls", help="Security controls")
    controls_sub = controls.add_subparsers(dest="controls_command", required=True)

    run = controls_sub.add_parser("run", help="Run security controls")
    run.add_argument("--config", default="config/security.yaml")
    run.add_argument("--persist", action="store_true")
    run.add_argument("--limit", type=int)
    run.add_argument("--security-version")
    run.add_argument("--no-artefacts", action="store_true")
    run.add_argument("--output-dir")
    run.set_defaults(func=command_controls_run)

    read_runs = controls_sub.add_parser("read-runs", help="Read security control runs")
    read_runs.add_argument("--security-version")
    read_runs.add_argument("--limit", type=int)
    read_runs.set_defaults(func=command_read_runs)

    read_fields = controls_sub.add_parser("read-fields", help="Read sensitive field inventory")
    read_fields.add_argument("--security-run-id")
    read_fields.add_argument("--classification")
    read_fields.add_argument("--limit", type=int)
    read_fields.set_defaults(func=command_read_fields)

    read_permissions = controls_sub.add_parser("read-permissions", help="Read permission matrix")
    read_permissions.add_argument("--security-run-id")
    read_permissions.add_argument("--role")
    read_permissions.add_argument("--limit", type=int)
    read_permissions.set_defaults(func=command_read_permissions)

    read_secrets = controls_sub.add_parser("read-secrets", help="Read secrets scan findings")
    read_secrets.add_argument("--security-run-id")
    read_secrets.add_argument("--allowed", choices=("true", "false"))
    read_secrets.add_argument("--limit", type=int)
    read_secrets.set_defaults(func=command_read_secrets)

    read_audit = controls_sub.add_parser(
        "read-audit-integrity",
        help="Read audit integrity checks",
    )
    read_audit.add_argument("--security-run-id")
    read_audit.add_argument("--status")
    read_audit.add_argument("--limit", type=int)
    read_audit.set_defaults(func=command_read_audit_integrity)

    summary = controls_sub.add_parser("summary", help="Read security control summary")
    summary.add_argument("--limit", type=int)
    summary.set_defaults(func=command_summary)

    preview = subparsers.add_parser("mask-preview", help="Preview masked table sample")
    preview.add_argument("--config", default="config/security.yaml")
    preview.add_argument("--schema", required=True)
    preview.add_argument("--table", required=True)
    preview.add_argument("--limit", type=int, default=10)
    preview.set_defaults(func=command_mask_preview)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
