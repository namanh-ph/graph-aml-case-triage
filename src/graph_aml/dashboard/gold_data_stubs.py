"""Gold-layer stubs for dashboard data modules that haven't been ported yet.

These return empty DataFrames or sensible empty payloads so the corresponding
Streamlit pages render "no data" cleanly instead of raising SQL errors.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


_EMPTY = pd.DataFrame()


# --- account_data.py replacements -------------------------------------------------

def read_account_profile(*args: Any, **kwargs: Any) -> dict[str, pd.DataFrame]:
    return {
        "header": _EMPTY,
        "features": _EMPTY,
        "transactions": _EMPTY,
        "alerts": _EMPTY,
        "cases": _EMPTY,
        "counterparties": _EMPTY,
    }


def read_account_profile_alerts(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_account_profile_cases(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_account_profile_counterparties(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_account_profile_features(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_account_profile_header(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


def read_account_profile_transactions(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return _EMPTY


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
