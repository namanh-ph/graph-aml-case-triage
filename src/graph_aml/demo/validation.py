"""Post-run validation helpers for demo readiness."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.demo.config import DemoOrchestrationConfig, validate_demo_orchestration_config
from graph_aml.demo.exceptions import DemoValidationError

DEMO_COUNT_TABLES: dict[str, str] = {
    "transactions": "staging.transactions",
    "accounts": "staging.accounts",
    "alerts": "aml.alerts",
    "graph_features": "mart.graph_features",
    "account_anomaly_scores": "mart.account_anomaly_scores",
    "account_risk_scores": "mart.account_risk_scores",
    "cases": "aml.cases",
    "case_risk_scores": "aml.case_risk_scores",
    "case_evidence_packs": "aml.case_evidence_packs",
    "case_explanations": "aml.case_explanations",
    "audit_events": "governance.audit_events",
}

THRESHOLD_COUNT_KEYS: dict[str, str] = {
    "min_transactions": "transactions",
    "min_accounts": "accounts",
    "min_alerts": "alerts",
    "min_cases": "cases",
    "min_case_risk_scores": "case_risk_scores",
    "min_case_evidence_packs": "case_evidence_packs",
    "min_audit_events": "audit_events",
}


def _config_or_default(config: DemoOrchestrationConfig | None) -> DemoOrchestrationConfig:
    resolved = config or DemoOrchestrationConfig()
    validate_demo_orchestration_config(resolved)
    return resolved


def _count_value(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float | str):
        return int(value)
    raise DemoValidationError(f"count value is not numeric: {value!r}")


def read_demo_database_counts(engine: Engine) -> dict[str, object]:
    """Read post-demo database counts from existing persisted tables."""

    if engine is None:
        raise DemoValidationError("engine is required")
    counts: dict[str, object] = {}
    try:
        for key, table_name in DEMO_COUNT_TABLES.items():
            frame = pd.read_sql_query(
                text(f"SELECT COUNT(*) AS row_count FROM {table_name}"),
                engine,
            )
            counts[key] = int(frame["row_count"].iloc[0]) if not frame.empty else 0
    except Exception as exc:
        raise DemoValidationError(f"failed to read demo database counts: {exc}") from exc
    return counts


def validate_demo_database_counts(
    counts: dict[str, object],
    config: DemoOrchestrationConfig | None = None,
) -> dict[str, object]:
    """Compare database counts with configured demo thresholds."""

    if not isinstance(counts, dict):
        raise DemoValidationError("counts must be a dictionary")
    resolved = _config_or_default(config)
    warnings: list[str] = []
    thresholds: dict[str, int] = {}
    for threshold_name, count_key in THRESHOLD_COUNT_KEYS.items():
        threshold = int(getattr(resolved.validation_thresholds, threshold_name))
        thresholds[threshold_name] = threshold
        observed = _count_value(counts.get(count_key, 0))
        if observed < threshold:
            warnings.append(f"{count_key} below threshold {threshold}: {observed}")
    return {
        "status": "ok" if not warnings else "warning",
        "counts": {str(key): _count_value(value) for key, value in counts.items()},
        "thresholds": thresholds,
        "warnings": warnings,
    }


def validate_demo_artefacts(
    report_dir: str | None = None,
    config: DemoOrchestrationConfig | None = None,
) -> dict[str, object]:
    """Validate local demo artefact presence."""

    resolved = _config_or_default(config)
    directory = Path(report_dir or resolved.demo.artefact_output_dir)
    if not directory.exists():
        min_files = int(resolved.validation_thresholds.min_validation_files)
        return {
            "status": "warning" if min_files > 0 else "ok",
            "report_dir": str(directory),
            "file_count": 0,
            "warnings": ["report directory does not exist"] if min_files > 0 else [],
        }
    if not directory.is_dir():
        raise DemoValidationError("report_dir must be a directory")
    files = sorted(path for path in directory.rglob("*") if path.is_file())
    min_files = int(resolved.validation_thresholds.min_validation_files)
    warnings = [] if len(files) >= min_files else [f"validation files below threshold {min_files}"]
    return {
        "status": "ok" if not warnings else "warning",
        "report_dir": str(directory),
        "file_count": len(files),
        "extensions": sorted({path.suffix.lower() for path in files if path.suffix}),
        "warnings": warnings,
    }


def build_demo_validation_summary(
    engine: Engine | None = None,
    config: DemoOrchestrationConfig | None = None,
) -> dict[str, object]:
    """Build a combined database and artefact validation summary."""

    resolved = _config_or_default(config)
    database: dict[str, object]
    if engine is None:
        database = {"status": "skipped", "reason": "engine_not_supplied"}
    else:
        counts = read_demo_database_counts(engine)
        database = validate_demo_database_counts(counts, resolved)
    artefacts = validate_demo_artefacts(resolved.demo.artefact_output_dir, resolved)
    statuses = (database.get("status"), artefacts.get("status"))
    return {
        "demo_name": resolved.demo.name,
        "demo_version": resolved.demo.version,
        "status": "ok" if all(status in {"ok", "skipped"} for status in statuses) else "warning",
        "database": database,
        "artefacts": artefacts,
    }
