"""Rolling-window boundary tests for rapid movement and dormant reactivation."""

import pandas as pd

from graph_aml.rules import (
    DormantReactivationRuleConfig,
    detect_dormant_reactivation_windows,
    detect_rapid_movement_windows,
)
from tests.fixtures.movement_dormancy_fixtures import (
    TRANSACTION_COLUMNS,
    build_movement_dormancy_window_boundary_transactions_fixture,
)


def test_rapid_outbound_at_window_start_is_included() -> None:
    output = detect_rapid_movement_windows(
        build_movement_dormancy_window_boundary_transactions_fixture()
    )
    row = output.loc[output["account_id"].eq("ACC_PASS_001")].iloc[0]

    assert row["outbound_evidence_ids"] == ("TXN_MD_BOUNDARY_RM_OUT_START",)


def test_rapid_outbound_at_window_end_is_included() -> None:
    output = detect_rapid_movement_windows(
        build_movement_dormancy_window_boundary_transactions_fixture()
    )
    row = output.loc[output["account_id"].eq("ACC_PASS_002")].iloc[0]

    assert row["outbound_evidence_ids"] == ("TXN_MD_BOUNDARY_RM_OUT_END",)


def test_rapid_outbound_just_after_window_is_excluded() -> None:
    output = detect_rapid_movement_windows(
        build_movement_dormancy_window_boundary_transactions_fixture()
    )

    assert "ACC_PASS_003" not in set(output["account_id"])


def test_dormant_reactivation_at_window_start_is_included() -> None:
    output = detect_dormant_reactivation_windows(
        build_movement_dormancy_window_boundary_transactions_fixture()
    )
    row = output.loc[output["account_id"].eq("ACC_DORMANT_001")].iloc[0]

    assert "TXN_MD_BOUNDARY_DR_REACT_001" in row["reactivation_evidence_ids"]


def test_dormant_reactivation_at_window_end_is_included() -> None:
    output = detect_dormant_reactivation_windows(
        build_movement_dormancy_window_boundary_transactions_fixture()
    )
    row = output.loc[output["account_id"].eq("ACC_DORMANT_001")].iloc[0]

    assert "TXN_MD_BOUNDARY_DR_REACT_002" in row["reactivation_evidence_ids"]


def test_dormant_reactivation_just_after_window_is_excluded() -> None:
    config = DormantReactivationRuleConfig(min_outbound_transaction_count=2)

    output = detect_dormant_reactivation_windows(
        build_movement_dormancy_window_boundary_transactions_fixture(),
        config,
    )

    assert "ACC_DORMANT_002" not in set(output["account_id"])


def test_later_valid_rapid_window_can_trigger_when_earliest_does_not() -> None:
    start = pd.Timestamp("2025-01-20 09:00:00", tz="UTC")
    frame = pd.DataFrame(
        [
            _row("TXN_MD_LATER_RM_IN_BAD", "SRC", "ACC_PASS_001", None, start, 10000, "transfer"),
            _row(
                "TXN_MD_LATER_RM_OUT_BAD",
                "ACC_PASS_001",
                "ACC_MD_RECIPIENT_001",
                None,
                start + pd.Timedelta(hours=1),
                1000,
                "wire",
            ),
            _row(
                "TXN_MD_LATER_RM_IN_GOOD",
                "SRC",
                "ACC_PASS_001",
                None,
                start + pd.Timedelta(days=3),
                10000,
                "transfer",
            ),
            _row(
                "TXN_MD_LATER_RM_OUT_GOOD",
                "ACC_PASS_001",
                "ACC_MD_RECIPIENT_001",
                None,
                start + pd.Timedelta(days=3, hours=1),
                10000,
                "wire",
            ),
        ],
        columns=TRANSACTION_COLUMNS,
    )

    output = detect_rapid_movement_windows(frame)

    assert output.loc[0, "inbound_evidence_ids"] == ("TXN_MD_LATER_RM_IN_GOOD",)


def test_later_valid_dormant_window_can_trigger_when_earliest_account_does_not() -> None:
    output = detect_dormant_reactivation_windows(
        build_movement_dormancy_window_boundary_transactions_fixture()
    )

    assert "ACC_DORMANT_001" in set(output["account_id"])


def test_detection_windows_are_populated_in_both_rule_outputs() -> None:
    frame = build_movement_dormancy_window_boundary_transactions_fixture()
    rapid = detect_rapid_movement_windows(frame)
    dormant = detect_dormant_reactivation_windows(frame)

    assert rapid["detection_window_start"].notna().all()
    assert rapid["detection_window_end"].notna().all()
    assert dormant["detection_window_start"].notna().all()
    assert dormant["detection_window_end"].notna().all()


def test_evidence_ids_are_deterministic_for_both_rule_outputs() -> None:
    frame = build_movement_dormancy_window_boundary_transactions_fixture()

    first_rapid = detect_rapid_movement_windows(frame)
    second_rapid = detect_rapid_movement_windows(frame.sample(frac=1, random_state=5))
    first_dormant = detect_dormant_reactivation_windows(frame)
    second_dormant = detect_dormant_reactivation_windows(frame.sample(frac=1, random_state=6))

    assert first_rapid["evidence_ids"].tolist() == second_rapid["evidence_ids"].tolist()
    assert first_dormant["evidence_ids"].tolist() == second_dormant["evidence_ids"].tolist()


def _row(
    transaction_id: str,
    sender: str,
    receiver: str | None,
    counterparty: str | None,
    timestamp: pd.Timestamp,
    amount: float,
    transaction_type: str,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender,
        "receiver_account_id": receiver,
        "counterparty_id": counterparty,
        "device_id": "DEV_MD_BOUNDARY",
        "transaction_timestamp": timestamp,
        "amount": amount,
        "currency": "USD",
        "transaction_type": transaction_type,
        "channel": "online",
        "origin_country": "US",
        "destination_country": "US",
        "is_cross_border": False,
        "is_labelled_suspicious": False,
        "typology_label": None,
        "source_file": "movement_dormancy_window_test",
    }
