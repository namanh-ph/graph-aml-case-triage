"""Case-level risk component construction."""

from __future__ import annotations

import json
from collections.abc import Iterable

import pandas as pd

from graph_aml.cases.exceptions import CaseRiskComputationError
from graph_aml.cases.risk_config import CaseRiskScoringConfig

CASE_RISK_COMPONENT_COLUMNS = (
    "case_id",
    "alert_risk_score",
    "account_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "typology_diversity_score",
    "evidence_value_score",
    "max_alert_score",
    "mean_alert_score",
    "max_account_risk_score",
    "mean_account_risk_score",
    "max_graph_risk_score",
    "mean_graph_risk_score",
    "max_anomaly_score",
    "mean_anomaly_score",
    "typology_count",
    "alert_count",
    "related_account_count",
    "evidence_transaction_count",
    "total_transaction_value",
    "component_coverage",
)


def _empty_components() -> pd.DataFrame:
    return pd.DataFrame(columns=CASE_RISK_COMPONENT_COLUMNS)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def clip_case_score(value: object, lower: float = 0.0, upper: float = 100.0) -> float:
    try:
        number = pd.to_numeric(pd.Series([value]), errors="coerce").fillna(lower).iloc[0]
        return float(max(lower, min(upper, number)))
    except Exception as exc:
        raise CaseRiskComputationError(f"invalid score value: {value}") from exc


def percentile_rank_score(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0)
    if numeric.empty:
        return pd.Series(dtype=float)
    return numeric.rank(method="average", pct=True).fillna(0) * 100.0


def map_case_alert_severity_to_score(
    severity: object,
    config: CaseRiskScoringConfig | None = None,
) -> float:
    resolved = CaseRiskScoringConfig() if config is None else config
    key = "low" if _is_missing(severity) else str(severity).strip().lower()
    return clip_case_score(resolved.alert.severity_scores.get(key, 0.0))


def normalise_case_id_list(value: object) -> tuple[str, ...]:
    try:
        if _is_missing(value):
            return ()
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return ()
            if text.startswith("["):
                payload = json.loads(text)
                if not isinstance(payload, list):
                    raise CaseRiskComputationError("JSON ID payload must be a list")
                return tuple(sorted({str(item).strip() for item in payload if str(item).strip()}))
            if "," in text:
                return tuple(sorted({part.strip() for part in text.split(",") if part.strip()}))
            return (text,)
        if isinstance(value, dict):
            raise CaseRiskComputationError("ID lists cannot be mappings")
        if isinstance(value, Iterable):
            return tuple(sorted({str(item).strip() for item in value if str(item).strip()}))
        return (str(value),)
    except CaseRiskComputationError:
        raise
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to normalise ID list: {exc}") from exc


def _case_ids(cases: pd.DataFrame) -> pd.Series:
    if "case_id" not in cases.columns:
        raise CaseRiskComputationError("cases must include case_id")
    return cases["case_id"].astype(str)


def _case_account_ids(row: pd.Series) -> tuple[str, ...]:
    values = list(normalise_case_id_list(row.get("related_accounts")))
    primary = row.get("primary_account_id")
    if not _is_missing(primary) and str(primary).strip():
        values.append(str(primary).strip())
    return tuple(sorted(set(values)))


def _dedupe_latest_or_highest(frame: pd.DataFrame, score_col: str) -> pd.DataFrame:
    if frame.empty or "account_id" not in frame.columns:
        return pd.DataFrame(columns=frame.columns)
    output = frame.copy(deep=True)
    sort_cols = ["account_id"]
    ascending = [True]
    for column in ("scored_at", "computed_at", "updated_at"):
        if column in output.columns:
            sort_cols.append(column)
            ascending.append(False)
            break
    if score_col in output.columns:
        output["_score_sort"] = pd.to_numeric(output[score_col], errors="coerce").fillna(0)
        sort_cols.append("_score_sort")
        ascending.append(False)
    output = output.sort_values(sort_cols, ascending=ascending, kind="mergesort")
    output = output.drop_duplicates("account_id", keep="first")
    return output.drop(columns=["_score_sort"], errors="ignore")


def compute_case_alert_risk_component(
    cases: pd.DataFrame,
    case_alerts: pd.DataFrame,
    alerts: pd.DataFrame,
    config: CaseRiskScoringConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseRiskScoringConfig() if config is None else config
    try:
        rows: list[dict[str, object]] = []
        case_ids = _case_ids(cases)
        links = case_alerts.copy(deep=True)
        alert_frame = alerts.copy(deep=True)
        if not links.empty and {"case_id", "alert_id"}.difference(links.columns):
            raise CaseRiskComputationError("case_alerts must include case_id and alert_id")
        if not alert_frame.empty and "alert_id" not in alert_frame.columns:
            raise CaseRiskComputationError("alerts must include alert_id")
        joined = (
            links.merge(alert_frame, on="alert_id", how="left")
            if not links.empty and not alert_frame.empty
            else pd.DataFrame()
        )
        if not joined.empty:
            rule_scores = pd.to_numeric(joined.get("risk_score_rule"), errors="coerce")
            severity_scores = joined.get("severity", pd.Series(dtype=object)).apply(
                lambda value: map_case_alert_severity_to_score(value, resolved)
            )
            joined["_alert_score"] = rule_scores.fillna(severity_scores)
        for case_id in case_ids:
            subset = (
                joined[joined["case_id"].astype(str) == case_id] if not joined.empty else joined
            )
            if subset.empty:
                max_score = mean_score = alert_risk = 0.0
            else:
                scores = pd.to_numeric(subset["_alert_score"], errors="coerce").fillna(0)
                max_score = clip_case_score(scores.max())
                mean_score = clip_case_score(scores.mean())
                values: list[float] = []
                if resolved.alert.use_max_alert_score:
                    values.append(max_score * resolved.alert.max_alert_weight)
                if resolved.alert.use_mean_alert_score:
                    values.append(mean_score * resolved.alert.mean_alert_weight)
                alert_risk = clip_case_score(sum(values))
            rows.append(
                {
                    "case_id": case_id,
                    "alert_risk_score": alert_risk,
                    "max_alert_score": max_score,
                    "mean_alert_score": mean_score,
                    "alert_count": int(len(subset)),
                }
            )
        return pd.DataFrame(rows)
    except CaseRiskComputationError:
        raise
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to compute alert risk component: {exc}") from exc


def compute_case_account_risk_component(
    cases: pd.DataFrame,
    account_risk_scores: pd.DataFrame,
    config: CaseRiskScoringConfig | None = None,
) -> pd.DataFrame:
    try:
        scores = _dedupe_latest_or_highest(
            account_risk_scores.copy(deep=True), "account_risk_score"
        )
        rows = []
        for _, row in cases.copy(deep=True).iterrows():
            case_id = str(row["case_id"])
            account_ids = _case_account_ids(row)
            subset = (
                scores[scores["account_id"].astype(str).isin(account_ids)]
                if not scores.empty
                else scores
            )
            values = pd.to_numeric(subset.get("account_risk_score"), errors="coerce").fillna(0)
            max_score = clip_case_score(values.max()) if not values.empty else 0.0
            mean_score = clip_case_score(values.mean()) if not values.empty else 0.0
            rows.append(
                {
                    "case_id": case_id,
                    "account_risk_score": max_score,
                    "max_account_risk_score": max_score,
                    "mean_account_risk_score": mean_score,
                    "related_account_count": int(len(account_ids)),
                }
            )
        return pd.DataFrame(rows)
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to compute account risk component: {exc}") from exc


def _graph_account_scores(
    graph_features: pd.DataFrame, config: CaseRiskScoringConfig
) -> pd.DataFrame:
    if graph_features.empty:
        return pd.DataFrame(columns=("account_id", "_graph_score"))
    frame = _dedupe_latest_or_highest(graph_features.copy(deep=True), "pagerank_score")
    for column in (
        "pagerank_score",
        "degree_centrality",
        "cycle_count",
        "community_size",
        "high_risk_alert_count",
    ):
        if column not in frame.columns:
            frame[column] = 0
    frame["_pagerank_pct"] = percentile_rank_score(frame["pagerank_score"])
    frame["_degree_pct"] = percentile_rank_score(frame["degree_centrality"])
    frame["_cycle_pct"] = percentile_rank_score(frame["cycle_count"])
    frame["_community_pct"] = percentile_rank_score(frame["community_size"])
    frame["_alert_pct"] = percentile_rank_score(frame["high_risk_alert_count"])
    if "shortest_path_to_flagged" in frame.columns:
        path = pd.to_numeric(frame["shortest_path_to_flagged"], errors="coerce")
        frame["_proximity"] = path.apply(
            lambda value: 0.0 if pd.isna(value) else 100.0 / (1.0 + max(0.0, value - 1.0))
        )
    else:
        frame["_proximity"] = frame["_alert_pct"]
    graph = config.graph
    frame["_graph_score"] = (
        frame["_pagerank_pct"] * graph.pagerank_weight
        + frame["_degree_pct"] * graph.degree_weight
        + frame["_cycle_pct"] * graph.cycle_weight
        + frame["_community_pct"] * graph.community_size_weight
        + ((frame["_alert_pct"] + frame["_proximity"]) / 2.0) * graph.alert_proximity_weight
    ).clip(0, 100)
    return frame[["account_id", "_graph_score"]]


def compute_case_graph_risk_component(
    cases: pd.DataFrame,
    graph_features: pd.DataFrame,
    config: CaseRiskScoringConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseRiskScoringConfig() if config is None else config
    try:
        graph_scores = _graph_account_scores(graph_features, resolved)
        rows = []
        for _, row in cases.copy(deep=True).iterrows():
            case_id = str(row["case_id"])
            account_ids = _case_account_ids(row)
            subset = graph_scores[graph_scores["account_id"].astype(str).isin(account_ids)]
            values = pd.to_numeric(subset.get("_graph_score"), errors="coerce").fillna(0)
            max_score = clip_case_score(values.max()) if not values.empty else 0.0
            mean_score = clip_case_score(values.mean()) if not values.empty else 0.0
            rows.append(
                {
                    "case_id": case_id,
                    "graph_risk_score": max_score,
                    "max_graph_risk_score": max_score,
                    "mean_graph_risk_score": mean_score,
                }
            )
        return pd.DataFrame(rows)
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to compute graph risk component: {exc}") from exc


def compute_case_anomaly_risk_component(
    cases: pd.DataFrame,
    anomaly_scores: pd.DataFrame,
    config: CaseRiskScoringConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseRiskScoringConfig() if config is None else config
    try:
        scores = _dedupe_latest_or_highest(anomaly_scores.copy(deep=True), "anomaly_score")
        rows = []
        for _, row in cases.copy(deep=True).iterrows():
            account_ids = _case_account_ids(row)
            subset = (
                scores[scores["account_id"].astype(str).isin(account_ids)]
                if not scores.empty
                else scores
            )
            values = pd.to_numeric(subset.get("anomaly_score"), errors="coerce").fillna(0)
            max_score = clip_case_score(values.max()) if not values.empty else 0.0
            mean_score = clip_case_score(values.mean()) if not values.empty else 0.0
            weighted = 0.0
            if resolved.anomaly.use_max_anomaly_score:
                weighted += max_score * resolved.anomaly.max_anomaly_weight
            if resolved.anomaly.use_mean_anomaly_score:
                weighted += mean_score * resolved.anomaly.mean_anomaly_weight
            rows.append(
                {
                    "case_id": str(row["case_id"]),
                    "anomaly_risk_score": clip_case_score(weighted),
                    "max_anomaly_score": max_score,
                    "mean_anomaly_score": mean_score,
                }
            )
        return pd.DataFrame(rows)
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to compute anomaly risk component: {exc}") from exc


def compute_case_typology_diversity_component(
    cases: pd.DataFrame,
    alerts: pd.DataFrame | None = None,
    config: CaseRiskScoringConfig | None = None,
) -> pd.DataFrame:
    try:
        rows = []
        alert_frame = pd.DataFrame() if alerts is None else alerts.copy(deep=True)
        for _, row in cases.copy(deep=True).iterrows():
            typologies = set(normalise_case_id_list(row.get("typologies")))
            if not typologies and not alert_frame.empty and "alert_id" in alert_frame.columns:
                alert_ids = normalise_case_id_list(row.get("alert_ids"))
                subset = alert_frame[alert_frame["alert_id"].astype(str).isin(alert_ids)]
                if "typology" in subset.columns:
                    typologies.update(str(value) for value in subset["typology"].dropna().tolist())
            count = len({value for value in typologies if value})
            rows.append(
                {
                    "case_id": str(row["case_id"]),
                    "typology_diversity_score": clip_case_score(count * 25.0),
                    "typology_count": int(count),
                }
            )
        return pd.DataFrame(rows)
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to compute typology diversity: {exc}") from exc


def compute_case_evidence_value_component(
    cases: pd.DataFrame,
    transactions: pd.DataFrame,
    config: CaseRiskScoringConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseRiskScoringConfig() if config is None else config
    try:
        frame = cases.copy(deep=True)
        if "total_transaction_value" not in frame.columns:
            frame["total_transaction_value"] = 0.0
        if "evidence_transaction_count" not in frame.columns:
            frame["evidence_transaction_count"] = 0
        if "related_accounts" not in frame.columns:
            frame["related_accounts"] = [[] for _ in range(len(frame))]
        values = pd.to_numeric(frame["total_transaction_value"], errors="coerce").fillna(0)
        evidence_counts = pd.to_numeric(
            frame["evidence_transaction_count"], errors="coerce"
        ).fillna(0)
        related_counts = frame["related_accounts"].apply(
            lambda value: len(normalise_case_id_list(value))
        )
        value_pct = percentile_rank_score(values)
        evidence_pct = percentile_rank_score(evidence_counts)
        related_pct = percentile_rank_score(related_counts)
        evidence = resolved.evidence
        score = (
            value_pct * evidence.transaction_value_percentile_weight
            + evidence_pct * evidence.evidence_count_percentile_weight
            + related_pct * evidence.related_account_count_percentile_weight
        ).clip(0, 100)
        return pd.DataFrame(
            {
                "case_id": frame["case_id"].astype(str),
                "evidence_value_score": score,
                "evidence_transaction_count": evidence_counts.astype(int),
                "total_transaction_value": values.astype(float),
                "related_account_count": related_counts.astype(int),
            }
        )
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to compute evidence value: {exc}") from exc


def build_case_risk_components(
    cases: pd.DataFrame,
    case_alerts: pd.DataFrame,
    alerts: pd.DataFrame,
    account_risk_scores: pd.DataFrame,
    graph_features: pd.DataFrame,
    anomaly_scores: pd.DataFrame,
    transactions: pd.DataFrame,
    config: CaseRiskScoringConfig | None = None,
) -> pd.DataFrame:
    """Build all case-level risk components."""

    resolved = CaseRiskScoringConfig() if config is None else config
    if cases.empty:
        return _empty_components()
    try:
        base = pd.DataFrame({"case_id": _case_ids(cases)})
        frames = [
            compute_case_alert_risk_component(cases, case_alerts, alerts, resolved),
            compute_case_account_risk_component(cases, account_risk_scores, resolved),
            compute_case_graph_risk_component(cases, graph_features, resolved),
            compute_case_anomaly_risk_component(cases, anomaly_scores, resolved),
            compute_case_typology_diversity_component(cases, alerts, resolved),
            compute_case_evidence_value_component(cases, transactions, resolved),
        ]
        merged = base
        for frame in frames:
            merged = merged.merge(frame, on="case_id", how="left")
        for column in CASE_RISK_COMPONENT_COLUMNS:
            if column not in merged.columns:
                merged[column] = 0
        major = (
            "alert_risk_score",
            "account_risk_score",
            "graph_risk_score",
            "anomaly_risk_score",
            "typology_diversity_score",
            "evidence_value_score",
        )
        for column in CASE_RISK_COMPONENT_COLUMNS:
            if column != "case_id":
                merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0)
        merged["component_coverage"] = merged.loc[:, major].gt(0).sum(axis=1).astype(float) / float(
            len(major)
        )
        return (
            merged.loc[:, CASE_RISK_COMPONENT_COLUMNS]
            .sort_values("case_id", kind="mergesort")
            .reset_index(drop=True)
        )
    except CaseRiskComputationError:
        raise
    except Exception as exc:
        raise CaseRiskComputationError(f"failed to build case risk components: {exc}") from exc
