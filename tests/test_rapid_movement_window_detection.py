"""Tests for rapid movement window detection."""

import pandas as pd

from graph_aml.rules import RapidMovementRuleConfig, detect_rapid_movement_windows
from tests.fixtures.rapid_movement_fixtures import (
    build_rapid_movement_multi_account_transactions_fixture,
    build_rapid_movement_non_trigger_transactions_fixture,
    build_rapid_movement_overlapping_window_transactions_fixture,
    build_rapid_movement_trigger_transactions_fixture,
)


def test_detection_returns_empty_output_when_no_inbound_transactions_exist() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame["receiver_account_id"] = None

    assert detect_rapid_movement_windows(frame).empty


def test_detection_returns_empty_output_when_no_outbound_transactions_exist() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "transaction_type"] = "card"

    assert detect_rapid_movement_windows(frame).empty


def test_detection_triggers_when_configured_outflow_ratio_is_met() -> None:
    output = detect_rapid_movement_windows(build_rapid_movement_trigger_transactions_fixture())

    assert output.loc[0, "outflow_ratio"] == 0.9


def test_detection_does_not_trigger_when_outflow_ratio_below_threshold() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture(sent_amount=8999.0)

    assert detect_rapid_movement_windows(frame).empty


def test_detection_does_not_trigger_when_retained_ratio_above_maximum() -> None:
    config = RapidMovementRuleConfig(min_outflow_ratio=0.8, max_retained_ratio=0.1)
    frame = build_rapid_movement_trigger_transactions_fixture(sent_amount=8500.0)

    assert detect_rapid_movement_windows(frame, config).empty


def test_detection_does_not_trigger_when_total_received_below_minimum() -> None:
    config = RapidMovementRuleConfig(min_total_received=11000.0)

    assert detect_rapid_movement_windows(
        build_rapid_movement_trigger_transactions_fixture(),
        config,
    ).empty


def test_detection_does_not_trigger_when_outgoing_count_below_threshold() -> None:
    config = RapidMovementRuleConfig(min_outgoing_transaction_count=2)

    assert detect_rapid_movement_windows(
        build_rapid_movement_trigger_transactions_fixture(),
        config,
    ).empty


def test_outbound_transactions_exactly_at_window_start_are_included() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "transaction_timestamp"] = frame.loc[0, "transaction_timestamp"]

    output = detect_rapid_movement_windows(frame)

    assert output.loc[0, "outbound_evidence_ids"] == ("TXN_RM_OUT_001",)


def test_outbound_transactions_exactly_at_window_end_are_included() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "transaction_timestamp"] = pd.Timestamp("2025-01-27 09:00:00", tz="UTC")

    output = detect_rapid_movement_windows(frame)

    assert output.loc[0, "outbound_evidence_ids"] == ("TXN_RM_OUT_001",)


def test_outbound_transactions_just_after_window_are_excluded() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "transaction_timestamp"] = pd.Timestamp(
        "2025-01-27 09:00:01",
        tz="UTC",
    )

    assert detect_rapid_movement_windows(frame).empty


def test_evidence_ids_include_inbound_then_outbound_ids() -> None:
    output = detect_rapid_movement_windows(build_rapid_movement_trigger_transactions_fixture())

    assert output.loc[0, "evidence_ids"] == ("TXN_RM_IN_001", "TXN_RM_OUT_001")


def test_detection_includes_value_and_ratio_fields() -> None:
    output = detect_rapid_movement_windows(build_rapid_movement_trigger_transactions_fixture())

    assert output.loc[0, "total_received"] == 10000.0
    assert output.loc[0, "total_sent_out"] == 9000.0
    assert output.loc[0, "retained_amount"] == 1000.0
    assert output.loc[0, "retained_ratio"] == 0.1


def test_overlapping_windows_are_deduplicated_deterministically() -> None:
    output = detect_rapid_movement_windows(
        build_rapid_movement_overlapping_window_transactions_fixture()
    )

    assert len(output) == 1
    assert output.loc[0, "outflow_ratio"] == 1.92


def test_multiple_accounts_can_produce_separate_detections() -> None:
    output = detect_rapid_movement_windows(
        build_rapid_movement_multi_account_transactions_fixture()
    )

    assert output["account_id"].tolist() == ["ACC_PASS_001", "ACC_PASS_002"]


def test_detection_output_ordering_is_deterministic() -> None:
    frame = build_rapid_movement_multi_account_transactions_fixture().sample(
        frac=1,
        random_state=9,
    )

    output = detect_rapid_movement_windows(frame)

    assert output["account_id"].tolist() == ["ACC_PASS_001", "ACC_PASS_002"]


def test_detection_returns_empty_for_benign_fixture() -> None:
    assert detect_rapid_movement_windows(
        build_rapid_movement_non_trigger_transactions_fixture()
    ).empty
