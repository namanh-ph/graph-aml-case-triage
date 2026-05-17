"""Model metric summarisation helpers for dashboard pages."""

from __future__ import annotations

import pandas as pd

from graph_aml.dashboard.config import DashboardConfig
from graph_aml.dashboard.exceptions import DashboardDataError


def build_score_distribution_summary(
    scores: pd.DataFrame,
    score_column: str,
    risk_band_column: str | None = "risk_band",
) -> dict[str, object]:
    if not isinstance(scores, pd.DataFrame):
        raise DashboardDataError("scores must be a DataFrame")
    if scores.empty or score_column not in scores.columns:
        return {
            "row_count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
            "risk_band_counts": {},
        }
    series = pd.to_numeric(scores[score_column], errors="coerce").dropna()
    bands = (
        scores[risk_band_column].dropna().astype(str).value_counts().sort_index().to_dict()
        if risk_band_column and risk_band_column in scores.columns
        else {}
    )
    return {
        "row_count": int(len(scores)),
        "min": None if series.empty else float(series.min()),
        "max": None if series.empty else float(series.max()),
        "mean": None if series.empty else float(series.mean()),
        "median": None if series.empty else float(series.median()),
        "std": None if series.empty else float(series.std(ddof=0)),
        "risk_band_counts": {str(key): int(value) for key, value in bands.items()},
    }


def build_top_ranked_scores(
    scores: pd.DataFrame,
    rank_column: str,
    score_column: str,
    top_k: int = 25,
) -> pd.DataFrame:
    if not isinstance(scores, pd.DataFrame):
        raise DashboardDataError("scores must be a DataFrame")
    if top_k <= 0:
        raise DashboardDataError("top_k must be positive")
    frame = scores.copy(deep=True)
    if frame.empty:
        return frame
    if rank_column in frame.columns:
        return frame.sort_values(
            by=[rank_column, score_column],
            ascending=[True, False],
            na_position="last",
        ).head(top_k)
    if score_column not in frame.columns:
        raise DashboardDataError(f"{score_column} is required")
    return frame.sort_values(by=score_column, ascending=False, na_position="last").head(top_k)


def build_precision_at_k_placeholder(
    scores: pd.DataFrame,
    top_k_values: tuple[int, ...] | list[int],
    label_column: str | None = None,
    rank_column: str | None = None,
) -> pd.DataFrame:
    if not isinstance(scores, pd.DataFrame):
        raise DashboardDataError("scores must be a DataFrame")
    if not top_k_values or any(int(value) <= 0 for value in top_k_values):
        raise DashboardDataError("top_k_values must be positive")
    frame = scores.copy(deep=True)
    if rank_column and rank_column in frame.columns:
        frame = frame.sort_values(rank_column, ascending=True, na_position="last")
    rows: list[dict[str, object]] = []
    has_labels = bool(label_column and label_column in frame.columns)
    for value in top_k_values:
        top_k = int(value)
        if has_labels:
            labels = pd.to_numeric(frame.head(top_k)[str(label_column)], errors="coerce").fillna(0)
            positives = int((labels > 0).sum())
            rows.append(
                {
                    "top_k": top_k,
                    "precision_at_k": float(positives / max(1, min(top_k, len(frame)))),
                    "label_count": int(len(labels)),
                    "status": "computed",
                }
            )
        else:
            rows.append(
                {
                    "top_k": top_k,
                    "precision_at_k": None,
                    "label_count": 0,
                    "status": "label_unavailable",
                }
            )
    return pd.DataFrame(rows)


def build_model_metrics_summary(
    bundle: dict[str, pd.DataFrame],
    config: DashboardConfig | None = None,
) -> dict[str, object]:
    if not isinstance(bundle, dict):
        raise DashboardDataError("bundle must be a dictionary")
    resolved = config or DashboardConfig()
    anomaly = bundle.get("account_anomaly_scores", pd.DataFrame())
    account = bundle.get("account_risk_scores", pd.DataFrame())
    case = bundle.get("case_risk_scores", pd.DataFrame())
    supervised = bundle.get("supervised_model_scores", pd.DataFrame())
    runs = bundle.get("model_runs", pd.DataFrame())
    supervised_runs = bundle.get("supervised_model_runs", pd.DataFrame())
    comparison_runs = bundle.get("model_comparison_runs", pd.DataFrame())
    champion_rows = bundle.get("champion_challenger_results", pd.DataFrame())
    monitoring_runs = bundle.get("monitoring_runs", pd.DataFrame())
    explainability_runs = bundle.get("explainability_runs", pd.DataFrame())
    model_cards = bundle.get("model_cards", pd.DataFrame())
    champion = (
        champion_rows[champion_rows["is_champion"]]
        if "is_champion" in champion_rows
        else pd.DataFrame()
    )
    return {
        "model_run_count": int(len(runs)) + int(len(supervised_runs)),
        "model_comparison_run_count": int(len(comparison_runs)),
        "monitoring_run_count": int(len(monitoring_runs)),
        "explainability_run_count": int(len(explainability_runs)),
        "latest_monitoring_run_id": None
        if monitoring_runs.empty or "monitoring_run_id" not in monitoring_runs
        else str(monitoring_runs["monitoring_run_id"].iloc[0]),
        "latest_explanation_run_id": None
        if explainability_runs.empty or "explanation_run_id" not in explainability_runs
        else str(explainability_runs["explanation_run_id"].iloc[0]),
        "model_card_count": int(len(model_cards)),
        "latest_champion_candidate": None
        if champion.empty
        else str(champion["candidate_name"].iloc[0]),
        "anomaly_score_summary": build_score_distribution_summary(anomaly, "anomaly_score"),
        "account_risk_summary": build_score_distribution_summary(account, "account_risk_score"),
        "case_risk_summary": build_score_distribution_summary(case, "case_risk_score"),
        "supervised_score_summary": build_score_distribution_summary(
            supervised,
            "supervised_score",
            None,
        ),
        "top_k_values": [int(value) for value in resolved.model_metrics.default_top_k_values],
    }
