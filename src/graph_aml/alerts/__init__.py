"""AML alert schema public API."""

from graph_aml.alerts.audit import write_alert_persistence_audit_event
from graph_aml.alerts.dataframe import (
    alerts_to_dataframe,
    dataframe_to_alerts,
    normalise_alert_dataframe,
)
from graph_aml.alerts.exceptions import (
    AlertAuditError,
    AlertDataFrameError,
    AlertError,
    AlertPersistenceError,
    AlertValidationError,
)
from graph_aml.alerts.ids import (
    build_alert_id,
    build_sequential_alert_id,
    normalise_rule_name_for_id,
)
from graph_aml.alerts.persistence import (
    AML_ALERTS_TABLE,
    persist_alerts,
    prepare_alerts_for_persistence,
    read_alerts,
    upsert_alerts,
)
from graph_aml.alerts.schema import (
    ALERT_COLUMNS,
    ALERT_SEVERITIES,
    ALERT_SOURCES,
    ALERT_STATUSES,
    AlertRecord,
    alert_record_from_dict,
    alert_record_to_dict,
    create_alert_record,
)
from graph_aml.alerts.summary import summarise_alerts
from graph_aml.alerts.validation import (
    validate_alert_dataframe,
    validate_alert_record,
    validate_alert_records,
)

__all__ = [
    "ALERT_COLUMNS",
    "ALERT_SEVERITIES",
    "ALERT_SOURCES",
    "ALERT_STATUSES",
    "AML_ALERTS_TABLE",
    "AlertAuditError",
    "AlertDataFrameError",
    "AlertError",
    "AlertPersistenceError",
    "AlertRecord",
    "AlertValidationError",
    "alert_record_from_dict",
    "alert_record_to_dict",
    "alerts_to_dataframe",
    "build_alert_id",
    "build_sequential_alert_id",
    "create_alert_record",
    "dataframe_to_alerts",
    "normalise_alert_dataframe",
    "normalise_rule_name_for_id",
    "persist_alerts",
    "prepare_alerts_for_persistence",
    "read_alerts",
    "summarise_alerts",
    "upsert_alerts",
    "validate_alert_dataframe",
    "validate_alert_record",
    "validate_alert_records",
    "write_alert_persistence_audit_event",
]
