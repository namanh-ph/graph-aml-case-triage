"""Compatibility shims for dashboard pages that previously required a PG engine.

The dashboard now reads from ``data/gold/*.parquet`` exclusively. These helpers
exist so existing Streamlit pages that still call ``create_dashboard_engine``
keep working without changes; both functions are intentional no-ops.
"""

from __future__ import annotations

from typing import Any


def create_dashboard_engine() -> Any:
    """Return ``None`` -- the dashboard no longer needs a database engine."""

    return None


def dispose_dashboard_engine(engine: Any | None) -> None:
    """No-op -- kept for backwards compatibility with existing page code."""

    return None


def check_dashboard_database_health(engine: Any | None = None) -> dict[str, object]:
    """Lightweight health response for the gold-parquet dashboard."""

    return {"status": "ok", "query_ok": True, "mode": "gold-parquet"}
