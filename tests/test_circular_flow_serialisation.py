"""Tests for circular flow detection serialisation helpers."""

import json

from graph_aml.rules import (
    CIRCULAR_FLOW_DETECTION_COLUMNS,
    circular_flow_detections_to_dataframe,
    circular_flow_detections_to_dicts,
    detect_circular_flows,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_non_trigger_transactions_fixture,
    build_circular_flow_three_hop_transactions_fixture,
)


def test_detection_dataframe_converts_to_json_serialisable_dicts() -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    payload = circular_flow_detections_to_dicts(detections)

    json.dumps(payload, default=str)
    assert isinstance(payload[0]["cycle_accounts"], list)


def test_serialised_payload_preserves_cycle_accounts_and_evidence_ids() -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    payload = circular_flow_detections_to_dicts(detections)

    assert payload[0]["cycle_accounts"] == ["ACC_CF_A", "ACC_CF_B", "ACC_CF_C"]
    assert payload[0]["evidence_ids"] == [
        "TXN_CF_3HOP_001",
        "TXN_CF_3HOP_002",
        "TXN_CF_3HOP_003",
    ]


def test_dictionary_payload_converts_back_to_dataframe_with_expected_columns() -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())
    payload = circular_flow_detections_to_dicts(detections)

    round_tripped = circular_flow_detections_to_dataframe(payload)

    assert tuple(round_tripped.columns) == CIRCULAR_FLOW_DETECTION_COLUMNS
    assert round_tripped.loc[0, "cycle_accounts"] == ("ACC_CF_A", "ACC_CF_B", "ACC_CF_C")


def test_empty_detections_serialise_and_deserialise_cleanly() -> None:
    detections = detect_circular_flows(build_circular_flow_non_trigger_transactions_fixture())

    payload = circular_flow_detections_to_dicts(detections)
    round_tripped = circular_flow_detections_to_dataframe(payload)

    assert payload == []
    assert round_tripped.empty
    assert tuple(round_tripped.columns) == CIRCULAR_FLOW_DETECTION_COLUMNS


def test_round_trip_conversion_preserves_cycle_ids_and_paths() -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    payload = circular_flow_detections_to_dicts(detections)
    round_tripped = circular_flow_detections_to_dataframe(payload)

    assert round_tripped.loc[0, "cycle_id"] == detections.loc[0, "cycle_id"]
    assert round_tripped.loc[0, "cycle_path"] == detections.loc[0, "cycle_path"]
