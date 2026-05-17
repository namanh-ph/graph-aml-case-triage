"""Tests for rolling structuring window detection."""

import pandas as pd

from graph_aml.rules import StructuringRuleConfig, detect_structuring_windows


def _transactions(
    account_id: str = "ACC_1",
    count: int = 3,
    hour_step: int = 1,
    amount: float = 9500.0,
) -> pd.DataFrame:
    rows = []
    start = pd.Timestamp("2025-01-01T00:00:00Z")
    for index in range(count):
        rows.append(
            {
                "transaction_id": f"{account_id}_TXN_{index}",
                "sender_account_id": account_id,
                "receiver_account_id": "ACC_TARGET",
                "counterparty_id": None,
                "transaction_timestamp": start + pd.Timedelta(hours=index * hour_step),
                "amount": amount,
                "transaction_type": "transfer",
            }
        )
    return pd.DataFrame(rows)


def _config() -> StructuringRuleConfig:
    return StructuringRuleConfig(min_transaction_count=3, window_hours=3)


def test_detection_returns_empty_output_when_no_candidates_exist() -> None:
    frame = _transactions(amount=100)

    output = detect_structuring_windows(frame, _config())

    assert output.empty
    assert tuple(output.columns) == (
        "account_id",
        "detection_window_start",
        "detection_window_end",
        "transaction_count",
        "total_amount",
        "min_amount",
        "max_amount",
        "evidence_ids",
    )


def test_detection_triggers_with_configured_count_inside_window() -> None:
    output = detect_structuring_windows(_transactions(), _config())

    assert output.loc[0, "transaction_count"] == 3


def test_detection_does_not_trigger_when_transactions_are_outside_window() -> None:
    output = detect_structuring_windows(_transactions(hour_step=5), _config())

    assert output.empty


def test_detection_does_not_trigger_when_transaction_count_is_below_threshold() -> None:
    output = detect_structuring_windows(_transactions(count=2), _config())

    assert output.empty


def test_detection_evidence_ids_include_all_transactions_in_detected_window() -> None:
    output = detect_structuring_windows(_transactions(), _config())

    assert output.loc[0, "evidence_ids"] == ("ACC_1_TXN_0", "ACC_1_TXN_1", "ACC_1_TXN_2")


def test_detection_includes_total_minimum_and_maximum_amounts() -> None:
    frame = _transactions()
    frame.loc[1, "amount"] = 9600

    output = detect_structuring_windows(frame, _config())

    assert output.loc[0, "total_amount"] == 28600.0
    assert output.loc[0, "min_amount"] == 9500.0
    assert output.loc[0, "max_amount"] == 9600.0


def test_overlapping_windows_are_deduplicated_deterministically() -> None:
    output = detect_structuring_windows(_transactions(count=4), _config())

    assert len(output) == 1
    assert output.loc[0, "transaction_count"] == 4


def test_multiple_accounts_can_produce_separate_detections() -> None:
    frame = pd.concat(
        [_transactions("ACC_1"), _transactions("ACC_2")],
        ignore_index=True,
    )

    output = detect_structuring_windows(frame, _config())

    assert output["account_id"].tolist() == ["ACC_1", "ACC_2"]


def test_detection_output_ordering_is_deterministic() -> None:
    frame = pd.concat(
        [_transactions("ACC_2"), _transactions("ACC_1")],
        ignore_index=True,
    )

    output = detect_structuring_windows(frame, _config())

    assert output["account_id"].tolist() == ["ACC_1", "ACC_2"]
