"""Fixture-based rolling-window edge tests for structuring detections."""

import pandas as pd

from graph_aml.rules import StructuringRuleConfig, detect_structuring_windows
from tests.fixtures.structuring_fixtures import (
    build_structuring_overlapping_window_transactions_fixture,
)


def _window_frame(offsets: list[pd.Timedelta], amounts: list[float] | None = None) -> pd.DataFrame:
    start = pd.Timestamp("2025-01-20 09:00:00", tz="UTC")
    values = [9500.0] * len(offsets) if amounts is None else amounts
    return pd.DataFrame(
        [
            {
                "transaction_id": f"TXN_WINDOW_{index:03d}",
                "sender_account_id": "ACC_STRUCT_001",
                "receiver_account_id": "ACC_INTERNAL_001",
                "counterparty_id": None,
                "transaction_timestamp": start + offset,
                "amount": amount,
                "transaction_type": "wire",
            }
            for index, (offset, amount) in enumerate(zip(offsets, values, strict=True), start=1)
        ]
    )


def test_transactions_exactly_at_window_start_are_included() -> None:
    config = StructuringRuleConfig(min_transaction_count=3, window_hours=2)

    detection = detect_structuring_windows(
        _window_frame([pd.Timedelta(hours=0), pd.Timedelta(hours=1), pd.Timedelta(hours=2)]),
        config,
    )

    assert "TXN_WINDOW_001" in detection.loc[0, "evidence_ids"]


def test_transactions_exactly_at_window_end_are_included() -> None:
    config = StructuringRuleConfig(min_transaction_count=3, window_hours=2)

    detection = detect_structuring_windows(
        _window_frame([pd.Timedelta(hours=0), pd.Timedelta(hours=1), pd.Timedelta(hours=2)]),
        config,
    )

    assert "TXN_WINDOW_003" in detection.loc[0, "evidence_ids"]


def test_transactions_just_after_window_end_are_excluded_from_that_window() -> None:
    config = StructuringRuleConfig(min_transaction_count=3, window_hours=2)

    detection = detect_structuring_windows(
        _window_frame(
            [
                pd.Timedelta(hours=0),
                pd.Timedelta(hours=1),
                pd.Timedelta(hours=2),
                pd.Timedelta(hours=2, seconds=1),
            ]
        ),
        config,
    )

    assert detection.loc[0, "evidence_ids"] == (
        "TXN_WINDOW_001",
        "TXN_WINDOW_002",
        "TXN_WINDOW_003",
    )


def test_later_valid_window_can_trigger_when_earliest_window_does_not() -> None:
    config = StructuringRuleConfig(min_transaction_count=3, window_hours=2)

    detection = detect_structuring_windows(
        _window_frame(
            [
                pd.Timedelta(hours=0),
                pd.Timedelta(hours=10),
                pd.Timedelta(hours=11),
                pd.Timedelta(hours=12),
            ]
        ),
        config,
    )

    assert detection.loc[0, "evidence_ids"] == (
        "TXN_WINDOW_002",
        "TXN_WINDOW_003",
        "TXN_WINDOW_004",
    )


def test_overlapping_windows_are_deduplicated_deterministically() -> None:
    detection = detect_structuring_windows(
        build_structuring_overlapping_window_transactions_fixture()
    )

    assert len(detection) == 1


def test_strongest_overlapping_window_selected_by_highest_transaction_count() -> None:
    detection = detect_structuring_windows(
        build_structuring_overlapping_window_transactions_fixture()
    )

    assert detection.loc[0, "transaction_count"] == 9


def test_tied_transaction_counts_select_highest_total_amount() -> None:
    config = StructuringRuleConfig(min_transaction_count=3, window_hours=2)

    detection = detect_structuring_windows(
        _window_frame(
            [
                pd.Timedelta(hours=0),
                pd.Timedelta(hours=1),
                pd.Timedelta(hours=2),
                pd.Timedelta(hours=3),
            ],
            amounts=[9000.0, 9000.0, 9000.0, 9999.0],
        ),
        config,
    )

    assert detection.loc[0, "detection_window_start"].startswith("2025-01-20T10:00:00")


def test_tied_count_and_total_amount_select_earliest_window() -> None:
    config = StructuringRuleConfig(min_transaction_count=3, window_hours=2)

    detection = detect_structuring_windows(
        _window_frame(
            [
                pd.Timedelta(hours=0),
                pd.Timedelta(hours=1),
                pd.Timedelta(hours=2),
                pd.Timedelta(hours=3),
            ]
        ),
        config,
    )

    assert detection.loc[0, "detection_window_start"].startswith("2025-01-20T09:00:00")


def test_detection_output_contains_window_start_and_end() -> None:
    detection = detect_structuring_windows(
        build_structuring_overlapping_window_transactions_fixture()
    )

    assert detection.loc[0, "detection_window_start"]
    assert detection.loc[0, "detection_window_end"]


def test_detection_output_evidence_ids_are_deterministic() -> None:
    detection = detect_structuring_windows(
        build_structuring_overlapping_window_transactions_fixture()
    )

    assert detection.loc[0, "evidence_ids"] == tuple(
        f"TXN_STRUCT_OVERLAP_{index:03d}" for index in range(1, 10)
    )
