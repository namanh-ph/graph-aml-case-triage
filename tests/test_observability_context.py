"""Tests for observability run context helpers."""

from graph_aml.observability.context import RunContext, create_run_context, utc_now_iso


def test_create_run_context_returns_run_context() -> None:
    context = create_run_context(component="ingestion")

    assert isinstance(context, RunContext)


def test_two_contexts_have_different_run_ids() -> None:
    first = create_run_context(component="ingestion")
    second = create_run_context(component="ingestion")

    assert first.run_id != second.run_id


def test_component_and_pipeline_stage_are_stored() -> None:
    context = create_run_context(component="ingestion", pipeline_stage="raw_load")

    assert context.component == "ingestion"
    assert context.pipeline_stage == "raw_load"


def test_metadata_is_stored() -> None:
    context = create_run_context(component="ingestion", source_file="transactions.csv")

    assert context.metadata["source_file"] == "transactions.csv"


def test_metadata_mapping_is_copied() -> None:
    metadata = {"source_file": "transactions.csv"}
    context = create_run_context(component="ingestion", **metadata)
    metadata["source_file"] = "changed.csv"

    assert context.metadata["source_file"] == "transactions.csv"


def test_utc_now_iso_contains_utc_information() -> None:
    timestamp = utc_now_iso()

    assert isinstance(timestamp, str)
    assert timestamp.endswith("+00:00")
