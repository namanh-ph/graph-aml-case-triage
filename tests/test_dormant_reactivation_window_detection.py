"""Tests for dormant reactivation window detection."""

import pandas as pd

from graph_aml.rules import (
    DormantReactivationRuleConfig,
    detect_dormant_reactivation_windows,
)
from tests.fixtures.dormant_reactivation_fixtures import (
    TRANSACTION_COLUMNS,
    build_dormant_reactivation_multi_account_transactions_fixture,
    build_dormant_reactivation_overlapping_window_transactions_fixture,
    build_dormant_reactivation_trigger_transactions_fixture,
)


def test_detection_returns_empty_output_when_no_prior_activity_exists() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture().iloc[[1]]

    assert detect_dormant_reactivation_windows(frame).empty


def test_detection_returns_empty_when_dormancy_period_below_threshold() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture(
        prior_timestamp="2025-01-01 09:00:00"
    )

    assert detect_dormant_reactivation_windows(frame).empty


def test_detection_triggers_when_dormant_period_and_outbound_activity_qualify() -> None:
    output = detect_dormant_reactivation_windows(
        build_dormant_reactivation_trigger_transactions_fixture()
    )

    assert output.loc[0, "account_id"] == "ACC_DORMANT_001"


def test_detection_does_not_trigger_when_total_outbound_below_threshold() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture(outbound_amount=9000.0)

    assert detect_dormant_reactivation_windows(frame).empty


def test_detection_does_not_trigger_when_outbound_transaction_count_below_threshold() -> None:
    config = DormantReactivationRuleConfig(min_outbound_transaction_count=2)

    assert detect_dormant_reactivation_windows(
        build_dormant_reactivation_trigger_transactions_fixture(),
        config,
    ).empty


def test_detection_respects_reactivation_window() -> None:
    frame = _with_second_reactivation("2025-01-20 09:00:00")
    config = DormantReactivationRuleConfig(
        min_outbound_amount=1000,
        min_total_outbound_amount=10000,
    )

    output = detect_dormant_reactivation_windows(frame, config)

    assert output.loc[0, "reactivation_evidence_ids"] == ("TXN_DR_REACT_001",)


def test_reactivation_transactions_exactly_at_window_start_are_included() -> None:
    output = detect_dormant_reactivation_windows(
        build_dormant_reactivation_trigger_transactions_fixture()
    )

    assert output.loc[0, "reactivation_evidence_ids"] == ("TXN_DR_REACT_001",)


def test_reactivation_transactions_exactly_at_window_end_are_included() -> None:
    frame = _with_second_reactivation("2025-01-17 09:00:00")
    config = DormantReactivationRuleConfig(
        min_outbound_amount=1000,
        min_outbound_transaction_count=2,
    )

    output = detect_dormant_reactivation_windows(frame, config)

    assert output.loc[0, "reactivation_evidence_ids"] == (
        "TXN_DR_REACT_001",
        "TXN_DR_REACT_002",
    )


def test_reactivation_transactions_just_after_window_are_excluded() -> None:
    frame = _with_second_reactivation("2025-01-17 09:00:01")
    config = DormantReactivationRuleConfig(
        min_outbound_amount=1000,
        min_outbound_transaction_count=2,
    )

    assert detect_dormant_reactivation_windows(frame, config).empty


def test_evidence_ids_include_prior_activity_followed_by_reactivation_ids() -> None:
    output = detect_dormant_reactivation_windows(
        build_dormant_reactivation_trigger_transactions_fixture()
    )

    assert output.loc[0, "evidence_ids"] == ("TXN_DR_PRIOR_001", "TXN_DR_REACT_001")


def test_detection_includes_dormant_value_and_recipient_fields() -> None:
    output = detect_dormant_reactivation_windows(
        build_dormant_reactivation_trigger_transactions_fixture()
    )

    assert output.loc[0, "dormant_days_before_activity"] == 131
    assert output.loc[0, "total_outbound_amount"] == 10000.0
    assert output.loc[0, "max_outbound_amount"] == 10000.0
    assert output.loc[0, "recipient_count"] == 1


def test_overlapping_reactivation_windows_are_deduplicated_deterministically() -> None:
    output = detect_dormant_reactivation_windows(
        build_dormant_reactivation_overlapping_window_transactions_fixture()
    )

    assert len(output) == 1
    assert output.loc[0, "total_outbound_amount"] == 22000.0


def test_multiple_accounts_can_produce_separate_detections() -> None:
    output = detect_dormant_reactivation_windows(
        build_dormant_reactivation_multi_account_transactions_fixture()
    )

    assert output["account_id"].tolist() == ["ACC_DORMANT_001", "ACC_DORMANT_002"]


def test_detection_output_ordering_is_deterministic() -> None:
    frame = build_dormant_reactivation_multi_account_transactions_fixture().sample(
        frac=1,
        random_state=12,
    )

    output = detect_dormant_reactivation_windows(frame)

    assert output["account_id"].tolist() == ["ACC_DORMANT_001", "ACC_DORMANT_002"]


def _with_second_reactivation(timestamp: str) -> pd.DataFrame:
    frame = build_dormant_reactivation_trigger_transactions_fixture()
    second = frame.iloc[1].copy()
    second["transaction_id"] = "TXN_DR_REACT_002"
    second["receiver_account_id"] = "ACC_RECIPIENT_002"
    second["transaction_timestamp"] = pd.Timestamp(timestamp, tz="UTC")
    second["amount"] = 5000.0
    return pd.DataFrame(
        [*frame.to_dict(orient="records"), second.to_dict()],
        columns=TRANSACTION_COLUMNS,
    )
