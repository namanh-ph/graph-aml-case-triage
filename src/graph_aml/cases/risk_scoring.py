"""Composite case-level risk scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import pandas as pd
from sqlalchemy import Engine

from graph_aml.cases.exceptions import CaseRiskComputationError
from graph_aml.cases.risk_components import (
    CASE_RISK_COMPONENT_COLUMNS,
    build_case_risk_components,
    clip_case_score,
)
from graph_aml.cases.risk_config import CaseRiskScoringConfig

CASE_RISK_SCORE_COLUMNS = (
    "case_id",
    "score_date",
    "score_name",
    "score_version",
    "case_risk_score",
    "risk_band",
    "risk_rank",
    "alert_risk_score",
    "account_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "typology_diversity_score",
    "evidence_value_score",
    "component_coverage",
    "alert_count",
    "typology_count",
    "related_account_count",
    "evidence_transaction_count",
    "total_transaction_value",
    "max_alert_score",
    "max_account_risk_score",
    "max_anomaly_score",
)


@dataclass(frozen=True)
class CaseRiskScoreResult:
    scores: pd.DataFrame
    components: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def assign_case_risk_band(score: float, config: CaseRiskScoringConfig | None = None) -> str:
    resolved = CaseRiskScoringConfig() if config is None else config
    value = clip_case_score(score)
    if value >= resolved.risk_bands["critical"]:
        return "critical"
    if value >= resolved.risk_bands["high"]:
        return "high"
    if value >= resolved.risk_bands["medium"]:
        return "medium"
    return "low"


def _summary(scores: pd.DataFrame, config: CaseRiskScoringConfig) -> dict[str, object]:
    if scores.empty:
        return {
            "row_count": 0,
            "unique_case_count": 0,
            "min_score": 0.0,
            "max_score": 0.0,
            "mean_score": 0.0,
            "risk_band_counts": {},
            "component_coverage_mean": 0.0,
            "cases_below_component_coverage_threshold": 0,
        }
    case_scores = pd.to_numeric(scores["case_risk_score"], errors="coerce").fillna(0)
    coverage = pd.to_numeric(scores["component_coverage"], errors="coerce").fillna(0)
    return {
        "row_count": int(len(scores)),
        "unique_case_count": int(scores["case_id"].nunique(dropna=True)),
        "min_score": float(case_scores.min()),
        "max_score": float(case_scores.max()),
        "mean_score": float(case_scores.mean()),
        "risk_band_counts": {
            str(key): int(value)
            for key, value in scores["risk_band"].astype(str).value_counts().sort_index().items()
        },
        "component_coverage_mean": float(coverage.mean()),
        "cases_below_component_coverage_threshold": int(
            (coverage < config.thresholds.min_component_coverage).sum()
        ),
    }


def compute_case_risk_scores(
    components: pd.DataFrame,
    config: CaseRiskScoringConfig | None = None,
    score_date: date | None = None,
) -> CaseRiskScoreResult:
    resolved = CaseRiskScoringConfig() if config is None else config
    try:
        if components.empty:
            raise CaseRiskComputationError("case risk components are empty")
        missing = set(CASE_RISK_COMPONENT_COLUMNS).difference(components.columns)
        if missing:
            raise CaseRiskComputationError(
                f"case risk components missing columns: {sorted(missing)}"
            )
        output = components.copy(deep=True)
        for column, weight in resolved.weights.items():
            output[column] = pd.to_numeric(output[column], errors="coerce").fillna(0)
            output[column] = output[column].clip(0, 100)
            output[f"_{column}_weighted"] = output[column] * weight
        weighted_columns = [f"_{column}_weighted" for column in resolved.weights]
        output["case_risk_score"] = output.loc[:, weighted_columns].sum(axis=1).clip(0, 100)
        output["score_date"] = score_date or datetime.now(UTC).date()
        output["score_name"] = resolved.score_name
        output["score_version"] = resolved.score_version
        output["risk_band"] = output["case_risk_score"].apply(
            lambda value: assign_case_risk_band(float(value), resolved)
        )
        output = output.sort_values(
            ["case_risk_score", "case_id"], ascending=[False, True], kind="mergesort"
        )
        output["risk_rank"] = range(1, len(output) + 1)
        output = output.loc[:, CASE_RISK_SCORE_COLUMNS].reset_index(drop=True)
        metadata: dict[str, object] = {
            "score_name": resolved.score_name,
            "score_version": resolved.score_version,
            "weights": dict(resolved.weights),
            "score_date": str(output.iloc[0]["score_date"])
            if not output.empty
            else str(score_date),
            "case_version": resolved.case_version,
            "account_risk_score_version": resolved.account_risk_score_version,
            "graph_feature_version": resolved.graph_feature_version,
            "graph_build_id": resolved.graph_build_id,
            "anomaly_model_version": resolved.anomaly_model_version,
            "anomaly_model_run_id": resolved.anomaly_model_run_id,
        }
        return CaseRiskScoreResult(
            scores=output,
            components=components.copy(deep=True),
            summary=_summary(output, resolved),
            metadata=metadata,
        )
    except CaseRiskComputationError:
        raise
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to compute case risk scores: {exc}") from exc


def compute_case_risk_scores_from_inputs(
    inputs: dict[str, pd.DataFrame],
    config: CaseRiskScoringConfig | None = None,
    score_date: date | None = None,
) -> CaseRiskScoreResult:
    resolved = CaseRiskScoringConfig() if config is None else config
    try:
        components = build_case_risk_components(
            inputs.get("cases", pd.DataFrame()),
            inputs.get("case_alerts", pd.DataFrame()),
            inputs.get("alerts", pd.DataFrame()),
            inputs.get("account_risk_scores", pd.DataFrame()),
            inputs.get("graph_features", pd.DataFrame()),
            inputs.get("anomaly_scores", pd.DataFrame()),
            inputs.get("transactions", pd.DataFrame()),
            resolved,
        )
        return compute_case_risk_scores(components, resolved, score_date=score_date)
    except CaseRiskComputationError:
        raise
    except Exception as exc:
        raise CaseRiskComputationError(
            f"failed to compute case risk scores from inputs: {exc}"
        ) from exc


def compute_and_persist_case_risk_scores(
    engine: Engine,
    scoring_config: CaseRiskScoringConfig | None = None,
    persistence_config: Any | None = None,
    limit: int | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> tuple[CaseRiskScoreResult, Any]:
    """Read inputs, compute case risk scores, and persist them."""

    resolved = CaseRiskScoringConfig() if scoring_config is None else scoring_config
    try:
        from graph_aml.cases.risk_inputs import read_case_risk_inputs
        from graph_aml.cases.risk_persistence import (
            CaseRiskScorePersistenceConfig,
            persist_case_risk_scores,
        )

        inputs = read_case_risk_inputs(engine, resolved, limit=limit)
        score_result = compute_case_risk_scores_from_inputs(inputs, resolved)
        persist_config = persistence_config or CaseRiskScorePersistenceConfig(
            score_name=resolved.score_name,
            score_version=resolved.score_version,
        )
        persistence_result = persist_case_risk_scores(
            engine,
            score_result,
            persist_config,
            extra_metadata=extra_metadata,
        )
        return score_result, persistence_result
    except CaseRiskComputationError:
        raise
    except Exception as exc:
        raise CaseRiskComputationError(
            f"failed to compute and persist case risk scores: {exc}"
        ) from exc
