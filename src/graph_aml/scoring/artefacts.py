"""Local artefact writers for account risk scoring."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.scoring.composite import AccountRiskScoreResult
from graph_aml.scoring.exceptions import ScoringPersistenceError, ScoringValidationError
from graph_aml.scoring.persistence import AccountRiskScorePersistenceResult
from graph_aml.scoring.summary import account_risk_score_result_to_dict


def _write_json(payload: object, output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        raise ScoringPersistenceError(f"Failed to write scoring JSON artefact: {exc}") from exc
    return path


def write_account_risk_scores_csv(
    scores: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/account_risk_scores.csv",
) -> Path:
    """Write account risk scores as CSV."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        scores.to_csv(path, index=False)
    except Exception as exc:
        raise ScoringPersistenceError(f"Failed to write account risk score CSV: {exc}") from exc
    return path


def write_account_risk_scores_json(
    scores: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/account_risk_scores.json",
) -> Path:
    """Write account risk scores as JSON records."""

    records = scores.astype(object).where(pd.notna(scores), None).to_dict(orient="records")
    return _write_json(records, output_path)


def write_account_risk_score_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/account_risk_score_summary.json",
) -> Path:
    """Write account risk score summary JSON."""

    if not isinstance(summary, dict):
        raise ScoringValidationError("summary must be a dictionary")
    return _write_json(summary, output_path)


def _persistence_result_to_dict(result: AccountRiskScorePersistenceResult) -> dict[str, object]:
    return {
        "rows_prepared": result.rows_prepared,
        "rows_persisted": result.rows_persisted,
        "unique_account_count": result.unique_account_count,
        "score_date": result.score_date,
        "score_name": result.score_name,
        "score_version": result.score_version,
        "persisted": result.persisted,
        "metadata": result.metadata,
        "summary": result.summary,
    }


def write_account_risk_score_persistence_summary_json(
    result: AccountRiskScorePersistenceResult,
    output_path: Path
    | str = "reports/model_validation/account_risk_score_persistence_summary.json",
) -> Path:
    """Write account risk score persistence summary JSON."""

    if not isinstance(result, AccountRiskScorePersistenceResult):
        raise ScoringValidationError("result must be AccountRiskScorePersistenceResult")
    return _write_json(_persistence_result_to_dict(result), output_path)


def generate_account_risk_score_artefacts(
    scoring_result: AccountRiskScoreResult,
    persistence_result: AccountRiskScorePersistenceResult | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write account risk scoring artefacts."""

    if not isinstance(scoring_result, AccountRiskScoreResult):
        raise ScoringValidationError("scoring_result must be AccountRiskScoreResult")
    directory = Path(output_dir)
    paths = {
        "scores_csv": write_account_risk_scores_csv(
            scoring_result.scores,
            directory / "account_risk_scores.csv",
        ),
        "scores_json": write_account_risk_scores_json(
            scoring_result.scores,
            directory / "account_risk_scores.json",
        ),
        "score_summary_json": write_account_risk_score_summary_json(
            account_risk_score_result_to_dict(scoring_result),
            directory / "account_risk_score_summary.json",
        ),
    }
    if persistence_result is not None:
        paths["persistence_summary_json"] = write_account_risk_score_persistence_summary_json(
            persistence_result,
            directory / "account_risk_score_persistence_summary.json",
        )
    return paths
