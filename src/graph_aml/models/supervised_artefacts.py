"""Local artefact writers for supervised AML model baselines."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from graph_aml.models.supervised_exceptions import SupervisedPersistenceError
from graph_aml.models.supervised_summary import supervised_training_result_to_dict
from graph_aml.models.supervised_training import SupervisedTrainingResult
from graph_aml.models.supervised_validation import build_supervised_model_quality_summary


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_supervised_scores_csv(
    scores: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/supervised_model_scores.csv",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        scores.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to write supervised scores: {exc}") from exc


def write_supervised_metrics_json(
    training_result: SupervisedTrainingResult,
    output_path: Path | str = "reports/model_validation/supervised_model_metrics.json",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        payload = json.dumps(
            supervised_training_result_to_dict(training_result),
            indent=2,
            sort_keys=True,
            default=str,
        )
        path.write_text(payload, encoding="utf-8")
        return path
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to write supervised metrics: {exc}") from exc


def write_supervised_threshold_metrics_csv(
    training_result: SupervisedTrainingResult,
    output_path: Path | str = "reports/model_validation/supervised_threshold_metrics.csv",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        training_result.threshold_metrics.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to write threshold metrics: {exc}") from exc


def write_supervised_top_k_metrics_csv(
    training_result: SupervisedTrainingResult,
    output_path: Path | str = "reports/model_validation/supervised_top_k_metrics.csv",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        training_result.top_k_metrics.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to write top-k metrics: {exc}") from exc


def write_supervised_model_card_md(
    training_result: SupervisedTrainingResult,
    scores: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/supervised_model_card.md",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        summary = build_supervised_model_quality_summary(training_result, scores)
        lines = [
            "# Supervised AML Baseline Model Card",
            "",
            "## Intended Use",
            "Interpretable supervised benchmark for AML triage prioritisation.",
            "",
            "## Label Source",
            "Analyst lifecycle closure decisions from supervised-readiness datasets.",
            "",
            "## Model",
            f"- Name: `{training_result.model_name}`",
            f"- Version: `{training_result.model_version}`",
            f"- Family: `{training_result.model_family}`",
            f"- Dataset version: `{training_result.metadata.get('dataset_version')}`",
            "",
            "## Features",
            *[f"- `{name}`" for name in training_result.feature_names],
            "",
            "## Validation Metrics",
            "```json",
            json.dumps(summary["validation_metrics"], indent=2, sort_keys=True, default=str),
            "```",
            "",
            "## Limitations",
            "Sparse reference analyst labels limit statistical confidence.",
            "This model complements Isolation Forest and composite risk scoring.",
            "",
            "## Leakage Controls",
            "Training uses supervised-readiness labels and timestamp-aware validation splits.",
            "",
            "## Reference Data Caveat",
            "Outputs are portfolio demonstration artefacts, not production model approvals.",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to write supervised model card: {exc}") from exc


def write_supervised_model_artifact(
    training_result: SupervisedTrainingResult,
    output_path: Path | str = "reports/model_validation/supervised_model.joblib",
) -> Path:
    path = Path(output_path)
    try:
        _ensure_parent(path)
        joblib.dump(
            {
                "estimator": training_result.estimator,
                "preprocessing_pipeline": training_result.preprocessing_pipeline,
                "feature_names": training_result.feature_names,
                "metadata": supervised_training_result_to_dict(training_result),
            },
            path,
        )
        return path
    except Exception as exc:
        message = f"failed to write supervised model artifact: {exc}"
        raise SupervisedPersistenceError(message) from exc


def generate_supervised_model_artefacts(
    training_result: SupervisedTrainingResult,
    scores: pd.DataFrame,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write all supervised model artefacts."""

    directory = Path(output_dir)
    return {
        "supervised_scores_csv": write_supervised_scores_csv(
            scores,
            directory / "supervised_model_scores.csv",
        ),
        "supervised_metrics_json": write_supervised_metrics_json(
            training_result,
            directory / "supervised_model_metrics.json",
        ),
        "supervised_threshold_metrics_csv": write_supervised_threshold_metrics_csv(
            training_result,
            directory / "supervised_threshold_metrics.csv",
        ),
        "supervised_top_k_metrics_csv": write_supervised_top_k_metrics_csv(
            training_result,
            directory / "supervised_top_k_metrics.csv",
        ),
        "supervised_model_card_md": write_supervised_model_card_md(
            training_result,
            scores,
            directory / "supervised_model_card.md",
        ),
        "supervised_model_artifact": write_supervised_model_artifact(
            training_result,
            directory / "supervised_model.joblib",
        ),
    }
