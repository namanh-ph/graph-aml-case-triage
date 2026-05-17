"""Raw ingestion utilities for silver-layer parquet datasets."""

from graph_aml.ingestion.audit import write_ingestion_audit_event
from graph_aml.ingestion.exceptions import (
    IngestionAuditError,
    IngestionError,
    IngestionSourceError,
    RawIngestionError,
)
from graph_aml.ingestion.raw_loader import (
    DEFAULT_SOURCE_SYSTEM,
    RAW_TABLE_MAPPING,
    ingest_silver_to_raw,
    insert_raw_records,
    read_table_file,
)
from graph_aml.ingestion.records import (
    build_raw_payload,
    build_record_hash,
    dataframe_to_raw_records,
    normalise_missing_values,
)
from graph_aml.ingestion.sources import (
    DEFAULT_SILVER_DIR,
    TABLE_NAMES,
    resolve_silver_paths,
)

__all__ = [
    "DEFAULT_SILVER_DIR",
    "DEFAULT_SOURCE_SYSTEM",
    "IngestionAuditError",
    "IngestionError",
    "IngestionSourceError",
    "RAW_TABLE_MAPPING",
    "RawIngestionError",
    "TABLE_NAMES",
    "build_raw_payload",
    "build_record_hash",
    "dataframe_to_raw_records",
    "ingest_silver_to_raw",
    "insert_raw_records",
    "normalise_missing_values",
    "read_table_file",
    "resolve_silver_paths",
    "write_ingestion_audit_event",
]
