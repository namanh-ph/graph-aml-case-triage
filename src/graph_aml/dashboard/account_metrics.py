"""Metric helpers for account profile dashboard views."""

from __future__ import annotations

import pandas as pd

from graph_aml.dashboard.exceptions import DashboardDataError


def _amount(frame: pd.DataFrame, mask: pd.Series) -> float:
    if "amount" not in frame:
        return 0.0
    return float(pd.to_numeric(frame.loc[mask, "amount"], errors="coerce").fillna(0).sum())


def build_account_transaction_summary(transactions: pd.DataFrame) -> dict[str, object]:
    if not isinstance(transactions, pd.DataFrame):
        raise DashboardDataError("transactions must be a DataFrame")
    if transactions.empty:
        return {
            "transaction_count": 0,
            "total_sent": 0.0,
            "total_received": 0.0,
            "net_flow": 0.0,
            "unique_counterparties": 0,
        }
    account_id = None
    if "sender_account_id" in transactions and not transactions["sender_account_id"].dropna().empty:
        account_id = str(transactions["sender_account_id"].dropna().iloc[0])
    sent_mask = (
        transactions.get("sender_account_id", pd.Series(index=transactions.index)) == account_id
    )
    received_mask = (
        transactions.get("receiver_account_id", pd.Series(index=transactions.index)) == account_id
    )
    total_sent = _amount(transactions, sent_mask)
    total_received = _amount(transactions, received_mask)
    counterparties = pd.concat(
        [
            transactions.get("sender_account_id", pd.Series(dtype="object")),
            transactions.get("receiver_account_id", pd.Series(dtype="object")),
            transactions.get("counterparty_id", pd.Series(dtype="object")),
        ],
        ignore_index=True,
    ).dropna()
    return {
        "transaction_count": int(len(transactions)),
        "total_sent": total_sent,
        "total_received": total_received,
        "net_flow": total_received - total_sent,
        "unique_counterparties": int(counterparties.astype(str).nunique()),
    }


def build_account_alert_summary(alerts: pd.DataFrame) -> dict[str, object]:
    if not isinstance(alerts, pd.DataFrame):
        raise DashboardDataError("alerts must be a DataFrame")
    severities = alerts.get("severity", pd.Series(dtype="object")).astype(str).str.lower()
    return {
        "alert_count": int(len(alerts)),
        "high_risk_alert_count": int(severities.isin(["high", "critical"]).sum()),
    }


def build_account_case_summary(cases: pd.DataFrame) -> dict[str, object]:
    if not isinstance(cases, pd.DataFrame):
        raise DashboardDataError("cases must be a DataFrame")
    scores = pd.to_numeric(
        cases.get("case_risk_score", pd.Series(dtype="float64")), errors="coerce"
    )
    return {
        "linked_case_count": int(len(cases)),
        "max_case_risk_score": None if scores.dropna().empty else float(scores.max()),
    }


def build_account_profile_metrics(profile: dict[str, pd.DataFrame]) -> dict[str, object]:
    if not isinstance(profile, dict):
        raise DashboardDataError("profile must be a dictionary")
    tx_summary = build_account_transaction_summary(profile.get("transactions", pd.DataFrame()))
    alert_summary = build_account_alert_summary(profile.get("alerts", pd.DataFrame()))
    case_summary = build_account_case_summary(profile.get("cases", pd.DataFrame()))
    risk_scores = profile.get("account_risk_scores", pd.DataFrame())
    anomaly_scores = profile.get("anomaly_scores", pd.DataFrame())
    graph_features = profile.get("graph_features", pd.DataFrame())
    latest_risk = (
        None
        if risk_scores.empty or "account_risk_score" not in risk_scores
        else float(pd.to_numeric(risk_scores["account_risk_score"], errors="coerce").iloc[0])
    )
    latest_anomaly = (
        None
        if anomaly_scores.empty or "anomaly_score" not in anomaly_scores
        else float(pd.to_numeric(anomaly_scores["anomaly_score"], errors="coerce").iloc[0])
    )
    community_id = (
        None
        if graph_features.empty or "community_id" not in graph_features
        else graph_features["community_id"].iloc[0]
    )
    return {
        **tx_summary,
        **alert_summary,
        **case_summary,
        "latest_account_risk_score": latest_risk,
        "latest_anomaly_score": latest_anomaly,
        "graph_community_id": None if pd.isna(community_id) else str(community_id),
    }
