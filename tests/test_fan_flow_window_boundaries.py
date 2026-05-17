"""Rolling-window boundary tests for fan-in and fan-out."""

import pandas as pd

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    detect_fan_in_windows,
    detect_fan_out_windows,
)
from tests.fixtures.fan_flow_fixtures import (
    TRANSACTION_COLUMNS,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
)


def test_fan_in_window_start_is_included() -> None:
    output = detect_fan_in_windows(
        _fan_in_window_frame(), FanInRuleConfig(min_unique_senders=3, window_days=1)
    )

    assert "TXN_WINDOW_IN_START" in output.loc[0, "evidence_ids"]


def test_fan_in_window_end_is_included() -> None:
    output = detect_fan_in_windows(
        _fan_in_window_frame(), FanInRuleConfig(min_unique_senders=3, window_days=1)
    )

    assert "TXN_WINDOW_IN_END" in output.loc[0, "evidence_ids"]


def test_fan_in_after_window_end_is_excluded_from_that_window() -> None:
    output = detect_fan_in_windows(
        _fan_in_after_window_frame(), FanInRuleConfig(min_unique_senders=3, window_days=1)
    )

    assert output.empty


def test_fan_out_window_start_is_included() -> None:
    output = detect_fan_out_windows(
        _fan_out_window_frame(), FanOutRuleConfig(min_unique_recipients=3, window_days=1)
    )

    assert "TXN_WINDOW_OUT_START" in output.loc[0, "evidence_ids"]


def test_fan_out_window_end_is_included() -> None:
    output = detect_fan_out_windows(
        _fan_out_window_frame(), FanOutRuleConfig(min_unique_recipients=3, window_days=1)
    )

    assert "TXN_WINDOW_OUT_END" in output.loc[0, "evidence_ids"]


def test_fan_out_after_window_end_is_excluded_from_that_window() -> None:
    output = detect_fan_out_windows(
        _fan_out_after_window_frame(), FanOutRuleConfig(min_unique_recipients=3, window_days=1)
    )

    assert output.empty


def test_later_valid_fan_in_window_can_trigger_when_earliest_does_not() -> None:
    output = detect_fan_in_windows(
        _later_fan_in_window_frame(), FanInRuleConfig(min_unique_senders=3, window_days=1)
    )

    assert output.loc[0, "detection_window_start"].startswith("2025-02-18T09:01:00")


def test_later_valid_fan_out_window_can_trigger_when_earliest_does_not() -> None:
    output = detect_fan_out_windows(
        _later_fan_out_window_frame(), FanOutRuleConfig(min_unique_recipients=3, window_days=1)
    )

    assert output.loc[0, "detection_window_start"].startswith("2025-02-19T09:01:00")


def test_detection_windows_are_populated_for_both_rules() -> None:
    fan_in = detect_fan_in_windows(
        build_fan_in_only_transactions_fixture(), FanInRuleConfig(min_unique_senders=4)
    )
    fan_out = detect_fan_out_windows(
        build_fan_out_only_transactions_fixture(), FanOutRuleConfig(min_unique_recipients=4)
    )

    assert fan_in.loc[0, "detection_window_start"]
    assert fan_in.loc[0, "detection_window_end"]
    assert fan_out.loc[0, "detection_window_start"]
    assert fan_out.loc[0, "detection_window_end"]


def test_evidence_ids_are_deterministic_for_both_rules() -> None:
    fan_in_first = detect_fan_in_windows(
        build_fan_in_only_transactions_fixture(), FanInRuleConfig(min_unique_senders=4)
    )
    fan_in_second = detect_fan_in_windows(
        build_fan_in_only_transactions_fixture(), FanInRuleConfig(min_unique_senders=4)
    )
    fan_out_first = detect_fan_out_windows(
        build_fan_out_only_transactions_fixture(), FanOutRuleConfig(min_unique_recipients=4)
    )
    fan_out_second = detect_fan_out_windows(
        build_fan_out_only_transactions_fixture(), FanOutRuleConfig(min_unique_recipients=4)
    )

    assert fan_in_first.loc[0, "evidence_ids"] == fan_in_second.loc[0, "evidence_ids"]
    assert fan_out_first.loc[0, "evidence_ids"] == fan_out_second.loc[0, "evidence_ids"]


def _fan_in_window_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-17 09:00:00", tz="UTC")
    return pd.DataFrame(
        [
            _row("TXN_WINDOW_IN_START", "ACC_FLOW_SENDER_001", "ACC_COLLECT_001", None, start),
            _row(
                "TXN_WINDOW_IN_MID",
                "ACC_FLOW_SENDER_002",
                "ACC_COLLECT_001",
                None,
                start + pd.Timedelta(hours=12),
            ),
            _row(
                "TXN_WINDOW_IN_END",
                "ACC_FLOW_SENDER_003",
                "ACC_COLLECT_001",
                None,
                start + pd.Timedelta(days=1),
            ),
        ],
        columns=TRANSACTION_COLUMNS,
    )


def _fan_in_after_window_frame() -> pd.DataFrame:
    frame = _fan_in_window_frame()
    frame.loc[2, "transaction_timestamp"] = pd.Timestamp("2025-02-18 09:01:00", tz="UTC")
    return frame


def _fan_out_window_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-17 09:00:00", tz="UTC")
    return pd.DataFrame(
        [
            _row("TXN_WINDOW_OUT_START", "ACC_DISPERSE_001", "ACC_FLOW_RECEIVER_001", None, start),
            _row(
                "TXN_WINDOW_OUT_MID",
                "ACC_DISPERSE_001",
                "ACC_FLOW_RECEIVER_002",
                None,
                start + pd.Timedelta(hours=12),
            ),
            _row(
                "TXN_WINDOW_OUT_END",
                "ACC_DISPERSE_001",
                "ACC_FLOW_RECEIVER_003",
                None,
                start + pd.Timedelta(days=1),
            ),
        ],
        columns=TRANSACTION_COLUMNS,
    )


def _fan_out_after_window_frame() -> pd.DataFrame:
    frame = _fan_out_window_frame()
    frame.loc[2, "transaction_timestamp"] = pd.Timestamp("2025-02-18 09:01:00", tz="UTC")
    return frame


def _later_fan_in_window_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-17 09:00:00", tz="UTC")
    return pd.DataFrame(
        [
            _row("TXN_LATER_IN_EARLY", "ACC_FLOW_SENDER_001", "ACC_COLLECT_001", None, start),
            _row(
                "TXN_LATER_IN_001",
                "ACC_FLOW_SENDER_002",
                "ACC_COLLECT_001",
                None,
                start + pd.Timedelta(days=1, minutes=1),
            ),
            _row(
                "TXN_LATER_IN_002",
                "ACC_FLOW_SENDER_003",
                "ACC_COLLECT_001",
                None,
                start + pd.Timedelta(days=1, minutes=2),
            ),
            _row(
                "TXN_LATER_IN_003",
                "ACC_FLOW_SENDER_004",
                "ACC_COLLECT_001",
                None,
                start + pd.Timedelta(days=1, minutes=3),
            ),
        ],
        columns=TRANSACTION_COLUMNS,
    )


def _later_fan_out_window_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-18 09:00:00", tz="UTC")
    return pd.DataFrame(
        [
            _row("TXN_LATER_OUT_EARLY", "ACC_DISPERSE_001", "ACC_FLOW_RECEIVER_001", None, start),
            _row(
                "TXN_LATER_OUT_001",
                "ACC_DISPERSE_001",
                "ACC_FLOW_RECEIVER_002",
                None,
                start + pd.Timedelta(days=1, minutes=1),
            ),
            _row(
                "TXN_LATER_OUT_002",
                "ACC_DISPERSE_001",
                "ACC_FLOW_RECEIVER_003",
                None,
                start + pd.Timedelta(days=1, minutes=2),
            ),
            _row(
                "TXN_LATER_OUT_003",
                "ACC_DISPERSE_001",
                "ACC_FLOW_RECEIVER_004",
                None,
                start + pd.Timedelta(days=1, minutes=3),
            ),
        ],
        columns=TRANSACTION_COLUMNS,
    )


def _row(
    transaction_id: str,
    sender_account_id: str,
    receiver_account_id: str | None,
    counterparty_id: str | None,
    timestamp: object,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender_account_id,
        "receiver_account_id": receiver_account_id,
        "counterparty_id": counterparty_id,
        "device_id": "DEV_WINDOW",
        "transaction_timestamp": timestamp,
        "amount": 500.0,
        "currency": "USD",
        "transaction_type": "transfer",
        "channel": "online",
        "origin_country": "US",
        "destination_country": "US",
        "is_cross_border": False,
        "is_labelled_suspicious": True,
        "typology_label": None,
        "source_file": "fan_flow_window_test",
    }
