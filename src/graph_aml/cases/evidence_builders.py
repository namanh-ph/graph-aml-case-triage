"""Builders for deterministic AML case evidence packs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from sqlalchemy import Engine

from graph_aml.cases.evidence_config import CaseEvidenceConfig
from graph_aml.cases.exceptions import CaseEvidenceBuildError

if TYPE_CHECKING:
    from graph_aml.cases.evidence_persistence import (
        CaseEvidencePersistenceConfig,
        CaseEvidencePersistenceResult,
    )

CASE_EVIDENCE_PACK_COLUMNS = (
    "case_id",
    "evidence_version",
    "case_summary",
    "typology_evidence",
    "alert_evidence",
    "transaction_evidence",
    "account_evidence",
    "graph_evidence",
    "risk_driver_evidence",
    "chronology",
    "recommended_review_focus",
    "evidence_quality",
    "created_at",
)

CASE_EXPLANATION_COLUMNS = (
    "case_id",
    "explanation_version",
    "explanation_text",
    "explanation_bullets",
    "risk_driver_summary",
    "typology_summary",
    "transaction_summary",
    "graph_summary",
    "created_at",
)

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


@dataclass(frozen=True)
class CaseEvidenceBuildResult:
    evidence_packs: pd.DataFrame
    explanations: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(cast(Any, value))
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, bool) else False


def _json_safe(value: object) -> object:
    if _is_missing(value):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return cast(Any, value).item()
        except (AttributeError, ValueError):
            return str(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(cast(Any, value))
    except (TypeError, ValueError):
        return default


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(cast(Any, value))
    except (TypeError, ValueError):
        return default


def _object_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list | tuple) else []


def _object_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def normalise_json_payload(value: object) -> object:
    """Return a deterministic JSON-serialisable payload."""

    return _json_safe(value)


def normalise_evidence_list(value: object) -> tuple[str, ...]:
    """Convert common evidence-list encodings into a deterministic tuple."""

    if _is_missing(value):
        return ()
    raw: object = value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ()
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError:
            raw = stripped.strip("{}")
    if isinstance(raw, list | tuple | set):
        items = raw
    elif isinstance(raw, str) and "," in raw:
        items = [part.strip() for part in raw.split(",")]
    else:
        items = [raw]
    clean = [str(item).strip().strip('"').strip("'") for item in items if not _is_missing(item)]
    return tuple(sorted(dict.fromkeys(item for item in clean if item)))


def records_from_frame(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Convert a DataFrame into deterministic serialisable row dictionaries."""

    if frame.empty:
        return []
    return [
        {str(column): _json_safe(value) for column, value in row.items()}
        for row in frame.astype(object).to_dict(orient="records")
    ]


def _case_dict(case_row: pd.Series | dict[str, object]) -> dict[str, object]:
    if isinstance(case_row, pd.Series):
        return {str(key): value for key, value in case_row.to_dict().items()}
    if isinstance(case_row, dict):
        return dict(case_row)
    raise CaseEvidenceBuildError("case_row must be a Series or dictionary")


def _case_id(case_row: pd.Series | dict[str, object]) -> str:
    value = _case_dict(case_row).get("case_id")
    if _is_missing(value) or not str(value).strip():
        raise CaseEvidenceBuildError("case_id is required")
    return str(value)


def _case_alert_ids(case: dict[str, object]) -> tuple[str, ...]:
    return normalise_evidence_list(case.get("alert_ids"))


def _case_accounts(case: dict[str, object]) -> tuple[str, ...]:
    accounts = list(normalise_evidence_list(case.get("related_accounts")))
    primary = case.get("primary_account_id")
    if not _is_missing(primary):
        accounts.append(str(primary))
    return tuple(sorted(dict.fromkeys(account for account in accounts if account)))


def _filter_alerts_for_case(case: dict[str, object], alerts: pd.DataFrame) -> pd.DataFrame:
    if alerts.empty:
        return alerts.copy()
    alert_ids = _case_alert_ids(case)
    case_id = str(case.get("case_id", ""))
    mask = pd.Series(False, index=alerts.index)
    if alert_ids and "alert_id" in alerts.columns:
        mask = mask | alerts["alert_id"].astype(str).isin(alert_ids)
    if "case_id" in alerts.columns:
        mask = mask | (alerts["case_id"].astype(str) == case_id)
    return alerts.loc[mask].copy()


def _sort_alerts(alerts: pd.DataFrame) -> pd.DataFrame:
    if alerts.empty:
        return alerts.copy()
    frame = alerts.copy()
    frame["_severity_rank"] = (
        frame.get("severity", "").astype(str).str.lower().map(_SEVERITY_RANK).fillna(0)
    )
    frame["_risk_score"] = pd.to_numeric(frame.get("risk_score_rule", 0), errors="coerce").fillna(0)
    frame["_created"] = pd.to_datetime(frame.get("created_at", pd.NaT), errors="coerce")
    return frame.sort_values(
        ["_severity_rank", "_risk_score", "_created", "alert_id"],
        ascending=[False, False, False, True],
    ).drop(columns=["_severity_rank", "_risk_score", "_created"], errors="ignore")


def build_evidence_quality_summary(
    case_id: str,
    alerts: pd.DataFrame,
    transactions: pd.DataFrame,
    account_rows: pd.DataFrame,
    graph_rows: pd.DataFrame,
    risk_rows: pd.DataFrame,
) -> dict[str, object]:
    """Build evidence presence and count summary for one case."""

    return {
        "case_id": str(case_id),
        "has_alerts": bool(len(alerts)),
        "has_transactions": bool(len(transactions)),
        "has_account_context": bool(len(account_rows)),
        "has_graph_context": bool(len(graph_rows)),
        "has_risk_scores": bool(len(risk_rows)),
        "alert_count": int(len(alerts)),
        "transaction_count": int(len(transactions)),
        "account_context_count": int(len(account_rows)),
        "graph_context_count": int(len(graph_rows)),
        "risk_score_count": int(len(risk_rows)),
    }


def build_typology_evidence(
    case_row: pd.Series | dict[str, object],
    alerts: pd.DataFrame,
    config: CaseEvidenceConfig | None = None,
) -> dict[str, object]:
    resolved = CaseEvidenceConfig() if config is None else config
    case = _case_dict(case_row)
    case_alerts = _sort_alerts(_filter_alerts_for_case(case, alerts)).head(
        resolved.limits.max_alerts_per_case
    )
    typologies = set(normalise_evidence_list(case.get("typologies")))
    rule_names = set(normalise_evidence_list(case.get("rule_names")))
    reason_codes: set[str] = set()
    if not case_alerts.empty:
        if "typology" in case_alerts:
            typologies.update(case_alerts["typology"].dropna().astype(str).tolist())
        if "rule_name" in case_alerts:
            rule_names.update(case_alerts["rule_name"].dropna().astype(str).tolist())
        if "reason_code" in case_alerts:
            reason_codes.update(case_alerts["reason_code"].dropna().astype(str).tolist())
    severity_counts = (
        case_alerts["severity"].astype(str).str.lower().value_counts().sort_index().to_dict()
        if "severity" in case_alerts
        else {}
    )
    risk_scores = (
        pd.to_numeric(case_alerts.get("risk_score_rule", pd.Series(dtype=float)), errors="coerce")
        .dropna()
        .tolist()
    )
    return {
        "typologies": sorted(typologies),
        "rule_names": sorted(rule_names),
        "reason_codes": sorted(reason_codes)[: resolved.limits.max_reason_codes],
        "severity_counts": {str(key): int(value) for key, value in severity_counts.items()},
        "max_rule_risk_score": float(max(risk_scores)) if risk_scores else 0.0,
        "mean_rule_risk_score": float(sum(risk_scores) / len(risk_scores)) if risk_scores else 0.0,
    }


def build_alert_evidence(
    case_row: pd.Series | dict[str, object],
    alerts: pd.DataFrame,
    config: CaseEvidenceConfig | None = None,
) -> dict[str, object]:
    resolved = CaseEvidenceConfig() if config is None else config
    case = _case_dict(case_row)
    case_alerts = _sort_alerts(_filter_alerts_for_case(case, alerts)).head(
        resolved.limits.max_alerts_per_case
    )
    selected_columns = [
        column
        for column in (
            "alert_id",
            "rule_name",
            "typology",
            "severity",
            "risk_score_rule",
            "reason_code",
            "detection_window_start",
            "detection_window_end",
            "evidence_ids",
        )
        if column in case_alerts.columns
    ]
    return {
        "alert_count": int(len(case_alerts)),
        "alerts": records_from_frame(case_alerts.loc[:, selected_columns])
        if selected_columns
        else [],
    }


def _transaction_ids_for_case(case: dict[str, object], alerts: pd.DataFrame) -> tuple[str, ...]:
    ids: set[str] = set()
    case_alerts = _filter_alerts_for_case(case, alerts)
    if "evidence_ids" in case_alerts:
        for value in case_alerts["evidence_ids"].tolist():
            ids.update(normalise_evidence_list(value))
    return tuple(sorted(ids))


def build_transaction_evidence(
    case_row: pd.Series | dict[str, object],
    alerts: pd.DataFrame,
    transactions: pd.DataFrame,
    config: CaseEvidenceConfig | None = None,
) -> dict[str, object]:
    resolved = CaseEvidenceConfig() if config is None else config
    case = _case_dict(case_row)
    ids = _transaction_ids_for_case(case, alerts)
    if transactions.empty or not ids or "transaction_id" not in transactions.columns:
        rows = transactions.iloc[0:0].copy()
    else:
        rows = transactions.loc[transactions["transaction_id"].astype(str).isin(ids)].copy()
    if not rows.empty:
        rows["_primary"] = pd.to_datetime(
            rows.get(resolved.transaction_sorting.primary, pd.NaT), errors="coerce"
        )
        rows["_secondary"] = pd.to_numeric(
            rows.get(resolved.transaction_sorting.secondary, 0), errors="coerce"
        ).fillna(0)
        rows = rows.sort_values(
            ["_primary", "_secondary", "transaction_id"],
            ascending=[True, not resolved.transaction_sorting.descending_amount, True],
        ).head(resolved.limits.max_transactions_per_case)
        rows = rows.drop(columns=["_primary", "_secondary"], errors="ignore")
    amount = pd.to_numeric(rows.get("amount", pd.Series(dtype=float)), errors="coerce").fillna(0)
    account_values: set[str] = set()
    for column in ("sender_account_id", "receiver_account_id"):
        if column in rows:
            account_values.update(rows[column].dropna().astype(str).tolist())
    date_values = pd.to_datetime(
        rows.get("transaction_timestamp", pd.Series(dtype=object)), errors="coerce"
    ).dropna()
    return {
        "transaction_count": int(len(rows)),
        "total_value": float(amount.sum()),
        "max_value": float(amount.max()) if len(amount) else 0.0,
        "involved_account_count": len(account_values),
        "counterparty_count": int(rows["counterparty_id"].nunique(dropna=True))
        if "counterparty_id" in rows
        else 0,
        "country_count": int(rows["country_code"].nunique(dropna=True))
        if "country_code" in rows
        else 0,
        "date_range": {
            "min": date_values.min().isoformat() if len(date_values) else None,
            "max": date_values.max().isoformat() if len(date_values) else None,
        },
        "transactions": records_from_frame(
            rows.loc[
                :,
                [
                    column
                    for column in (
                        "transaction_id",
                        "transaction_timestamp",
                        "sender_account_id",
                        "receiver_account_id",
                        "counterparty_id",
                        "amount",
                        "currency",
                        "transaction_type",
                        "channel",
                        "country_code",
                    )
                    if column in rows.columns
                ],
            ]
        ),
    }


def _latest_by_score(frame: pd.DataFrame, key: str, score_col: str) -> pd.DataFrame:
    if frame.empty or key not in frame.columns:
        return frame.iloc[0:0].copy()
    rows = frame.copy()
    rows["_score"] = pd.to_numeric(rows.get(score_col, 0), errors="coerce").fillna(0)
    rows["_time"] = pd.to_datetime(rows.get("scored_at", pd.NaT), errors="coerce")
    return rows.sort_values(
        [key, "_time", "_score"], ascending=[True, False, False]
    ).drop_duplicates(key, keep="first")


def build_account_evidence(
    case_row: pd.Series | dict[str, object],
    account_risk_scores: pd.DataFrame,
    anomaly_scores: pd.DataFrame,
    config: CaseEvidenceConfig | None = None,
) -> dict[str, object]:
    resolved = CaseEvidenceConfig() if config is None else config
    accounts = _case_accounts(_case_dict(case_row))[: resolved.limits.max_related_accounts]
    risk_rows = _latest_by_score(account_risk_scores, "account_id", "account_risk_score")
    anomaly_rows = _latest_by_score(anomaly_scores, "account_id", "anomaly_score")
    if accounts:
        risk_rows = risk_rows.loc[
            risk_rows.get("account_id", pd.Series(dtype=str)).astype(str).isin(accounts)
        ]
        anomaly_rows = anomaly_rows.loc[
            anomaly_rows.get("account_id", pd.Series(dtype=str)).astype(str).isin(accounts)
        ]
    risk_map = {
        str(row["account_id"]): row
        for row in risk_rows.astype(object).to_dict(orient="records")
        if "account_id" in row
    }
    anomaly_map = {
        str(row["account_id"]): row
        for row in anomaly_rows.astype(object).to_dict(orient="records")
        if "account_id" in row
    }
    records: list[dict[str, object]] = []
    for account_id in accounts:
        risk = risk_map.get(account_id, {})
        anomaly = anomaly_map.get(account_id, {})
        records.append(
            {
                "account_id": account_id,
                "account_risk_score": _json_safe(risk.get("account_risk_score")),
                "account_risk_band": _json_safe(risk.get("risk_band")),
                "account_risk_rank": _json_safe(risk.get("risk_rank")),
                "anomaly_score": _json_safe(anomaly.get("anomaly_score")),
                "anomaly_risk_band": _json_safe(anomaly.get("risk_band")),
                "anomaly_rank": _json_safe(anomaly.get("anomaly_rank")),
            }
        )
    records = sorted(
        records,
        key=lambda row: (_to_float(row.get("account_risk_score")), str(row["account_id"])),
        reverse=True,
    )
    return {
        "primary_account_id": str(_case_dict(case_row).get("primary_account_id", "")),
        "accounts": records,
    }


def build_graph_evidence(
    case_row: pd.Series | dict[str, object],
    graph_features: pd.DataFrame,
    config: CaseEvidenceConfig | None = None,
) -> dict[str, object]:
    resolved = CaseEvidenceConfig() if config is None else config
    accounts = _case_accounts(_case_dict(case_row))[: resolved.limits.max_related_accounts]
    rows = graph_features.copy()
    if accounts and not rows.empty and "account_id" in rows:
        rows = rows.loc[rows["account_id"].astype(str).isin(accounts)]
    selected = [
        column
        for column in (
            "account_id",
            "pagerank_score",
            "degree_centrality",
            "betweenness_centrality",
            "community_id",
            "community_size",
            "cycle_count",
            "high_risk_alert_count",
            "shortest_path_to_flagged",
            "fan_in_count",
            "fan_out_count",
            "neighbour_account_count",
        )
        if column in rows.columns
    ]
    if selected:
        rows = rows.sort_values(["account_id"]).loc[:, selected]
    return {"account_count": int(len(rows)), "accounts": records_from_frame(rows)}


def build_risk_driver_evidence(
    case_row: pd.Series | dict[str, object],
    case_risk_scores: pd.DataFrame,
    account_risk_scores: pd.DataFrame,
    graph_features: pd.DataFrame,
    anomaly_scores: pd.DataFrame,
    alerts: pd.DataFrame,
    transactions: pd.DataFrame,
    config: CaseEvidenceConfig | None = None,
) -> dict[str, object]:
    resolved = CaseEvidenceConfig() if config is None else config
    case = _case_dict(case_row)
    case_id = str(case.get("case_id", ""))
    drivers: list[dict[str, object]] = []
    risk_rows = case_risk_scores.loc[
        case_risk_scores.get("case_id", pd.Series(dtype=str)).astype(str) == case_id
    ].copy()
    component_cols = [
        "alert_risk_score",
        "account_risk_score",
        "graph_risk_score",
        "anomaly_risk_score",
        "typology_diversity_score",
        "evidence_value_score",
    ]
    if not risk_rows.empty:
        row = risk_rows.sort_values("case_risk_score", ascending=False).iloc[0]
        for column in component_cols:
            score = float(
                pd.to_numeric(pd.Series([row.get(column, 0)]), errors="coerce").fillna(0).iloc[0]
            )
            if score >= resolved.risk_driver_thresholds.high_component_score:
                band = (
                    "critical"
                    if score >= resolved.risk_driver_thresholds.critical_component_score
                    else "high"
                )
                drivers.append(
                    {
                        "component": column,
                        "score": score,
                        "band": band,
                        "label": column.replace("_", " "),
                    }
                )
    typology_evidence = build_typology_evidence(case, alerts, resolved)
    transaction_evidence = build_transaction_evidence(case, alerts, transactions, resolved)
    graph_evidence = build_graph_evidence(case, graph_features, resolved)
    account_evidence = build_account_evidence(case, account_risk_scores, anomaly_scores, resolved)
    severity_counts = _object_dict(typology_evidence.get("severity_counts"))
    if _to_int(severity_counts.get("high")) or _to_int(severity_counts.get("critical")):
        drivers.append(
            {
                "component": "alert_severity",
                "score": 75.0,
                "band": "high",
                "label": "high severity alerts",
            }
        )
    if (
        _to_int(transaction_evidence.get("transaction_count"))
        >= resolved.risk_driver_thresholds.high_alert_count
    ):
        drivers.append(
            {
                "component": "evidence_count",
                "score": 75.0,
                "band": "high",
                "label": "dense transaction evidence",
            }
        )
    for row in _object_list(graph_evidence.get("accounts")):
        if isinstance(row, dict) and _to_float(row.get("cycle_count")) > 0:
            drivers.append(
                {
                    "component": "graph_cycles",
                    "score": 75.0,
                    "band": "high",
                    "label": "cycle activity",
                }
            )
            break
    for row in _object_list(account_evidence.get("accounts")):
        if isinstance(row, dict) and _to_float(row.get("anomaly_score")) >= 75:
            drivers.append(
                {
                    "component": "anomaly_score",
                    "score": _to_float(row.get("anomaly_score")),
                    "band": "high",
                    "label": "high anomaly account",
                }
            )
            break
    drivers = sorted(
        drivers, key=lambda item: (-_to_float(item.get("score")), str(item.get("component", "")))
    )
    return {"risk_drivers": drivers, "driver_count": len(drivers)}


def build_case_chronology(
    case_row: pd.Series | dict[str, object],
    alerts: pd.DataFrame,
    transactions: pd.DataFrame,
    config: CaseEvidenceConfig | None = None,
) -> list[dict[str, object]]:
    case = _case_dict(case_row)
    case_alerts = _filter_alerts_for_case(case, alerts)
    tx_ids = _transaction_ids_for_case(case, alerts)
    tx_rows = (
        transactions.loc[transactions["transaction_id"].astype(str).isin(tx_ids)].copy()
        if not transactions.empty and "transaction_id" in transactions
        else transactions.iloc[0:0].copy()
    )
    events: list[dict[str, object]] = []
    for row in tx_rows.astype(object).to_dict(orient="records"):
        events.append(
            {
                "event_type": "transaction",
                "event_id": str(row.get("transaction_id", "")),
                "timestamp": _json_safe(row.get("transaction_timestamp")),
                "amount": _json_safe(row.get("amount")),
            }
        )
    for row in case_alerts.astype(object).to_dict(orient="records"):
        events.append(
            {
                "event_type": "alert",
                "event_id": str(row.get("alert_id", "")),
                "timestamp": _json_safe(row.get("created_at") or row.get("detection_window_end")),
                "severity": _json_safe(row.get("severity")),
            }
        )
    return sorted(
        events, key=lambda item: (str(item.get("timestamp") or ""), str(item.get("event_id") or ""))
    )


def build_recommended_review_focus(
    typology_evidence: dict[str, object],
    alert_evidence: dict[str, object],
    transaction_evidence: dict[str, object],
    account_evidence: dict[str, object],
    graph_evidence: dict[str, object],
    risk_driver_evidence: dict[str, object],
    config: CaseEvidenceConfig | None = None,
) -> list[str]:
    resolved = CaseEvidenceConfig() if config is None else config
    bullets: list[str] = []
    typologies = {str(value).lower() for value in _object_list(typology_evidence.get("typologies"))}
    if "circular_flow" in typologies:
        bullets.append("Review circular flow transaction chain.")
    if _to_float(transaction_evidence.get("max_value")) > 0:
        bullets.append("Verify legitimacy of high-value counterparties.")
    if graph_evidence.get("accounts"):
        bullets.append("Inspect graph community and proximity to flagged activity.")
    if account_evidence.get("accounts"):
        bullets.append("Compare account activity against customer profile and account risk score.")
    if any(
        isinstance(driver, dict) and driver.get("component") == "anomaly_score"
        for driver in _object_list(risk_driver_evidence.get("risk_drivers"))
    ):
        bullets.append("Review high anomaly accounts and behavioural deviation.")
    if _to_int(alert_evidence.get("alert_count")) > 1:
        bullets.append("Review repeated alerts and shared reason codes.")
    return list(dict.fromkeys(bullets))[: resolved.limits.max_explanation_bullets]


def _case_summary(
    case: dict[str, object],
    case_risk_scores: pd.DataFrame,
    transaction_evidence: dict[str, object],
) -> dict[str, object]:
    case_id = str(case.get("case_id", ""))
    risk_rows = case_risk_scores.loc[
        case_risk_scores.get("case_id", pd.Series(dtype=str)).astype(str) == case_id
    ].copy()
    risk_band = None
    case_risk_score = None
    if not risk_rows.empty:
        row = risk_rows.sort_values("case_risk_score", ascending=False).iloc[0]
        risk_band = row.get("risk_band")
        case_risk_score = row.get("case_risk_score")
    return {
        "case_id": case_id,
        "severity": _json_safe(case.get("severity")),
        "status": _json_safe(case.get("status")),
        "risk_band": _json_safe(risk_band or case.get("case_risk_band")),
        "case_risk_score": _json_safe(case_risk_score or case.get("case_risk_score")),
        "alert_count": _to_int(case.get("alert_count")),
        "evidence_transaction_count": _to_int(transaction_evidence.get("transaction_count")),
        "total_transaction_value": _to_float(transaction_evidence.get("total_value")),
        "primary_account_id": _json_safe(case.get("primary_account_id")),
        "primary_customer_id": _json_safe(case.get("primary_customer_id")),
    }


def build_case_evidence_pack_for_case(
    case_row: pd.Series | dict[str, object],
    inputs: dict[str, pd.DataFrame],
    config: CaseEvidenceConfig | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Build one evidence pack and one explanation row."""

    from graph_aml.cases.explanations import (
        render_case_explanation_bullets,
        render_case_explanation_text,
        render_graph_summary,
        render_risk_driver_summary,
        render_transaction_summary,
        render_typology_summary,
    )

    resolved = CaseEvidenceConfig() if config is None else config
    case = _case_dict(case_row)
    case_id = _case_id(case)
    alerts = inputs.get("alerts", pd.DataFrame())
    case_alerts = _filter_alerts_for_case(case, alerts)
    typology = (
        build_typology_evidence(case, alerts, resolved) if resolved.include.typology_context else {}
    )
    alert = build_alert_evidence(case, alerts, resolved) if resolved.include.alerts else {}
    transaction = (
        build_transaction_evidence(
            case, alerts, inputs.get("transactions", pd.DataFrame()), resolved
        )
        if resolved.include.transactions
        else {}
    )
    account = (
        build_account_evidence(
            case,
            inputs.get("account_risk_scores", pd.DataFrame()),
            inputs.get("anomaly_scores", pd.DataFrame()),
            resolved,
        )
        if resolved.include.account_context
        else {}
    )
    graph = (
        build_graph_evidence(case, inputs.get("graph_features", pd.DataFrame()), resolved)
        if resolved.include.graph_context
        else {}
    )
    risk = (
        build_risk_driver_evidence(
            case,
            inputs.get("case_risk_scores", pd.DataFrame()),
            inputs.get("account_risk_scores", pd.DataFrame()),
            inputs.get("graph_features", pd.DataFrame()),
            inputs.get("anomaly_scores", pd.DataFrame()),
            alerts,
            inputs.get("transactions", pd.DataFrame()),
            resolved,
        )
        if resolved.include.risk_drivers
        else {}
    )
    chronology = (
        build_case_chronology(case, alerts, inputs.get("transactions", pd.DataFrame()), resolved)
        if resolved.include.chronology
        else []
    )
    focus = build_recommended_review_focus(
        typology, alert, transaction, account, graph, risk, resolved
    )
    case_summary = _case_summary(case, inputs.get("case_risk_scores", pd.DataFrame()), transaction)
    quality = build_evidence_quality_summary(
        case_id,
        case_alerts,
        pd.DataFrame(transaction.get("transactions", [])),
        pd.DataFrame(account.get("accounts", [])),
        pd.DataFrame(graph.get("accounts", [])),
        inputs.get("case_risk_scores", pd.DataFrame()).loc[
            inputs.get("case_risk_scores", pd.DataFrame())
            .get("case_id", pd.Series(dtype=str))
            .astype(str)
            == case_id
        ],
    )
    created_at = _utc_now()
    pack = {
        "case_id": case_id,
        "evidence_version": resolved.evidence_version,
        "case_summary": case_summary,
        "typology_evidence": typology,
        "alert_evidence": alert,
        "transaction_evidence": transaction,
        "account_evidence": account,
        "graph_evidence": graph,
        "risk_driver_evidence": risk,
        "chronology": chronology,
        "recommended_review_focus": focus,
        "evidence_quality": quality,
        "created_at": created_at,
    }
    explanation = {
        "case_id": case_id,
        "explanation_version": resolved.explanation_version,
        "explanation_text": render_case_explanation_text(pack, resolved),
        "explanation_bullets": render_case_explanation_bullets(pack, resolved),
        "risk_driver_summary": render_risk_driver_summary(risk),
        "typology_summary": render_typology_summary(typology),
        "transaction_summary": render_transaction_summary(transaction),
        "graph_summary": render_graph_summary(graph),
        "created_at": created_at,
    }
    return pack, explanation


def build_case_evidence_packs(
    inputs: dict[str, pd.DataFrame],
    config: CaseEvidenceConfig | None = None,
) -> CaseEvidenceBuildResult:
    """Build evidence packs and deterministic explanations for all cases."""

    resolved = CaseEvidenceConfig() if config is None else config
    try:
        cases = inputs.get("cases", pd.DataFrame()).copy(deep=True)
        if cases.empty:
            evidence = pd.DataFrame(columns=CASE_EVIDENCE_PACK_COLUMNS)
            explanations = pd.DataFrame(columns=CASE_EXPLANATION_COLUMNS)
        else:
            if "case_id" not in cases.columns:
                raise CaseEvidenceBuildError("cases input must include case_id")
            case_risk = inputs.get("case_risk_scores", pd.DataFrame())
            if not case_risk.empty and "case_id" in case_risk and "case_risk_score" in case_risk:
                rank = case_risk.sort_values("case_risk_score", ascending=False).drop_duplicates(
                    "case_id"
                )
                cases = cases.merge(
                    rank[["case_id", "case_risk_score"]],
                    how="left",
                    on="case_id",
                    suffixes=("", "_risk"),
                )
                cases["_risk_sort"] = pd.to_numeric(
                    cases["case_risk_score"], errors="coerce"
                ).fillna(0)
            else:
                priority_series = cases.get("priority_score", pd.Series(0, index=cases.index))
                cases["_risk_sort"] = pd.to_numeric(priority_series, errors="coerce").fillna(0)
            cases = cases.sort_values(["_risk_sort", "case_id"], ascending=[False, True])
            packs: list[dict[str, object]] = []
            explanation_rows: list[dict[str, object]] = []
            for _, row in cases.drop(columns=["_risk_sort"], errors="ignore").iterrows():
                pack, explanation = build_case_evidence_pack_for_case(row, inputs, resolved)
                packs.append(pack)
                explanation_rows.append(explanation)
            evidence = pd.DataFrame(packs, columns=CASE_EVIDENCE_PACK_COLUMNS)
            explanations = pd.DataFrame(explanation_rows, columns=CASE_EXPLANATION_COLUMNS)
        summary: dict[str, object] = {
            "case_count": int(len(cases)),
            "evidence_pack_count": int(len(evidence)),
            "explanation_count": int(len(explanations)),
            "average_alert_count": float(
                evidence["evidence_quality"].apply(lambda item: item.get("alert_count", 0)).mean()
            )
            if not evidence.empty
            else 0.0,
            "average_evidence_transaction_count": float(
                evidence["evidence_quality"]
                .apply(lambda item: item.get("transaction_count", 0))
                .mean()
            )
            if not evidence.empty
            else 0.0,
            "cases_missing_alerts": int(
                evidence["evidence_quality"]
                .apply(lambda item: not item.get("has_alerts", False))
                .sum()
            )
            if not evidence.empty
            else 0,
            "cases_missing_transactions": int(
                evidence["evidence_quality"]
                .apply(lambda item: not item.get("has_transactions", False))
                .sum()
            )
            if not evidence.empty
            else 0,
            "cases_missing_risk_scores": int(
                evidence["evidence_quality"]
                .apply(lambda item: not item.get("has_risk_scores", False))
                .sum()
            )
            if not evidence.empty
            else 0,
        }
        metadata: dict[str, object] = {
            "evidence_version": resolved.evidence_version,
            "explanation_version": resolved.explanation_version,
            "include": dict(resolved.include.__dict__),
            "generated_at": _utc_now().isoformat(),
        }
        return CaseEvidenceBuildResult(evidence, explanations, summary, metadata)
    except CaseEvidenceBuildError:
        raise
    except Exception as exc:
        raise CaseEvidenceBuildError(f"Failed to build case evidence packs: {exc}") from exc


def build_and_persist_case_evidence(
    engine: Engine,
    evidence_config: CaseEvidenceConfig | None = None,
    persistence_config: CaseEvidencePersistenceConfig | None = None,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> tuple[CaseEvidenceBuildResult, CaseEvidencePersistenceResult]:
    """Read, build, and persist case evidence packs."""

    try:
        from graph_aml.cases.evidence_inputs import read_case_evidence_inputs
        from graph_aml.cases.evidence_persistence import (
            CaseEvidencePersistenceConfig,
            persist_case_evidence,
        )

        resolved = CaseEvidenceConfig() if evidence_config is None else evidence_config
        inputs = read_case_evidence_inputs(engine, resolved, case_ids=case_ids, limit=limit)
        build_result = build_case_evidence_packs(inputs, resolved)
        persistence = (
            CaseEvidencePersistenceConfig(
                evidence_version=resolved.evidence_version,
                explanation_version=resolved.explanation_version,
            )
            if persistence_config is None
            else persistence_config
        )
        persistence_result = persist_case_evidence(
            engine,
            build_result,
            cast(CaseEvidencePersistenceConfig, persistence),
            extra_metadata=extra_metadata,
        )
        return build_result, persistence_result
    except CaseEvidenceBuildError:
        raise
    except Exception as exc:
        raise CaseEvidenceBuildError(f"Failed to build and persist case evidence: {exc}") from exc
