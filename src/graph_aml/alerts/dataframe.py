"""Alert DataFrame conversion utilities."""

from __future__ import annotations

import pandas as pd

from graph_aml.alerts.exceptions import AlertDataFrameError, AlertValidationError
from graph_aml.alerts.schema import (
    ALERT_COLUMNS,
    AlertRecord,
    alert_record_from_dict,
    alert_record_to_dict,
)
from graph_aml.alerts.validation import validate_alert_dataframe, validate_alert_records


def alerts_to_dataframe(alerts: tuple[AlertRecord, ...] | list[AlertRecord]) -> pd.DataFrame:
    """Convert alert records into a DataFrame with stable column ordering."""

    try:
        validate_alert_records(alerts)
        rows = [alert_record_to_dict(alert) for alert in alerts]
        frame = pd.DataFrame(rows, columns=ALERT_COLUMNS)
        if frame.empty:
            return pd.DataFrame(columns=ALERT_COLUMNS)
        return normalise_alert_dataframe(frame)
    except (AlertDataFrameError, AlertValidationError):
        raise
    except Exception as exc:
        raise AlertDataFrameError(f"Failed to convert alerts to DataFrame: {exc}") from exc


def dataframe_to_alerts(frame: pd.DataFrame) -> tuple[AlertRecord, ...]:
    """Convert a DataFrame into validated alert records."""

    try:
        normalised = normalise_alert_dataframe(frame)
        return tuple(
            alert_record_from_dict(record)
            for record in normalised.loc[:, ALERT_COLUMNS].astype(object).to_dict(orient="records")
        )
    except (AlertDataFrameError, AlertValidationError):
        raise
    except Exception as exc:
        raise AlertDataFrameError(f"Failed to convert DataFrame to alerts: {exc}") from exc


def normalise_alert_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a validated alert DataFrame without mutating the input."""

    try:
        output = frame.copy()
        for column in ALERT_COLUMNS:
            if column not in output.columns:
                output[column] = pd.NA
        output["alert_status"] = output["alert_status"].fillna("New")
        now = pd.Timestamp.utcnow().replace(microsecond=0).isoformat()
        output["created_at"] = output["created_at"].fillna(now)
        output["updated_at"] = output["updated_at"].fillna(now)
        alerts = [
            alert_record_from_dict(record)
            for record in output.loc[:, ALERT_COLUMNS].astype(object).to_dict(orient="records")
        ]
        normalised = pd.DataFrame(
            [alert_record_to_dict(alert) for alert in alerts],
            columns=ALERT_COLUMNS,
        )
        validate_alert_dataframe(normalised)
        if normalised.empty:
            return normalised
        return normalised.sort_values(
            ["created_at", "alert_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except AlertValidationError as exc:
        raise AlertDataFrameError(f"Invalid alert DataFrame: {exc}") from exc
    except AlertDataFrameError:
        raise
    except Exception as exc:
        raise AlertDataFrameError(f"Failed to normalise alert DataFrame: {exc}") from exc
