"""Demo readiness and run artefact writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from graph_aml.demo.exceptions import DemoArtefactError
from graph_aml.demo.runner import DemoRunResult, demo_run_result_to_dict


def _write_json(payload: dict[str, object], output_path: Path | str) -> Path:
    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        raise DemoArtefactError(f"failed to write demo artefact {path}: {exc}") from exc
    return path


def write_demo_run_summary_json(
    result: DemoRunResult,
    output_path: Path | str = "reports/model_validation/demo_run_summary.json",
) -> Path:
    """Write a demo run summary JSON file."""

    return _write_json(demo_run_result_to_dict(result), output_path)


def write_demo_readiness_report_json(
    readiness: dict[str, object],
    output_path: Path | str = "reports/model_validation/demo_readiness_report.json",
) -> Path:
    """Write a demo readiness report JSON file."""

    return _write_json(readiness, output_path)


def write_demo_validation_summary_json(
    validation_summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/demo_validation_summary.json",
) -> Path:
    """Write a demo validation summary JSON file."""

    return _write_json(validation_summary, output_path)


def build_demo_artefact_index(
    report_dir: Path | str = "reports/model_validation",
) -> dict[str, object]:
    """Build an index of local demo artefacts."""

    root = Path(report_dir)
    if not root.exists():
        return {
            "report_dir": str(root),
            "file_count": 0,
            "files": [],
            "extensions": {},
        }
    if not root.is_dir():
        raise DemoArtefactError("report_dir must be a directory")
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()
        rows.append(
            {
                "file_name": path.name,
                "relative_path": str(path.relative_to(root)).replace("\\", "/"),
                "extension": path.suffix.lower(),
                "size_bytes": int(stat.st_size),
                "modified_at": modified,
            }
        )
    extension_counts: dict[str, int] = {}
    for row in rows:
        extension = str(row["extension"])
        extension_counts[extension] = extension_counts.get(extension, 0) + 1
    return {
        "report_dir": str(root),
        "file_count": len(rows),
        "files": rows,
        "extensions": extension_counts,
    }


def write_demo_artefact_index_json(
    artefact_index: dict[str, object],
    output_path: Path | str = "reports/model_validation/demo_artefact_index.json",
) -> Path:
    """Write a demo artefact index JSON file."""

    return _write_json(artefact_index, output_path)


def generate_demo_readiness_artefacts(
    run_result: DemoRunResult | None = None,
    readiness: dict[str, object] | None = None,
    validation_summary: dict[str, object] | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write supplied demo readiness artefacts and a local artefact index."""

    directory = Path(output_dir)
    paths: dict[str, Path] = {}
    if run_result is not None:
        paths["demo_run_summary_json"] = write_demo_run_summary_json(
            run_result,
            directory / "demo_run_summary.json",
        )
    if readiness is not None:
        paths["demo_readiness_report_json"] = write_demo_readiness_report_json(
            readiness,
            directory / "demo_readiness_report.json",
        )
    if validation_summary is not None:
        paths["demo_validation_summary_json"] = write_demo_validation_summary_json(
            validation_summary,
            directory / "demo_validation_summary.json",
        )
    artefact_index = build_demo_artefact_index(directory)
    paths["demo_artefact_index_json"] = write_demo_artefact_index_json(
        artefact_index,
        directory / "demo_artefact_index.json",
    )
    return paths
