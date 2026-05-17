"""Download serialisation helpers for dashboard pages."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.security import (
    SecurityControlConfig,
    SecurityControlError,
    dataframe_to_sanitised_csv_bytes,
)


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    if not isinstance(frame, pd.DataFrame):
        raise DashboardDataError("frame must be a DataFrame")
    csv_text = str(frame.to_csv(index=False))
    return csv_text.encode("utf-8")


def dataframe_to_security_csv_bytes(
    frame: pd.DataFrame,
    sensitive_fields: pd.DataFrame | None = None,
    role: str | None = None,
    export_mode: str | None = None,
    security_config: SecurityControlConfig | None = None,
) -> bytes:
    """Serialise CSV through security export controls when inventory is available."""

    if sensitive_fields is None:
        return dataframe_to_csv_bytes(frame)
    try:
        return dataframe_to_sanitised_csv_bytes(
            frame,
            sensitive_fields,
            role=role,
            export_mode=export_mode,
            config=security_config,
        )
    except SecurityControlError as exc:
        raise DashboardDataError(f"Security export control failed: {exc}") from exc


def dataframe_to_json_bytes(frame: pd.DataFrame) -> bytes:
    if not isinstance(frame, pd.DataFrame):
        raise DashboardDataError("frame must be a DataFrame")
    records = frame.astype(object).to_dict(orient="records")
    return json.dumps(records, indent=2, sort_keys=True, default=str).encode("utf-8")


def dict_to_json_bytes(payload: dict[str, object]) -> bytes:
    if not isinstance(payload, dict):
        raise DashboardDataError("payload must be a dictionary")
    return json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")


def safe_download_filename(prefix: str, suffix: str = "csv") -> str:
    clean_prefix = re.sub(r"[^A-Za-z0-9_.-]+", "_", prefix.strip()).strip("_") or "download"
    clean_suffix = re.sub(r"[^A-Za-z0-9]+", "", suffix.strip()) or "csv"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{clean_prefix}_{timestamp}.{clean_suffix}"


def bytes_for_report_file(
    file_path: Path | str,
    report_dir: Path | str = "reports/model_validation",
) -> bytes:
    root = Path(report_dir).resolve()
    candidate = Path(file_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise DashboardDataError("report path is outside the configured report directory")
    if not resolved.exists() or not resolved.is_file():
        raise DashboardDataError("report file does not exist")
    return resolved.read_bytes()
