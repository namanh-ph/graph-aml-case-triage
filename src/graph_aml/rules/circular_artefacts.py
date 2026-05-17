"""Local artefact writers for circular flow detections."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.alerts import AlertRecord, alert_record_to_dict
from graph_aml.rules.circular_flow import (
    CircularFlowDetectionConfig,
    CircularFlowRuleConfig,
    circular_flow_detections_to_dicts,
    detect_circular_flows,
    run_circular_flow_detection_and_alerts,
)
from graph_aml.rules.exceptions import RuleExecutionError, RuleInputError
from graph_aml.rules.summary import summarise_circular_flow_detections


def write_circular_flow_detections_json(
    detections: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/circular_flow_detections.json",
) -> Path:
    """Write circular-flow detections as deterministic JSON."""

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = circular_flow_detections_to_dicts(detections)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to write circular flow detection JSON: {exc}") from exc


def write_circular_flow_detections_csv(
    detections: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/circular_flow_detections.csv",
) -> Path:
    """Write circular-flow detections as CSV."""

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = detections.copy()
        for column in ("cycle_accounts", "evidence_ids"):
            if column in frame.columns:
                frame[column] = frame[column].apply(
                    lambda value: (
                        "|".join(str(item) for item in value)
                        if isinstance(value, tuple | list)
                        else value
                    )
                )
        frame.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise RuleExecutionError(f"Failed to write circular flow detection CSV: {exc}") from exc


def write_circular_flow_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/circular_flow_summary.json",
) -> Path:
    """Write circular-flow summary metrics as deterministic JSON."""

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(summary, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise RuleExecutionError(f"Failed to write circular flow summary JSON: {exc}") from exc


def write_circular_flow_alerts_json(
    alerts: tuple[AlertRecord, ...] | list[AlertRecord],
    output_path: Path | str = "reports/model_validation/circular_flow_alerts.json",
) -> Path:
    """Write circular-flow alerts as deterministic JSON dictionaries."""

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [alert_record_to_dict(alert) for alert in alerts]
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise RuleExecutionError(f"Failed to write circular flow alert JSON: {exc}") from exc


def generate_circular_flow_detection_artefacts(
    transactions: pd.DataFrame,
    output_dir: Path | str = "reports/model_validation",
    config: CircularFlowDetectionConfig | None = None,
) -> dict[str, Path]:
    """Generate circular-flow detections and write local JSON, CSV, and summary artefacts."""

    try:
        directory = Path(output_dir)
        detections = detect_circular_flows(transactions, config)
        summary = summarise_circular_flow_detections(detections)
        return {
            "detections_json": write_circular_flow_detections_json(
                detections,
                directory / "circular_flow_detections.json",
            ),
            "detections_csv": write_circular_flow_detections_csv(
                detections,
                directory / "circular_flow_detections.csv",
            ),
            "summary_json": write_circular_flow_summary_json(
                summary,
                directory / "circular_flow_summary.json",
            ),
        }
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to generate circular flow detection artefacts: {exc}"
        ) from exc


def generate_circular_flow_rule_artefacts(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    output_dir: Path | str = "reports/model_validation",
    detection_config: CircularFlowDetectionConfig | None = None,
    alert_config: CircularFlowRuleConfig | None = None,
) -> dict[str, Path]:
    """Generate circular-flow detections and alerts and write local artefacts."""

    try:
        directory = Path(output_dir)
        result = run_circular_flow_detection_and_alerts(
            transactions,
            accounts,
            detection_config=detection_config,
            alert_config=alert_config,
        )
        detections = result["detections"]
        detection_summary = result["detection_summary"]
        alerts = result["alerts"]
        if not isinstance(detections, pd.DataFrame):
            raise RuleExecutionError("circular flow detections payload must be a DataFrame")
        if not isinstance(detection_summary, dict):
            raise RuleExecutionError("circular flow detection summary must be a dictionary")
        if not isinstance(alerts, tuple | list):
            raise RuleExecutionError("circular flow alerts payload must be a sequence")
        return {
            "detections_json": write_circular_flow_detections_json(
                detections,
                directory / "circular_flow_detections.json",
            ),
            "detections_csv": write_circular_flow_detections_csv(
                detections,
                directory / "circular_flow_detections.csv",
            ),
            "summary_json": write_circular_flow_summary_json(
                detection_summary,
                directory / "circular_flow_summary.json",
            ),
            "alerts_json": write_circular_flow_alerts_json(
                tuple(alerts),
                directory / "circular_flow_alerts.json",
            ),
        }
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to generate circular flow rule artefacts: {exc}") from exc
