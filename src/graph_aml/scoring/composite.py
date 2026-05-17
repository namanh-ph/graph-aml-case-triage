"""Weighted composite account risk score computation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import pandas as pd
from sqlalchemy import Engine

from graph_aml.scoring.components import (
    RISK_COMPONENT_COLUMNS,
    build_account_risk_components,
    clip_score,
)
from graph_aml.scoring.config import AccountRiskScoringConfig
from graph_aml.scoring.exceptions import ScoringComputationError

ACCOUNT_RISK_SCORE_COLUMNS = (
    "account_id",
    "score_date",
    "score_name",
    "score_version",
    "account_risk_score",
    "risk_band",
    "risk_rank",
    "rule_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "customer_risk_score",
    "jurisdiction_risk_score",
    "component_coverage",
    "alert_count",
    "high_severity_alert_count",
    "critical_severity_alert_count",
    "max_rule_alert_score",
    "mean_rule_alert_score",
    "max_anomaly_score",
    "graph_percentile_score",
)


@dataclass(frozen=True)
class AccountRiskScoreResult:
    """Composite account risk score output."""

    scores: pd.DataFrame
    components: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def assign_account_risk_band(
    score: float,
    config: AccountRiskScoringConfig | None = None,
) -> str:
    """Assign a configured risk band for a 0-100 score."""

    resolved = AccountRiskScoringConfig() if config is None else config
    value = clip_score(score)
    if value >= resolved.risk_bands["critical"]:
        return "critical"
    if value >= resolved.risk_bands["high"]:
        return "high"
    if value >= resolved.risk_bands["medium"]:
        return "medium"
    return "low"


def _summary(scores: pd.DataFrame, config: AccountRiskScoringConfig) -> dict[str, object]:
    if scores.empty:
        return {
            "row_count": 0,
            "unique_account_count": 0,
            "min_score": None,
            "max_score": None,
            "mean_score": None,
            "risk_band_counts": {},
            "component_coverage_mean": None,
            "accounts_below_component_coverage_threshold": 0,
        }
    risk_band_counts = scores["risk_band"].value_counts().sort_index().to_dict()
    score_values = pd.to_numeric(scores["account_risk_score"], errors="coerce")
    coverage = pd.to_numeric(scores["component_coverage"], errors="coerce")
    return {
        "row_count": int(len(scores)),
        "unique_account_count": int(scores["account_id"].nunique()),
        "min_score": float(score_values.min()),
        "max_score": float(score_values.max()),
        "mean_score": float(score_values.mean()),
        "risk_band_counts": {str(key): int(value) for key, value in risk_band_counts.items()},
        "component_coverage_mean": float(coverage.mean()),
        "accounts_below_component_coverage_threshold": int(
            (coverage < config.min_component_coverage).sum()
        ),
    }


def compute_account_risk_scores(
    components: pd.DataFrame,
    config: AccountRiskScoringConfig | None = None,
    score_date: date | None = None,
) -> AccountRiskScoreResult:
    """Compute weighted composite account risk scores from component scores."""

    resolved = AccountRiskScoringConfig() if config is None else config
    try:
        missing = set(RISK_COMPONENT_COLUMNS).difference(components.columns)
        if missing:
            raise ScoringComputationError(f"components missing required columns: {sorted(missing)}")
        if components.empty:
            raise ScoringComputationError("components must not be empty")
        output = components.copy()
        output["account_id"] = output["account_id"].astype("string").str.strip()
        output = output[output["account_id"].notna() & (output["account_id"] != "")]
        for column in resolved.weights:
            output[column] = (
                pd.to_numeric(output[column], errors="coerce").fillna(0.0).map(clip_score)
            )
        output["account_risk_score"] = sum(
            output[column] * float(weight) for column, weight in resolved.weights.items()
        ).map(clip_score)
        output["score_date"] = score_date or datetime.now(UTC).date()
        output["score_name"] = resolved.score_name
        output["score_version"] = resolved.score_version
        output["risk_band"] = output["account_risk_score"].map(
            lambda value: assign_account_risk_band(float(value), resolved)
        )
        output = output.sort_values(
            ["account_risk_score", "account_id"],
            ascending=[False, True],
        ).reset_index(drop=True)
        output["risk_rank"] = range(1, len(output) + 1)
        scores = output.loc[:, ACCOUNT_RISK_SCORE_COLUMNS].copy()
        metadata: dict[str, object] = {
            "score_name": resolved.score_name,
            "score_version": resolved.score_version,
            "weights": dict(resolved.weights),
            "score_date": str(scores.iloc[0]["score_date"]) if not scores.empty else None,
        }
        return AccountRiskScoreResult(
            scores=scores,
            components=components.copy(),
            summary=_summary(scores, resolved),
            metadata=metadata,
        )
    except ScoringComputationError:
        raise
    except Exception as exc:
        raise ScoringComputationError(f"Failed to compute account risk scores: {exc}") from exc


def compute_account_risk_scores_from_inputs(
    inputs: dict[str, pd.DataFrame],
    config: AccountRiskScoringConfig | None = None,
    score_date: date | None = None,
) -> AccountRiskScoreResult:
    """Compute account risk scores from input frame dictionary."""

    resolved = AccountRiskScoringConfig() if config is None else config
    try:
        components = build_account_risk_components(
            inputs.get("accounts", pd.DataFrame()),
            inputs.get("alerts", pd.DataFrame()),
            inputs.get("graph_features", pd.DataFrame()),
            inputs.get("anomaly_scores", pd.DataFrame()),
            resolved,
        )
        return compute_account_risk_scores(components, resolved, score_date=score_date)
    except ScoringComputationError:
        raise
    except Exception as exc:
        raise ScoringComputationError(
            f"Failed to compute account risk scores from inputs: {exc}"
        ) from exc


def compute_and_persist_account_risk_scores(
    engine: Engine,
    scoring_config: AccountRiskScoringConfig | None = None,
    persistence_config: object | None = None,
    limit: int | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> tuple[AccountRiskScoreResult, object]:
    """Read scoring inputs, compute scores, and persist them."""

    from graph_aml.scoring.inputs import read_scoring_feature_inputs
    from graph_aml.scoring.persistence import (
        AccountRiskScorePersistenceConfig,
        persist_account_risk_scores,
    )

    resolved = AccountRiskScoringConfig() if scoring_config is None else scoring_config
    try:
        inputs = read_scoring_feature_inputs(engine, resolved, limit=limit)
        scoring_result = compute_account_risk_scores_from_inputs(
            inputs,
            resolved,
            score_date=resolved.feature_date,
        )
        persist_config = (
            AccountRiskScorePersistenceConfig(
                score_date=resolved.feature_date,
                score_name=resolved.score_name,
                score_version=resolved.score_version,
            )
            if persistence_config is None
            else persistence_config
        )
        persistence_result = persist_account_risk_scores(
            engine,
            scoring_result,
            persist_config,  # type: ignore[arg-type]
            extra_metadata=extra_metadata,
        )
        return scoring_result, persistence_result
    except Exception as exc:
        if isinstance(exc, ScoringComputationError):
            raise
        raise ScoringComputationError(
            f"Failed to compute and persist account risk scores: {exc}"
        ) from exc
