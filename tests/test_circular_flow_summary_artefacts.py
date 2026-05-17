"""Tests for circular flow summary and artefact writers."""

import json

from graph_aml.rules import (
    generate_circular_flow_detection_artefacts,
    summarise_circular_flow_detections,
    write_circular_flow_detections_csv,
    write_circular_flow_detections_json,
    write_circular_flow_summary_json,
)
from graph_aml.rules.circular_flow import detect_circular_flows
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_non_trigger_transactions_fixture,
    build_circular_flow_three_hop_transactions_fixture,
)

EXPECTED_SUMMARY_KEYS = {
    "cycle_count",
    "unique_primary_account_count",
    "unique_account_count",
    "min_cycle_length",
    "max_cycle_length",
    "mean_cycle_length",
    "min_time_span_hours",
    "max_time_span_hours",
    "mean_time_span_hours",
    "total_evidence_transaction_count",
    "mean_total_amount",
    "max_total_amount",
}


def test_summary_handles_empty_detections() -> None:
    detections = detect_circular_flows(build_circular_flow_non_trigger_transactions_fixture())

    summary = summarise_circular_flow_detections(detections)

    assert summary["cycle_count"] == 0
    assert summary["unique_account_count"] == 0


def test_summary_includes_expected_keys_and_metrics() -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    summary = summarise_circular_flow_detections(detections)

    assert set(summary) == EXPECTED_SUMMARY_KEYS
    assert summary["cycle_count"] == 1
    assert summary["unique_account_count"] == 3
    assert summary["min_cycle_length"] == 3
    assert summary["max_cycle_length"] == 3
    assert summary["total_evidence_transaction_count"] == 3
    assert summary["max_total_amount"] == 12000.0
    json.dumps(summary)


def test_json_writer_writes_parseable_detection_json(tmp_path) -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    path = write_circular_flow_detections_json(detections, tmp_path / "detections.json")

    assert json.loads(path.read_text(encoding="utf-8"))[0]["cycle_id"]


def test_csv_writer_writes_detection_csv(tmp_path) -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    path = write_circular_flow_detections_csv(detections, tmp_path / "detections.csv")

    assert path.read_text(encoding="utf-8").startswith("cycle_id,")


def test_summary_writer_writes_parseable_summary_json(tmp_path) -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())
    summary = summarise_circular_flow_detections(detections)

    path = write_circular_flow_summary_json(summary, tmp_path / "summary.json")

    assert json.loads(path.read_text(encoding="utf-8"))["cycle_count"] == 1


def test_high_level_artefact_generator_writes_all_expected_artefacts(tmp_path) -> None:
    paths = generate_circular_flow_detection_artefacts(
        build_circular_flow_three_hop_transactions_fixture(),
        tmp_path / "nested" / "artefacts",
    )

    assert set(paths) == {"detections_json", "detections_csv", "summary_json"}
    assert all(path.is_file() for path in paths.values())
    assert (tmp_path / "nested" / "artefacts").is_dir()
