"""CLI for governance inventory and lineage workflows."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.database import create_database_engine, dispose_engine  # noqa: E402
from graph_aml.governance import (  # noqa: E402
    GovernanceInventoryError,
    GovernanceInventoryPersistenceConfig,
    build_and_persist_governance_inventory,
    load_governance_inventory_config,
    read_artefact_registry,
    read_governance_inventory_summary,
    read_inventory_runs,
    read_lineage_edges,
    read_lineage_nodes,
    read_model_inventory,
    read_process_inventory,
    read_validation_inventory,
)


def _print_summary(summary: dict[str, object]) -> None:
    for key, value in summary.items():
        print(f"{key}={value}")


def _apply_inventory_overrides(config: object, args: argparse.Namespace) -> object:
    values: dict[str, object] = {}
    if args.inventory_version:
        values["inventory_version"] = args.inventory_version
    persistence = replace(
        config.persistence,  # type: ignore[attr-defined]
        write_database=bool(args.persist),
        write_artefacts=not args.no_artefacts,
        artefact_output_dir=args.output_dir or config.persistence.artefact_output_dir,  # type: ignore[attr-defined]
    )
    return replace(config, persistence=persistence, **values)  # type: ignore[arg-type]


def command_inventory_run(args: argparse.Namespace) -> int:
    engine = None
    try:
        print("governance inventory started")
        config = _apply_inventory_overrides(load_governance_inventory_config(args.config), args)
        persistence = GovernanceInventoryPersistenceConfig(
            inventory_name=config.inventory_name,  # type: ignore[attr-defined]
            inventory_version=config.inventory_version,  # type: ignore[attr-defined]
            write_audit=args.persist and config.persistence.write_audit,  # type: ignore[attr-defined]
        )
        engine = create_database_engine()
        result, persisted = build_and_persist_governance_inventory(
            engine,
            config,  # type: ignore[arg-type]
            persistence,
            limit=args.limit,
            write_artefacts=not args.no_artefacts,
        )
        print("governance CLI completed")
        _print_summary(
            {
                **result.summary,
                "persisted": bool(args.persist and persisted.persisted),  # type: ignore[attr-defined]
                "inventory_run_id": persisted.inventory_run_id,  # type: ignore[attr-defined]
            }
        )
        return 0
    except GovernanceInventoryError as exc:
        print(f"governance CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def command_inventory_read_runs(args: argparse.Namespace) -> int:
    engine = None
    try:
        print("governance inventory read requested")
        engine = create_database_engine()
        frame = read_inventory_runs(
            engine,
            inventory_version=args.inventory_version,
            limit=args.limit,
        )
        _print_summary({"row_count": int(len(frame)), "columns": list(frame.columns)})
        return 0
    except GovernanceInventoryError as exc:
        print(f"governance CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def command_inventory_read_lineage(args: argparse.Namespace) -> int:
    engine = None
    try:
        print("governance inventory read requested")
        engine = create_database_engine()
        nodes = read_lineage_nodes(
            engine,
            inventory_run_id=args.inventory_run_id,
            node_type=args.node_type,
            limit=args.limit,
        )
        edges = read_lineage_edges(
            engine,
            inventory_run_id=args.inventory_run_id,
            process_name=args.process_name,
            limit=args.limit,
        )
        _print_summary(
            {
                "node_count": int(len(nodes)),
                "edge_count": int(len(edges)),
                "node_columns": list(nodes.columns),
                "edge_columns": list(edges.columns),
            }
        )
        return 0
    except GovernanceInventoryError as exc:
        print(f"governance CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def _read_frame_command(args: argparse.Namespace, reader: object, **kwargs: object) -> int:
    engine = None
    try:
        print("governance inventory read requested")
        engine = create_database_engine()
        frame = reader(engine, limit=args.limit, **kwargs)  # type: ignore[operator]
        _print_summary({"row_count": int(len(frame)), "columns": list(frame.columns)})
        return 0
    except GovernanceInventoryError as exc:
        print(f"governance CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def command_inventory_read_artefacts(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_artefact_registry,
        inventory_run_id=args.inventory_run_id,
        artefact_type=args.artefact_type,
    )


def command_inventory_read_processes(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_process_inventory,
        inventory_run_id=args.inventory_run_id,
        process_name=args.process_name,
    )


def command_inventory_read_models(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_model_inventory,
        inventory_run_id=args.inventory_run_id,
        model_version=args.model_version,
    )


def command_inventory_read_validations(args: argparse.Namespace) -> int:
    return _read_frame_command(
        args,
        read_validation_inventory,
        inventory_run_id=args.inventory_run_id,
        validation_type=args.validation_type,
    )


def command_inventory_summary(args: argparse.Namespace) -> int:
    engine = None
    try:
        print("governance inventory summary requested")
        engine = create_database_engine()
        _print_summary(read_governance_inventory_summary(engine))
        return 0
    except GovernanceInventoryError as exc:
        print(f"governance CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        dispose_engine(engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governance inventory utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory", help="Governance inventory utilities")
    inventory_sub = inventory.add_subparsers(dest="inventory_command", required=True)

    run = inventory_sub.add_parser("run", help="Build governance inventory")
    run.add_argument("--config", default="config/governance.yaml")
    run.add_argument("--persist", action="store_true")
    run.add_argument("--limit", type=int)
    run.add_argument("--inventory-version")
    run.add_argument("--no-artefacts", action="store_true")
    run.add_argument("--output-dir")
    run.set_defaults(func=command_inventory_run)

    read_runs = inventory_sub.add_parser("read-runs", help="Read inventory runs")
    read_runs.add_argument("--inventory-version")
    read_runs.add_argument("--limit", type=int)
    read_runs.set_defaults(func=command_inventory_read_runs)

    read_lineage = inventory_sub.add_parser("read-lineage", help="Read lineage nodes and edges")
    read_lineage.add_argument("--inventory-run-id")
    read_lineage.add_argument("--node-type")
    read_lineage.add_argument("--process-name")
    read_lineage.add_argument("--limit", type=int)
    read_lineage.set_defaults(func=command_inventory_read_lineage)

    read_artefacts = inventory_sub.add_parser("read-artefacts", help="Read artefact registry")
    read_artefacts.add_argument("--inventory-run-id")
    read_artefacts.add_argument("--artefact-type")
    read_artefacts.add_argument("--limit", type=int)
    read_artefacts.set_defaults(func=command_inventory_read_artefacts)

    read_processes = inventory_sub.add_parser("read-processes", help="Read process inventory")
    read_processes.add_argument("--inventory-run-id")
    read_processes.add_argument("--process-name")
    read_processes.add_argument("--limit", type=int)
    read_processes.set_defaults(func=command_inventory_read_processes)

    read_models = inventory_sub.add_parser("read-models", help="Read model inventory")
    read_models.add_argument("--inventory-run-id")
    read_models.add_argument("--model-version")
    read_models.add_argument("--limit", type=int)
    read_models.set_defaults(func=command_inventory_read_models)

    read_validations = inventory_sub.add_parser(
        "read-validations",
        help="Read validation inventory",
    )
    read_validations.add_argument("--inventory-run-id")
    read_validations.add_argument("--validation-type")
    read_validations.add_argument("--limit", type=int)
    read_validations.set_defaults(func=command_inventory_read_validations)

    summary = inventory_sub.add_parser("summary", help="Read governance inventory summary")
    summary.add_argument("--limit", type=int)
    summary.set_defaults(func=command_inventory_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
