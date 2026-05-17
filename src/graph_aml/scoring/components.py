"""Component score construction for composite account risk scoring."""

from __future__ import annotations

import math
from typing import Any, cast

import pandas as pd

from graph_aml.scoring.config import AccountRiskScoringConfig
from graph_aml.scoring.exceptions import ScoringComputationError

RISK_COMPONENT_COLUMNS = (
    "account_id",
    "rule_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "customer_risk_score",
    "jurisdiction_risk_score",
    "alert_count",
    "high_severity_alert_count",
    "critical_severity_alert_count",
    "max_rule_alert_score",
    "mean_rule_alert_score",
    "max_anomaly_score",
    "graph_percentile_score",
    "component_coverage",
)

_MAJOR_COMPONENTS = (
    "rule_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "customer_risk_score",
    "jurisdiction_risk_score",
)


def _account_frame(accounts: pd.DataFrame) -> pd.DataFrame:
    if "account_id" not in accounts.columns:
        raise ScoringComputationError("accounts must include account_id")
    output = accounts.copy()
    output["account_id"] = output["account_id"].astype("string").str.strip()
    output = output[output["account_id"].notna() & (output["account_id"] != "")]
    output = output.sort_values("account_id").drop_duplicates("account_id", keep="last")
    return output


def clip_score(value: object, lower: float = 0.0, upper: float = 100.0) -> float:
    """Coerce and bound a score."""

    try:
        number = float(cast(Any, value))
    except (TypeError, ValueError):
        number = lower
    if math.isnan(number) or math.isinf(number):
        number = lower
    return float(min(max(number, lower), upper))


def percentile_rank_score(values: pd.Series) -> pd.Series:
    """Return stable percentile-rank scores on a 0-100 scale."""

    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if numeric.empty:
        return pd.Series(dtype="float64")
    if len(numeric) == 1:
        return pd.Series([100.0 if numeric.iloc[0] > 0 else 0.0], index=numeric.index)
    ranks = numeric.rank(method="average", pct=True)
    return (ranks * 100.0).clip(0, 100)


def map_severity_to_score(
    severity: object,
    config: AccountRiskScoringConfig | None = None,
) -> float:
    """Map alert severity to a configured score."""

    resolved = AccountRiskScoringConfig() if config is None else config
    key = str(severity or "").strip().lower()
    return clip_score(resolved.severity_scores.get(key, 0.0))


def map_risk_rating_to_score(
    risk_rating: object,
    config: AccountRiskScoringConfig | None = None,
) -> float:
    """Map customer risk rating to a configured score."""

    resolved = AccountRiskScoringConfig() if config is None else config
    key = str(risk_rating or "unknown").strip().lower() or "unknown"
    return clip_score(
        resolved.customer_risk_scores.get(key, resolved.customer_risk_scores["unknown"])
    )


def compute_rule_risk_component(
    accounts: pd.DataFrame,
    alerts: pd.DataFrame,
    config: AccountRiskScoringConfig | None = None,
) -> pd.DataFrame:
    """Compute account rule-alert risk component."""

    resolved = AccountRiskScoringConfig() if config is None else config
    try:
        base = _account_frame(accounts).loc[:, ["account_id"]].copy()
        defaults = {
            "rule_risk_score": 0.0,
            "alert_count": 0,
            "high_severity_alert_count": 0,
            "critical_severity_alert_count": 0,
            "max_rule_alert_score": 0.0,
            "mean_rule_alert_score": 0.0,
        }
        if alerts.empty or "account_id" not in alerts.columns:
            for key, value in defaults.items():
                base[key] = value
            return base
        frame = alerts.copy()
        frame["account_id"] = frame["account_id"].astype("string").str.strip()
        frame = frame[frame["account_id"].notna() & (frame["account_id"] != "")]
        severity_score = frame.get("severity", pd.Series(index=frame.index, dtype="object")).map(
            lambda value: map_severity_to_score(value, resolved)
        )
        rule_score = pd.to_numeric(frame.get("risk_score_rule"), errors="coerce")
        frame["alert_score"] = pd.concat([rule_score.fillna(0.0), severity_score], axis=1).max(
            axis=1
        )
        frame["severity_lower"] = frame.get("severity", "").astype(str).str.lower()
        grouped = frame.groupby("account_id", dropna=True).agg(
            alert_count=("alert_score", "size"),
            high_severity_alert_count=(
                "severity_lower",
                lambda values: int((values == "high").sum()),
            ),
            critical_severity_alert_count=(
                "severity_lower",
                lambda values: int((values == "critical").sum()),
            ),
            max_rule_alert_score=("alert_score", "max"),
            mean_rule_alert_score=("alert_score", "mean"),
        )
        grouped["rule_risk_score"] = (
            grouped["max_rule_alert_score"] + (grouped["alert_count"] - 1).clip(lower=0) * 2.0
        ).map(clip_score)
        output = base.merge(grouped.reset_index(), on="account_id", how="left")
        for key, value in defaults.items():
            output[key] = output[key].fillna(value)
        return output.loc[
            :,
            [
                "account_id",
                "rule_risk_score",
                "alert_count",
                "high_severity_alert_count",
                "critical_severity_alert_count",
                "max_rule_alert_score",
                "mean_rule_alert_score",
            ],
        ]
    except ScoringComputationError:
        raise
    except Exception as exc:
        raise ScoringComputationError(f"Failed to compute rule risk component: {exc}") from exc


def _column_or_zero(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([0.0] * len(frame), index=frame.index)
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0)


def _proximity_score(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    scores = numeric.map(
        lambda value: 0.0 if pd.isna(value) else max(0.0, 125.0 - (float(value) * 25.0))
    )
    return scores.clip(0, 100).fillna(0.0)


def compute_graph_risk_component(
    accounts: pd.DataFrame,
    graph_features: pd.DataFrame,
    config: AccountRiskScoringConfig | None = None,
) -> pd.DataFrame:
    """Compute graph-derived account risk component."""

    resolved = AccountRiskScoringConfig() if config is None else config
    try:
        base = _account_frame(accounts).loc[:, ["account_id"]].copy()
        if graph_features.empty or "account_id" not in graph_features.columns:
            base["graph_risk_score"] = 0.0
            base["graph_percentile_score"] = 0.0
            return base
        graph = graph_features.copy()
        graph["account_id"] = graph["account_id"].astype("string").str.strip()
        graph = graph.sort_values("account_id").drop_duplicates("account_id", keep="last")
        components = pd.DataFrame({"account_id": graph["account_id"]})
        components["pagerank_percentile"] = percentile_rank_score(
            _column_or_zero(graph, "pagerank_score")
        )
        components["degree_percentile"] = percentile_rank_score(
            _column_or_zero(graph, "degree_centrality").where(
                _column_or_zero(graph, "degree_centrality") != 0,
                _column_or_zero(graph, "degree"),
            )
        )
        components["betweenness_percentile"] = percentile_rank_score(
            _column_or_zero(graph, "betweenness_centrality")
        )
        components["cycle_count_percentile"] = percentile_rank_score(
            _column_or_zero(graph, "cycle_count")
        )
        components["high_risk_alert_count_percentile"] = percentile_rank_score(
            _column_or_zero(graph, "high_risk_alert_count")
        )
        components["proximity_score"] = _proximity_score(
            graph.get("shortest_path_to_flagged", pd.Series(index=graph.index))
        )
        weights = resolved.graph_component_weights
        weighted = sum(components[column] * float(weight) for column, weight in weights.items())
        percentile_columns = [column for column in weights if column != "proximity_score"]
        components["graph_percentile_score"] = (
            components[percentile_columns].mean(axis=1).fillna(0.0)
        )
        components["graph_risk_score"] = weighted.map(clip_score)
        output = base.merge(
            components.loc[:, ["account_id", "graph_risk_score", "graph_percentile_score"]],
            on="account_id",
            how="left",
        )
        output[["graph_risk_score", "graph_percentile_score"]] = output[
            ["graph_risk_score", "graph_percentile_score"]
        ].fillna(0.0)
        return output
    except Exception as exc:
        raise ScoringComputationError(f"Failed to compute graph risk component: {exc}") from exc


def compute_anomaly_risk_component(
    accounts: pd.DataFrame,
    anomaly_scores: pd.DataFrame,
    config: AccountRiskScoringConfig | None = None,
) -> pd.DataFrame:
    """Compute anomaly model risk component."""

    _ = AccountRiskScoringConfig() if config is None else config
    try:
        base = _account_frame(accounts).loc[:, ["account_id"]].copy()
        if anomaly_scores.empty or "account_id" not in anomaly_scores.columns:
            base["anomaly_risk_score"] = 0.0
            base["max_anomaly_score"] = 0.0
            return base
        frame = anomaly_scores.copy()
        frame["account_id"] = frame["account_id"].astype("string").str.strip()
        frame["anomaly_score"] = pd.to_numeric(frame.get("anomaly_score"), errors="coerce").fillna(
            0.0
        )
        sort_columns = ["account_id", "anomaly_score"]
        ascending = [True, True]
        if "scored_at" in frame.columns:
            sort_columns.append("scored_at")
            ascending.append(True)
        frame = frame.sort_values(sort_columns, ascending=ascending).drop_duplicates(
            "account_id",
            keep="last",
        )
        frame["max_anomaly_score"] = frame["anomaly_score"].map(clip_score)
        frame["anomaly_risk_score"] = frame["max_anomaly_score"]
        output = base.merge(
            frame.loc[:, ["account_id", "anomaly_risk_score", "max_anomaly_score"]],
            on="account_id",
            how="left",
        )
        output[["anomaly_risk_score", "max_anomaly_score"]] = output[
            ["anomaly_risk_score", "max_anomaly_score"]
        ].fillna(0.0)
        return output
    except Exception as exc:
        raise ScoringComputationError(f"Failed to compute anomaly risk component: {exc}") from exc


def compute_customer_risk_component(
    accounts: pd.DataFrame,
    config: AccountRiskScoringConfig | None = None,
) -> pd.DataFrame:
    """Compute customer risk rating component."""

    resolved = AccountRiskScoringConfig() if config is None else config
    try:
        frame = _account_frame(accounts)
        rating = pd.Series(["unknown"] * len(frame), index=frame.index)
        for column in ("customer_risk_rating", "risk_rating", "account_risk_rating"):
            if column in frame.columns:
                rating = frame[column]
                break
        output = frame.loc[:, ["account_id"]].copy()
        output["customer_risk_score"] = rating.map(
            lambda value: map_risk_rating_to_score(value, resolved)
        )
        return output
    except Exception as exc:
        raise ScoringComputationError(f"Failed to compute customer risk component: {exc}") from exc


def compute_jurisdiction_risk_component(
    accounts: pd.DataFrame,
    graph_features: pd.DataFrame | None = None,
    config: AccountRiskScoringConfig | None = None,
) -> pd.DataFrame:
    """Compute jurisdiction exposure risk component."""

    resolved = AccountRiskScoringConfig() if config is None else config
    try:
        frame = _account_frame(accounts)
        output = frame.loc[:, ["account_id"]].copy()
        exposure = None
        for source in (frame, graph_features if graph_features is not None else pd.DataFrame()):
            if "high_risk_country_exposure" in source.columns:
                source_frame = source.copy()
                source_frame["account_id"] = source_frame["account_id"].astype("string").str.strip()
                exposure = output.merge(
                    source_frame.loc[:, ["account_id", "high_risk_country_exposure"]],
                    on="account_id",
                    how="left",
                )["high_risk_country_exposure"]
                break
        if exposure is not None:
            numeric = pd.to_numeric(exposure, errors="coerce").clip(0, 1)
            output["jurisdiction_risk_score"] = (
                numeric * resolved.high_risk_country_score
                + (1 - numeric) * resolved.standard_country_score
            ).fillna(resolved.unknown_country_score)
        else:
            jurisdiction = frame.get(
                "home_country", frame.get("jurisdiction", pd.Series(index=frame.index))
            )
            output["jurisdiction_risk_score"] = jurisdiction.map(
                lambda value: (
                    resolved.unknown_country_score
                    if pd.isna(value) or str(value).strip() == ""
                    else resolved.standard_country_score
                )
            )
        output["jurisdiction_risk_score"] = output["jurisdiction_risk_score"].map(clip_score)
        return output
    except Exception as exc:
        raise ScoringComputationError(
            f"Failed to compute jurisdiction risk component: {exc}"
        ) from exc


def build_account_risk_components(
    accounts: pd.DataFrame,
    alerts: pd.DataFrame,
    graph_features: pd.DataFrame,
    anomaly_scores: pd.DataFrame,
    config: AccountRiskScoringConfig | None = None,
) -> pd.DataFrame:
    """Build all account risk components in one deterministic frame."""

    resolved = AccountRiskScoringConfig() if config is None else config
    try:
        base = _account_frame(accounts).loc[:, ["account_id"]].copy()
        frames = [
            compute_rule_risk_component(accounts, alerts, resolved),
            compute_graph_risk_component(accounts, graph_features, resolved),
            compute_anomaly_risk_component(accounts, anomaly_scores, resolved),
            compute_customer_risk_component(accounts, resolved),
            compute_jurisdiction_risk_component(accounts, graph_features, resolved),
        ]
        output = base
        for frame in frames:
            output = output.merge(frame, on="account_id", how="left")
        for column in RISK_COMPONENT_COLUMNS:
            if column not in output.columns:
                output[column] = 0.0 if column != "account_id" else output["account_id"]
        numeric_columns = [column for column in RISK_COMPONENT_COLUMNS if column != "account_id"]
        output[numeric_columns] = output[numeric_columns].fillna(0.0)
        output["component_coverage"] = output.loc[:, list(_MAJOR_COMPONENTS)].gt(0).sum(
            axis=1
        ) / len(_MAJOR_COMPONENTS)
        return (
            output.loc[:, RISK_COMPONENT_COLUMNS].sort_values("account_id").reset_index(drop=True)
        )
    except ScoringComputationError:
        raise
    except Exception as exc:
        raise ScoringComputationError(f"Failed to build account risk components: {exc}") from exc
