"""Local artefact writers for analyst label outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.labels.dataset import LabelDatasetBuildResult
from graph_aml.labels.exceptions import LabelPersistenceError
from graph_aml.labels.validation import build_label_quality_summary


def _write_csv(frame: pd.DataFrame, output_path: Path | str) -> Path:
    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
    except Exception as exc:
        raise LabelPersistenceError(f"failed to write CSV artefact {path}: {exc}") from exc
    return path


def write_case_labels_csv(
    case_labels: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_labels.csv",
) -> Path:
    return _write_csv(case_labels, output_path)


def write_account_labels_csv(
    account_labels: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/account_labels.csv",
) -> Path:
    return _write_csv(account_labels, output_path)


def write_case_supervised_dataset_csv(
    dataset: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/case_supervised_dataset.csv",
) -> Path:
    return _write_csv(dataset, output_path)


def write_account_supervised_dataset_csv(
    dataset: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/account_supervised_dataset.csv",
) -> Path:
    return _write_csv(dataset, output_path)


def write_label_quality_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/label_quality_summary.json",
) -> Path:
    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(summary, indent=2, sort_keys=True, default=str)
        path.write_text(payload, encoding="utf-8")
    except Exception as exc:
        message = f"failed to write label summary artefact {path}: {exc}"
        raise LabelPersistenceError(message) from exc
    return path


def generate_label_artefacts(
    result: LabelDatasetBuildResult,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    directory = Path(output_dir)
    return {
        "case_labels_csv": write_case_labels_csv(result.case_labels, directory / "case_labels.csv"),
        "account_labels_csv": write_account_labels_csv(
            result.account_labels,
            directory / "account_labels.csv",
        ),
        "case_supervised_dataset_csv": write_case_supervised_dataset_csv(
            result.case_dataset,
            directory / "case_supervised_dataset.csv",
        ),
        "account_supervised_dataset_csv": write_account_supervised_dataset_csv(
            result.account_dataset,
            directory / "account_supervised_dataset.csv",
        ),
        "label_quality_summary_json": write_label_quality_summary_json(
            build_label_quality_summary(result),
            directory / "label_quality_summary.json",
        ),
    }
