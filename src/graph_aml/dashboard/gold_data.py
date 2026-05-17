"""Gold-layer parquet readers for the local Streamlit dashboard.

Replaces the PostgreSQL-bound readers in ``dashboard/data.py`` with pure
filesystem reads against ``data/gold/*.parquet`` so the dashboard runs without
Postgres, Neo4j, or any background services.

All functions return ``pd.DataFrame`` (or plain dicts) with the same shape as
their PG counterparts so existing Streamlit pages can swap imports.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import pandas as pd

from graph_aml.dashboard.exceptions import DashboardDataError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLD_DIR = PROJECT_ROOT / "data" / "gold"


def _resolve_gold_dir(gold_dir: Path | str | None) -> Path:
    return Path(gold_dir) if gold_dir is not None else DEFAULT_GOLD_DIR


@lru_cache(maxsize=64)
def _read_table_cached(gold_dir_str: str, table: str) -> pd.DataFrame:
    """Read a gold-layer parquet table with simple LRU caching."""

    path = Path(gold_dir_str) / f"{table}.parquet"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_parquet(path)


def _read_table(gold_dir: Path, table: str) -> pd.DataFrame:
    """Read one gold-layer parquet table, returning empty DataFrame if missing."""

    return _read_table_cached(str(gold_dir), table).copy()


def clear_dashboard_cache() -> None:
    """Drop the cached gold-layer tables (useful when data on disk changes)."""

    _read_table_cached.cache_clear()


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise DashboardDataError("limit must be non-negative")
    return int(limit)


def _normalise_values(values: Sequence[str] | None) -> list[str]:
    if not values:
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _apply_isin_filter(
    frame: pd.DataFrame,
    column: str,
    values: Sequence[str] | None,
) -> pd.DataFrame:
    clean = _normalise_values(values)
    if not clean or column not in frame.columns:
        return frame
    return frame[frame[column].astype(str).isin(clean)]


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame.columns or frame.empty:
        return {}
    counts = frame[column].fillna("").astype(str).value_counts().sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def read_dashboard_overview_counts(
    gold_dir: Path | str | None = None,
) -> dict[str, object]:
    """Read high-level dashboard counts and simple distributions from gold parquet."""

    gold = _resolve_gold_dir(gold_dir)
    try:
        alerts = _read_table(gold, "alerts")
        cases = _read_table(gold, "cases")
        case_risk_scores = _read_table(gold, "case_risk_scores")
        lifecycle_events = _read_table(gold, "case_lifecycle_events")
        features = _read_table(gold, "features_account_daily")

        account_count = (
            int(features["account_id"].nunique()) if "account_id" in features.columns else 0
        )
        transaction_count = 0
        # transaction count is derived from silver since gold doesn't include raw transactions
        silver_tx = PROJECT_ROOT / "data" / "silver" / "transactions.parquet"
        if silver_tx.is_file():
            transaction_count = int(pd.read_parquet(silver_tx, columns=["transaction_id"]).shape[0])

        return {
            "transaction_count": transaction_count,
            "account_count": account_count,
            "alert_count": int(len(alerts)),
            "case_count": int(len(cases)),
            "case_risk_score_count": int(len(case_risk_scores)),
            "lifecycle_event_count": int(len(lifecycle_events)),
            "case_status_counts": _value_counts(cases, "status"),
            "case_risk_band_counts": _value_counts(case_risk_scores, "risk_band"),
            "alert_severity_counts": _value_counts(alerts, "severity"),
            "alert_typology_counts": _value_counts(alerts, "typology"),
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard overview counts: {exc}") from exc


def read_dashboard_alert_queue(
    gold_dir: Path | str | None = None,
    severities: tuple[str, ...] | list[str] | None = None,
    typologies: tuple[str, ...] | list[str] | None = None,
    account_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Filtered alert queue read from gold parquet."""

    gold = _resolve_gold_dir(gold_dir)
    safe_limit = _validate_limit(limit)
    try:
        alerts = _read_table(gold, "alerts")
        if alerts.empty:
            return alerts
        alerts = _apply_isin_filter(alerts, "severity", severities)
        alerts = _apply_isin_filter(alerts, "typology", typologies)
        if account_id and "account_id" in alerts.columns:
            needle = account_id.strip().lower()
            alerts = alerts[
                alerts["account_id"].astype(str).str.lower().str.contains(needle, na=False)
            ]
        sort_cols = [c for c in ("risk_score_rule", "created_at", "alert_id") if c in alerts.columns]
        if sort_cols:
            ascending = [c == "alert_id" for c in sort_cols]
            alerts = alerts.sort_values(by=sort_cols, ascending=ascending, na_position="last")
        if safe_limit is not None:
            alerts = alerts.head(safe_limit)
        return alerts.reset_index(drop=True)
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard alert queue: {exc}") from exc


def read_dashboard_case_queue(
    gold_dir: Path | str | None = None,
    statuses: tuple[str, ...] | list[str] | None = None,
    risk_bands: tuple[str, ...] | list[str] | None = None,
    assigned_to: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Filtered case queue joined with the latest risk score per case."""

    gold = _resolve_gold_dir(gold_dir)
    safe_limit = _validate_limit(limit)
    try:
        cases = _read_table(gold, "cases")
        scores = _read_table(gold, "case_risk_scores")
        if cases.empty:
            return cases

        # Latest score per case_id (mirrors PG ``DISTINCT ON (case_id)``).
        if not scores.empty and "case_id" in scores.columns:
            sort_cols = [c for c in ("case_id", "scored_at", "case_risk_score") if c in scores.columns]
            ascending = [c == "case_id" for c in sort_cols]
            scores_sorted = scores.sort_values(by=sort_cols, ascending=ascending, na_position="last")
            latest = scores_sorted.drop_duplicates(subset=["case_id"], keep="first")
            score_cols = [
                c
                for c in ("case_id", "case_risk_score", "risk_band", "risk_rank", "scored_at")
                if c in latest.columns
            ]
            latest = latest[score_cols].rename(columns={"scored_at": "risk_scored_at"})
            merged = cases.merge(latest, on="case_id", how="left")
        else:
            merged = cases.copy()
            for col in ("case_risk_score", "risk_band", "risk_rank", "risk_scored_at"):
                if col not in merged.columns:
                    merged[col] = pd.NA

        merged = _apply_isin_filter(merged, "status", statuses)
        merged = _apply_isin_filter(merged, "risk_band", risk_bands)
        if assigned_to and "assigned_to" in merged.columns:
            merged = merged[merged["assigned_to"].astype(str) == assigned_to]

        sort_cols = [
            c
            for c in ("risk_rank", "case_risk_score", "priority_score", "case_id")
            if c in merged.columns
        ]
        ascending = [c in {"risk_rank", "case_id"} for c in sort_cols]
        if sort_cols:
            merged = merged.sort_values(by=sort_cols, ascending=ascending, na_position="last")

        if safe_limit is not None:
            merged = merged.head(safe_limit)
        return merged.reset_index(drop=True)
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard case queue: {exc}") from exc


def read_dashboard_lifecycle_events(
    gold_dir: Path | str | None = None,
    case_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Per-case lifecycle event timeline."""

    if not case_id or not case_id.strip():
        raise DashboardDataError("case_id must be non-empty")
    gold = _resolve_gold_dir(gold_dir)
    safe_limit = _validate_limit(limit)
    try:
        events = _read_table(gold, "case_lifecycle_events")
        if events.empty or "case_id" not in events.columns:
            return events
        events = events[events["case_id"].astype(str) == case_id]
        sort_cols = [c for c in ("action_timestamp", "action_id") if c in events.columns]
        if sort_cols:
            ascending = [c == "action_id" for c in sort_cols]
            events = events.sort_values(by=sort_cols, ascending=ascending, na_position="last")
        if safe_limit is not None:
            events = events.head(safe_limit)
        return events.reset_index(drop=True)
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to read lifecycle events: {exc}") from exc


def read_dashboard_case_detail(
    case_id: str,
    gold_dir: Path | str | None = None,
) -> dict[str, pd.DataFrame]:
    """All artefacts for one case: case row, scores, alerts, entities, lifecycle."""

    if not case_id or not case_id.strip():
        raise DashboardDataError("case_id must be non-empty")
    gold = _resolve_gold_dir(gold_dir)
    try:
        def _by_case(table: str, sort: tuple[str, ...] = ()) -> pd.DataFrame:
            frame = _read_table(gold, table)
            if frame.empty or "case_id" not in frame.columns:
                return frame
            scoped = frame[frame["case_id"].astype(str) == case_id]
            if sort:
                cols = [c for c in sort if c in scoped.columns]
                if cols:
                    scoped = scoped.sort_values(by=cols, na_position="last")
            return scoped.reset_index(drop=True)

        case = _by_case("cases")
        case_risk_scores = _by_case("case_risk_scores", ("scored_at", "case_risk_score"))
        case_alerts = _by_case("case_alerts", ("alert_id",))
        case_entities = _by_case("case_entities", ("entity_type", "entity_id"))

        alerts = pd.DataFrame()
        if not case_alerts.empty and "alert_id" in case_alerts.columns:
            all_alerts = _read_table(gold, "alerts")
            if not all_alerts.empty and "alert_id" in all_alerts.columns:
                wanted_ids = set(case_alerts["alert_id"].dropna().astype(str))
                alerts = all_alerts[all_alerts["alert_id"].astype(str).isin(wanted_ids)]
                sort_cols = [
                    c for c in ("risk_score_rule", "created_at", "alert_id") if c in alerts.columns
                ]
                if sort_cols:
                    ascending = [c == "alert_id" for c in sort_cols]
                    alerts = alerts.sort_values(by=sort_cols, ascending=ascending, na_position="last")
                alerts = alerts.reset_index(drop=True)

        return {
            "case": case,
            "case_risk_scores": case_risk_scores,
            "case_alerts": case_alerts,
            "alerts": alerts,
            "case_entities": case_entities,
            "lifecycle_events": read_dashboard_lifecycle_events(gold, case_id),
        }
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard case detail: {exc}") from exc


def read_dashboard_case_evidence(
    case_id: str,
    gold_dir: Path | str | None = None,
) -> dict[str, pd.DataFrame]:
    """Evidence packs and analyst-facing explanations for one case."""

    if not case_id or not case_id.strip():
        raise DashboardDataError("case_id must be non-empty")
    gold = _resolve_gold_dir(gold_dir)
    try:
        def _by_case(table: str, version_col: str) -> pd.DataFrame:
            frame = _read_table(gold, table)
            if frame.empty or "case_id" not in frame.columns:
                return frame
            scoped = frame[frame["case_id"].astype(str) == case_id]
            sort_cols = [c for c in ("created_at", version_col) if c in scoped.columns]
            if sort_cols:
                ascending = [c == version_col for c in sort_cols]
                scoped = scoped.sort_values(by=sort_cols, ascending=ascending, na_position="last")
            return scoped.reset_index(drop=True)

        return {
            "evidence_packs": _by_case("case_evidence_packs", "evidence_version"),
            "explanations": _by_case("case_explanations", "explanation_version"),
        }
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard case evidence: {exc}") from exc


def _distinct_list(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame.columns or frame.empty:
        return []
    values = frame[column].dropna().astype(str).map(str.strip)
    return sorted({v for v in values if v})


def read_dashboard_filter_options(
    gold_dir: Path | str | None = None,
) -> dict[str, list[str]]:
    """Read filter choices for dashboard pages from gold parquet."""

    gold = _resolve_gold_dir(gold_dir)
    try:
        alerts = _read_table(gold, "alerts")
        cases = _read_table(gold, "cases")
        scores = _read_table(gold, "case_risk_scores")
        return {
            "alert_severities": _distinct_list(alerts, "severity"),
            "alert_typologies": _distinct_list(alerts, "typology"),
            "case_statuses": _distinct_list(cases, "status"),
            "case_risk_bands": _distinct_list(scores, "risk_band"),
            "assigned_to": _distinct_list(cases, "assigned_to"),
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard filter options: {exc}") from exc
