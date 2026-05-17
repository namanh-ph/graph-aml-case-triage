"""Read-only inputs for release readiness summaries."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.release.config import ReleaseReadinessConfig
from graph_aml.release.exceptions import ReleaseInputError


def _scalar_summary(engine: Engine, sql: str, key: str) -> dict[str, object]:
    try:
        frame = pd.read_sql_query(text(sql), engine, params=cast(Any, {}))
        value = frame.iloc[0, 0] if not frame.empty else 0
        return {key: int(cast(Any, value)) if pd.notna(value) else 0, "available": True}
    except Exception as exc:
        return {key: 0, "available": False, "error": str(exc)}


def read_release_audit_summary(engine: Engine) -> dict[str, object]:
    """Read compact audit summary for release evidence."""

    return _scalar_summary(
        engine,
        "SELECT COUNT(*) FROM governance.audit_events",
        "audit_event_count",
    )


def read_release_model_summary(engine: Engine) -> dict[str, object]:
    """Read compact model summary for release evidence."""

    summary = {}
    summary.update(
        _scalar_summary(engine, "SELECT COUNT(*) FROM governance.model_runs", "model_run_count")
    )
    summary.update(
        _scalar_summary(
            engine,
            "SELECT COUNT(*) FROM governance.supervised_model_runs",
            "supervised_model_run_count",
        )
    )
    return summary


def read_release_validation_summary(engine: Engine) -> dict[str, object]:
    """Read compact validation summary for release evidence."""

    summary = {}
    for table, key in (
        ("governance.model_comparison_runs", "model_comparison_run_count"),
        ("governance.monitoring_runs", "monitoring_run_count"),
        ("governance.explainability_runs", "explainability_run_count"),
    ):
        summary.update(_scalar_summary(engine, f"SELECT COUNT(*) FROM {table}", key))
    return summary


def read_release_governance_summary(engine: Engine) -> dict[str, object]:
    """Read compact governance inventory summary for release evidence."""

    return _scalar_summary(
        engine,
        "SELECT COUNT(*) FROM governance.inventory_runs",
        "governance_inventory_run_count",
    )


def read_release_security_summary(engine: Engine) -> dict[str, object]:
    """Read compact security controls summary for release evidence."""

    return _scalar_summary(
        engine,
        "SELECT COUNT(*) FROM governance.security_control_runs",
        "security_control_run_count",
    )


def read_release_readiness_inputs(
    engine: Engine | None = None,
    config: ReleaseReadinessConfig | None = None,
) -> dict[str, object]:
    """Read summaries needed by release readiness; local-only when engine is absent."""

    resolved = config or ReleaseReadinessConfig()
    try:
        if engine is None:
            return {
                "engine_supplied": False,
                "release_name": resolved.release_name,
                "release_version": resolved.release_version,
                "audit_summary": {"available": False},
                "model_summary": {"available": False},
                "validation_summary": {"available": False},
                "governance_summary": {"available": False},
                "security_summary": {"available": False},
            }
        return {
            "engine_supplied": True,
            "release_name": resolved.release_name,
            "release_version": resolved.release_version,
            "audit_summary": read_release_audit_summary(engine),
            "model_summary": read_release_model_summary(engine),
            "validation_summary": read_release_validation_summary(engine),
            "governance_summary": read_release_governance_summary(engine),
            "security_summary": read_release_security_summary(engine),
        }
    except Exception as exc:
        raise ReleaseInputError(f"release input read failed: {exc}") from exc
