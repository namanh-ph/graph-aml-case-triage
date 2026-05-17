"""Tests for fan-out rolling-window detection."""

import pandas as pd

from graph_aml.rules import FanOutRuleConfig, detect_fan_out_windows
from tests.fixtures.fan_out_fixtures import (
    build_fan_out_multi_sender_transactions_fixture,
    build_fan_out_non_trigger_transactions_fixture,
    build_fan_out_overlapping_window_transactions_fixture,
    build_fan_out_trigger_transactions_fixture,
)


def test_detection_returns_empty_output_when_no_candidates_exist() -> None:
    output = detect_fan_out_windows(build_fan_out_non_trigger_transactions_fixture())

    assert output.empty


def test_detection_triggers_with_configured_unique_recipients_inside_window() -> None:
    output = detect_fan_out_windows(build_fan_out_trigger_transactions_fixture())

    assert output.loc[0, "unique_recipient_count"] == 20


def test_detection_does_not_trigger_when_unique_recipient_count_below_threshold() -> None:
    output = detect_fan_out_windows(
        build_fan_out_trigger_transactions_fixture(unique_recipient_count=19)
    )

    assert output.empty


def test_repeated_transfers_to_same_recipient_do_not_inflate_unique_recipient_count() -> None:
    frame = build_fan_out_trigger_transactions_fixture()
    frame["receiver_account_id"] = "ACC_FAN_RECIPIENT_001"

    assert detect_fan_out_windows(frame).empty


def test_detection_does_not_trigger_when_transactions_are_outside_window() -> None:
    frame = build_fan_out_trigger_transactions_fixture()
    start = pd.Timestamp("2025-01-20 09:00:00", tz="UTC")
    frame["transaction_timestamp"] = [
        start + pd.Timedelta(days=index * 8) for index in range(len(frame))
    ]

    assert detect_fan_out_windows(frame).empty


def test_detection_does_not_trigger_when_total_amount_below_minimum() -> None:
    config = FanOutRuleConfig(min_total_amount=15000)

    assert detect_fan_out_windows(build_fan_out_trigger_transactions_fixture(), config).empty


def test_detection_evidence_ids_include_all_transactions_in_detected_window() -> None:
    output = detect_fan_out_windows(build_fan_out_trigger_transactions_fixture())

    assert output.loc[0, "evidence_ids"] == tuple(
        f"TXN_FAN_OUT_TRIGGER_{index:03d}" for index in range(1, 21)
    )


def test_detection_recipient_ids_include_all_unique_recipients() -> None:
    output = detect_fan_out_windows(build_fan_out_trigger_transactions_fixture())

    assert len(output.loc[0, "recipient_ids"]) == 20


def test_detection_includes_total_minimum_and_maximum_amounts() -> None:
    frame = build_fan_out_trigger_transactions_fixture()
    frame.loc[0, "amount"] = 750

    output = detect_fan_out_windows(frame)

    assert output.loc[0, "total_amount"] == 10250.0
    assert output.loc[0, "min_amount"] == 500.0
    assert output.loc[0, "max_amount"] == 750.0


def test_overlapping_windows_are_deduplicated_deterministically() -> None:
    output = detect_fan_out_windows(build_fan_out_overlapping_window_transactions_fixture())

    assert len(output) == 1
    assert output.loc[0, "unique_recipient_count"] == 21


def test_multiple_sending_accounts_can_produce_separate_detections() -> None:
    output = detect_fan_out_windows(build_fan_out_multi_sender_transactions_fixture())

    assert output["account_id"].tolist() == ["ACC_DISPERSE_001", "ACC_DISPERSE_002"]


def test_detection_output_ordering_is_deterministic() -> None:
    frame = build_fan_out_multi_sender_transactions_fixture().sample(frac=1, random_state=9)

    output = detect_fan_out_windows(frame)

    assert output["account_id"].tolist() == ["ACC_DISPERSE_001", "ACC_DISPERSE_002"]
