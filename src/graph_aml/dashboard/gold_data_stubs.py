"""Gold-layer stubs for dashboard data modules that haven't been ported yet.

These return empty DataFrames or sensible empty payloads so the corresponding
Streamlit pages render "no data" cleanly instead of raising SQL errors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from graph_aml.dashboard.exceptions import DashboardDataError

_EMPTY = pd.DataFrame()
_DATA_ROOT = Path(__file__).resolve().parents[3] / "data"


def _read_layer_table(layer: str, table: str) -> pd.DataFrame:
    path = _DATA_ROOT / layer / f"{table}.parquet"
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read {path}: {exc}") from exc


def _account_rows(layer: str, table: str, account_id: str) -> pd.DataFrame:
    frame = _read_layer_table(layer, table)
    if frame.empty or "account_id" not in frame.columns:
        return pd.DataFrame()
    return frame[frame["account_id"].astype(str) == account_id].reset_index(drop=True)


# --- account_data.py replacements -------------------------------------------------


def read_account_profile(
    engine: Any,
    account_id: str,
    config: Any | None = None,
) -> dict[str, pd.DataFrame]:
    clean = str(account_id).strip()
    if not clean:
        raise DashboardDataError("account_id must be non-empty")
    limits = getattr(config, "account_profile", None)
    return {
        "header": read_account_profile_header(engine, clean),
        "transactions": read_account_profile_transactions(
            engine, clean, limit=getattr(limits, "max_transactions", None)
        ),
        "alerts": read_account_profile_alerts(
            engine, clean, limit=getattr(limits, "max_alerts", None)
        ),
        "cases": read_account_profile_cases(
            engine, clean, limit=getattr(limits, "max_cases", None)
        ),
        "counterparties": read_account_profile_counterparties(
            engine, clean, limit=getattr(limits, "max_counterparties", None)
        ),
        **read_account_profile_features(engine, clean),
    }


def read_account_profile_alerts(
    engine: Any, account_id: str, limit: int | None = None
) -> pd.DataFrame:
    frame = _account_rows("gold", "alerts", str(account_id).strip())
    if not frame.empty and "risk_score_rule" in frame.columns:
        frame = frame.sort_values("risk_score_rule", ascending=False)
    return frame.head(limit).reset_index(drop=True) if limit is not None else frame


def read_account_profile_cases(
    engine: Any, account_id: str, limit: int | None = None
) -> pd.DataFrame:
    clean = str(account_id).strip()
    cases = _read_layer_table("gold", "cases")
    if cases.empty:
        return cases
    direct_column = "account_id" if "account_id" in cases.columns else "primary_account_id"
    direct = cases[cases[direct_column].astype(str) == clean]
    entities = _read_layer_table("gold", "case_entities")
    if not entities.empty:
        linked_ids = entities.loc[entities["entity_id"].astype(str) == clean, "case_id"].astype(str)
        direct = pd.concat(
            [direct, cases[cases["case_id"].astype(str).isin(linked_ids)]],
            ignore_index=True,
        ).drop_duplicates("case_id")
    scores = _read_layer_table("gold", "case_risk_scores")
    if not scores.empty:
        direct = direct.merge(scores, on="case_id", how="left", suffixes=("", "_score"))
    if "case_risk_score" in direct.columns:
        direct = direct.sort_values("case_risk_score", ascending=False, na_position="last")
    direct = direct.reset_index(drop=True)
    return direct.head(limit) if limit is not None else direct


def read_account_profile_counterparties(
    engine: Any, account_id: str, limit: int | None = None
) -> pd.DataFrame:
    transactions = read_account_profile_transactions(engine, account_id)
    if transactions.empty:
        return pd.DataFrame()
    clean = str(account_id).strip()
    transactions = transactions.copy()
    transactions["counterparty_key"] = transactions["receiver_account_id"].where(
        transactions["sender_account_id"].astype(str) == clean,
        transactions["sender_account_id"],
    )
    summary = (
        transactions.groupby("counterparty_key", dropna=False)
        .agg(
            transaction_count=("transaction_id", "count"),
            total_amount=("amount", "sum"),
            latest_transaction_timestamp=("transaction_timestamp", "max"),
        )
        .sort_values("total_amount", ascending=False)
        .reset_index()
    )
    return summary.head(limit) if limit is not None else summary


def read_account_profile_features(engine: Any, account_id: str) -> dict[str, pd.DataFrame]:
    clean = str(account_id).strip()
    return {
        "behavioural_features": _account_rows("gold", "features_account_daily", clean),
        "graph_features": _account_rows("gold", "graph_features", clean),
        "anomaly_scores": _account_rows("gold", "account_anomaly_scores", clean),
        "account_risk_scores": _account_rows("gold", "account_risk_scores", clean),
    }


def read_account_profile_header(engine: Any, account_id: str) -> pd.DataFrame:
    clean = str(account_id).strip()
    header = _account_rows("silver", "accounts", clean)
    if header.empty:
        return header
    customers = _read_layer_table("silver", "customers")
    if not customers.empty and "customer_id" in header.columns:
        header = header.merge(customers, on="customer_id", how="left")
    risk = _account_rows("gold", "account_risk_scores", clean)
    if not risk.empty:
        latest_risk = risk.iloc[[0]][["account_risk_score", "risk_band"]].rename(
            columns={"risk_band": "account_risk_band"}
        )
        header = pd.concat(
            [header.reset_index(drop=True), latest_risk.reset_index(drop=True)], axis=1
        )
    graph = _account_rows("gold", "graph_features", clean)
    if not graph.empty and "community_id" in graph.columns:
        header["community_id"] = graph.iloc[0]["community_id"]
    return header


def read_account_profile_transactions(
    engine: Any,
    account_id: str,
    lookback_days: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    clean = str(account_id).strip()
    frame = _read_layer_table("silver", "transactions")
    if frame.empty:
        return frame
    frame = frame[
        (frame["sender_account_id"].astype(str) == clean)
        | (frame["receiver_account_id"].astype(str) == clean)
    ]
    if "transaction_timestamp" in frame.columns:
        frame = frame.sort_values("transaction_timestamp", ascending=False)
    frame = frame.reset_index(drop=True)
    return frame.head(limit) if limit is not None else frame


# --- audit_data.py replacements ---------------------------------------------------


def read_dashboard_audit_events(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_audit_filter_options(*args: Any, **kwargs: Any) -> dict[str, list[str]]:
    return {"components": [], "event_types": [], "statuses": []}


def read_dashboard_audit_summary(*args: Any, **kwargs: Any) -> dict[str, object]:
    return {
        "event_count": 0,
        "component_counts": {},
        "event_type_counts": {},
        "status_counts": {},
        "latest_event_timestamp": None,
    }


# --- graph_data.py replacements ---------------------------------------------------


def read_graph_view_context(*args: Any, **kwargs: Any) -> dict[str, pd.DataFrame]:
    return {"nodes": _EMPTY, "edges": _EMPTY}


def read_graph_view_postgres_edges(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_graph_view_seed_accounts(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


# --- model_metrics_data.py replacements -------------------------------------------


def read_dashboard_account_anomaly_scores(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_account_risk_scores(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_backtesting_metrics(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_case_risk_scores(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_champion_challenger_results(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_drift_metrics(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_explainability_runs(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_global_feature_importance(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_model_cards(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_model_comparison_metrics(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_model_comparison_runs(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_model_metric_bundle(*args: Any, **kwargs: Any) -> dict[str, pd.DataFrame]:
    return {}


def read_dashboard_model_runs(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_monitoring_runs(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_reason_contributions(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_score_decomposition(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_supervised_model_runs(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_supervised_model_scores(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_threshold_recommendations(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_dashboard_volume_monitoring_metrics(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


# --- validation_report_data.py replacements ---------------------------------------


def build_validation_report_index(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def list_validation_report_files(*args: Any, **kwargs: Any) -> list[Any]:
    return []


def read_dashboard_governance_inventory_bundle(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}


def read_dashboard_release_readiness_bundle(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}


def read_dashboard_security_control_bundle(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {}


def read_validation_report_file(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"name": "", "path": "", "content": "", "size_bytes": 0}
