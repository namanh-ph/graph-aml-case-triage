"""High-level raw-to-staging pipeline orchestration."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine

from graph_aml.staging.audit import write_staging_audit_event
from graph_aml.staging.extract import read_raw_dataset
from graph_aml.staging.load import load_staging_dataset
from graph_aml.staging.transform import transform_raw_dataset, validate_staging_dataset


def transform_raw_to_staging_frames(
    engine: Engine,
    limit: int | None = None,
    validate: bool = True,
) -> dict[str, pd.DataFrame]:
    """Read raw PostgreSQL records and return transformed staging frames."""

    raw_dataset = read_raw_dataset(engine, limit=limit)
    staging_dataset = transform_raw_dataset(raw_dataset)
    if validate:
        validate_staging_dataset(staging_dataset)
    return staging_dataset


def run_staging_pipeline(
    engine: Engine,
    limit: int | None = None,
    validate: bool = True,
    write_audit: bool = True,
) -> dict[str, int]:
    """Run raw extraction, transformation, validation, load, and optional audit."""

    staging_dataset = transform_raw_to_staging_frames(engine, limit=limit, validate=validate)
    row_counts = load_staging_dataset(engine, staging_dataset)
    if write_audit:
        write_staging_audit_event(
            engine,
            row_counts=row_counts,
            status="completed",
            metadata={"limit": limit, "validate": validate},
        )
    return row_counts
