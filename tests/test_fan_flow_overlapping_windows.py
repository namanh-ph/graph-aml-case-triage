"""Overlapping-window selection tests for fan-in and fan-out."""

import pandas as pd

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    detect_fan_in_windows,
    detect_fan_out_windows,
)
from tests.fixtures.fan_flow_fixtures import (
    TRANSACTION_COLUMNS,
    build_fan_flow_overlapping_window_transactions_fixture,
)


def test_fan_in_overlapping_windows_are_deduplicated() -> None:
    output = detect_fan_in_windows(
        build_fan_flow_overlapping_window_transactions_fixture(),
        FanInRuleConfig(min_unique_senders=4),
    )

    assert len(output[output["account_id"].eq("ACC_COLLECT_001")]) == 1


def test_fan_in_strongest_window_prioritises_highest_unique_sender_count() -> None:
    output = detect_fan_in_windows(
        build_fan_flow_overlapping_window_transactions_fixture(),
        FanInRuleConfig(min_unique_senders=4),
    )

    assert output.loc[0, "unique_sender_count"] == 5


def test_fan_in_ties_prioritise_highest_transaction_count() -> None:
    output = detect_fan_in_windows(
        _fan_in_transaction_count_tie_frame(), FanInRuleConfig(min_unique_senders=4, window_days=1)
    )

    assert output.loc[0, "transaction_count"] == 5
    assert output.loc[0, "detection_window_start"].startswith("2025-02-20T10:00:00")


def test_fan_in_remaining_ties_prioritise_highest_total_amount() -> None:
    output = detect_fan_in_windows(
        _fan_in_total_amount_tie_frame(), FanInRuleConfig(min_unique_senders=4, window_days=1)
    )

    assert output.loc[0, "total_amount"] == 3500.0
    assert output.loc[0, "detection_window_start"].startswith("2025-02-21T10:00:00")


def test_fan_in_final_ties_prioritise_earliest_start() -> None:
    output = detect_fan_in_windows(
        _fan_in_earliest_tie_frame(), FanInRuleConfig(min_unique_senders=4, window_days=1)
    )

    assert output.loc[0, "detection_window_start"].startswith("2025-02-22T09:00:00")


def test_fan_out_overlapping_windows_are_deduplicated() -> None:
    output = detect_fan_out_windows(
        build_fan_flow_overlapping_window_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )

    assert len(output[output["account_id"].eq("ACC_DISPERSE_001")]) == 1


def test_fan_out_strongest_window_prioritises_highest_unique_recipient_count() -> None:
    output = detect_fan_out_windows(
        build_fan_flow_overlapping_window_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )

    assert output.loc[0, "unique_recipient_count"] == 5


def test_fan_out_ties_prioritise_highest_transaction_count() -> None:
    output = detect_fan_out_windows(
        _fan_out_transaction_count_tie_frame(),
        FanOutRuleConfig(min_unique_recipients=4, window_days=1),
    )

    assert output.loc[0, "transaction_count"] == 5
    assert output.loc[0, "detection_window_start"].startswith("2025-02-23T10:00:00")


def test_fan_out_remaining_ties_prioritise_highest_total_amount() -> None:
    output = detect_fan_out_windows(
        _fan_out_total_amount_tie_frame(), FanOutRuleConfig(min_unique_recipients=4, window_days=1)
    )

    assert output.loc[0, "total_amount"] == 3500.0
    assert output.loc[0, "detection_window_start"].startswith("2025-02-24T10:00:00")


def test_fan_out_final_ties_prioritise_earliest_start() -> None:
    output = detect_fan_out_windows(
        _fan_out_earliest_tie_frame(), FanOutRuleConfig(min_unique_recipients=4, window_days=1)
    )

    assert output.loc[0, "detection_window_start"].startswith("2025-02-25T09:00:00")


def _fan_in_transaction_count_tie_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-20 09:00:00", tz="UTC")
    rows = _fan_in_base_rows(start)
    rows.extend(
        [
            _row(
                "TXN_TIE_IN_COUNT_005",
                "ACC_FLOW_SENDER_005",
                "ACC_COLLECT_001",
                None,
                start + pd.Timedelta(hours=24, minutes=30),
            ),
            _row(
                "TXN_TIE_IN_COUNT_006",
                "ACC_FLOW_SENDER_005",
                "ACC_COLLECT_001",
                None,
                start + pd.Timedelta(hours=24, minutes=40),
            ),
        ]
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def _fan_in_total_amount_tie_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-21 09:00:00", tz="UTC")
    rows = _fan_in_base_rows(start)
    rows.append(
        _row(
            "TXN_TIE_IN_AMOUNT_005",
            "ACC_FLOW_SENDER_005",
            "ACC_COLLECT_001",
            None,
            start + pd.Timedelta(hours=24, minutes=30),
            amount=2000.0,
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def _fan_in_earliest_tie_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-22 09:00:00", tz="UTC")
    rows = _fan_in_base_rows(start)
    rows.append(
        _row(
            "TXN_TIE_IN_EARLY_005",
            "ACC_FLOW_SENDER_001",
            "ACC_COLLECT_001",
            None,
            start + pd.Timedelta(hours=24, minutes=30),
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def _fan_out_transaction_count_tie_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-23 09:00:00", tz="UTC")
    rows = _fan_out_base_rows(start)
    rows.extend(
        [
            _row(
                "TXN_TIE_OUT_COUNT_005",
                "ACC_DISPERSE_001",
                "ACC_FLOW_RECEIVER_005",
                None,
                start + pd.Timedelta(hours=24, minutes=30),
            ),
            _row(
                "TXN_TIE_OUT_COUNT_006",
                "ACC_DISPERSE_001",
                "ACC_FLOW_RECEIVER_005",
                None,
                start + pd.Timedelta(hours=24, minutes=40),
            ),
        ]
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def _fan_out_total_amount_tie_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-24 09:00:00", tz="UTC")
    rows = _fan_out_base_rows(start)
    rows.append(
        _row(
            "TXN_TIE_OUT_AMOUNT_005",
            "ACC_DISPERSE_001",
            "ACC_FLOW_RECEIVER_005",
            None,
            start + pd.Timedelta(hours=24, minutes=30),
            amount=2000.0,
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def _fan_out_earliest_tie_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-02-25 09:00:00", tz="UTC")
    rows = _fan_out_base_rows(start)
    rows.append(
        _row(
            "TXN_TIE_OUT_EARLY_005",
            "ACC_DISPERSE_001",
            "ACC_FLOW_RECEIVER_001",
            None,
            start + pd.Timedelta(hours=24, minutes=30),
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def _fan_in_base_rows(start: pd.Timestamp) -> list[dict[str, object]]:
    return [
        _row(
            f"TXN_TIE_IN_BASE_{index:03d}",
            f"ACC_FLOW_SENDER_{index:03d}",
            "ACC_COLLECT_001",
            None,
            start + pd.Timedelta(hours=index - 1),
        )
        for index in range(1, 5)
    ]


def _fan_out_base_rows(start: pd.Timestamp) -> list[dict[str, object]]:
    return [
        _row(
            f"TXN_TIE_OUT_BASE_{index:03d}",
            "ACC_DISPERSE_001",
            f"ACC_FLOW_RECEIVER_{index:03d}",
            None,
            start + pd.Timedelta(hours=index - 1),
        )
        for index in range(1, 5)
    ]


def _row(
    transaction_id: str,
    sender_account_id: str,
    receiver_account_id: str | None,
    counterparty_id: str | None,
    timestamp: object,
    amount: float = 500.0,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender_account_id,
        "receiver_account_id": receiver_account_id,
        "counterparty_id": counterparty_id,
        "device_id": "DEV_OVERLAP",
        "transaction_timestamp": timestamp,
        "amount": amount,
        "currency": "USD",
        "transaction_type": "transfer",
        "channel": "online",
        "origin_country": "US",
        "destination_country": "US",
        "is_cross_border": False,
        "is_labelled_suspicious": True,
        "typology_label": None,
        "source_file": "fan_flow_overlap_test",
    }
