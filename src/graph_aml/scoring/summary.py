"""Summary helpers for account risk scoring."""

from __future__ import annotations

import pandas as pd

from graph_aml.scoring.composite import AccountRiskScoreResult
from graph_aml.scoring.validation import build_account_risk_score_quality_summary


def summarise_risk_components(components: pd.DataFrame) -> dict[str, object]:
    """Summarise component score frame."""

    if components.empty:
        return {"row_count": 0, "unique_account_count": 0, "component_means": {}}
    score_columns = [column for column in components.columns if column.endswith("_score")]
    return {
        "row_count": int(len(components)),
        "unique_account_count": int(components["account_id"].nunique())
        if "account_id" in components
        else 0,
        "component_means": {
            column: float(pd.to_numeric(components[column], errors="coerce").fillna(0.0).mean())
            for column in score_columns
        },
    }


def summarise_account_risk_scores(scores: pd.DataFrame) -> dict[str, object]:
    """Summarise account risk score frame."""

    return build_account_risk_score_quality_summary(scores)


def account_risk_score_result_to_dict(
    result: AccountRiskScoreResult,
) -> dict[str, object]:
    """Convert an account risk score result to a JSON-ready dictionary."""

    records = (
        result.scores.astype(object).where(pd.notna(result.scores), None).to_dict(orient="records")
        if not result.scores.empty
        else []
    )
    return {
        "scores": records,
        "summary": dict(result.summary),
        "metadata": dict(result.metadata),
    }
