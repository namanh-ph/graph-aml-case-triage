"""Tests for fan-in rolling-window detection."""

import pandas as pd

from graph_aml.rules import FanInRuleConfig, detect_fan_in_windows
from tests.fixtures.fan_in_fixtures import (
    build_fan_in_multi_receiver_transactions_fixture,
    build_fan_in_non_trigger_transactions_fixture,
    build_fan_in_overlapping_window_transactions_fixture,
    build_fan_in_trigger_transactions_fixture,
)


def test_detection_returns_empty_output_when_no_candidates_exist() -> None:
    output = detect_fan_in_windows(build_fan_in_non_trigger_transactions_fixture())

    assert output.empty


def test_detection_triggers_with_configured_unique_senders_inside_window() -> None:
    output = detect_fan_in_windows(build_fan_in_trigger_transactions_fixture())

    assert output.loc[0, "unique_sender_count"] == 15


def test_detection_does_not_trigger_when_unique_sender_count_below_threshold() -> None:
    output = detect_fan_in_windows(
        build_fan_in_trigger_transactions_fixture(unique_sender_count=14)
    )

    assert output.empty


def test_detection_does_not_trigger_when_transactions_are_outside_window() -> None:
    frame = build_fan_in_trigger_transactions_fixture()
    start = pd.Timestamp("2025-01-15 09:00:00", tz="UTC")
    frame["transaction_timestamp"] = [
        start + pd.Timedelta(days=index * 8) for index in range(len(frame))
    ]

    assert detect_fan_in_windows(frame).empty


def test_detection_does_not_trigger_when_total_amount_below_minimum() -> None:
    config = FanInRuleConfig(min_total_amount=10000)

    assert detect_fan_in_windows(build_fan_in_trigger_transactions_fixture(), config).empty


def test_detection_evidence_ids_include_all_transactions_in_detected_window() -> None:
    output = detect_fan_in_windows(build_fan_in_trigger_transactions_fixture())

    assert output.loc[0, "evidence_ids"] == tuple(
        f"TXN_FAN_IN_TRIGGER_{index:03d}" for index in range(1, 16)
    )


def test_detection_sender_ids_include_all_unique_senders() -> None:
    output = detect_fan_in_windows(build_fan_in_trigger_transactions_fixture())

    assert len(output.loc[0, "sender_ids"]) == 15


def test_detection_includes_total_minimum_and_maximum_amounts() -> None:
    frame = build_fan_in_trigger_transactions_fixture()
    frame.loc[0, "amount"] = 750

    output = detect_fan_in_windows(frame)

    assert output.loc[0, "total_amount"] == 7750.0
    assert output.loc[0, "min_amount"] == 500.0
    assert output.loc[0, "max_amount"] == 750.0


def test_overlapping_windows_are_deduplicated_deterministically() -> None:
    output = detect_fan_in_windows(build_fan_in_overlapping_window_transactions_fixture())

    assert len(output) == 1
    assert output.loc[0, "unique_sender_count"] == 16


def test_multiple_receiving_accounts_can_produce_separate_detections() -> None:
    output = detect_fan_in_windows(build_fan_in_multi_receiver_transactions_fixture())

    assert output["account_id"].tolist() == ["ACC_COLLECT_001", "ACC_COLLECT_002"]


def test_detection_output_ordering_is_deterministic() -> None:
    frame = build_fan_in_multi_receiver_transactions_fixture().sample(frac=1, random_state=9)

    output = detect_fan_in_windows(frame)

    assert output["account_id"].tolist() == ["ACC_COLLECT_001", "ACC_COLLECT_002"]
