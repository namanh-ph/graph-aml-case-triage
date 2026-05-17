"""Dormant reactivation threshold and gap tests using joint fixtures."""

import pandas as pd

from graph_aml.rules import (
    DormantReactivationRuleConfig,
    build_dormant_reactivation_alerts,
    detect_dormant_reactivation_windows,
    run_dormant_reactivation_rule,
)
from tests.fixtures.movement_dormancy_fixtures import (
    TRANSACTION_COLUMNS,
    build_dormant_reactivation_only_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
)


def test_dormant_reactivation_triggers_exactly_at_dormant_days_threshold() -> None:
    frame = build_dormant_reactivation_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("PRIOR"), "transaction_timestamp"] = (
        pd.Timestamp("2024-09-12 09:00:00", tz="UTC")
    )

    output = detect_dormant_reactivation_windows(frame)

    assert output.loc[0, "dormant_days_before_activity"] == 120


def test_dormant_reactivation_does_not_trigger_one_day_below_threshold() -> None:
    frame = build_dormant_reactivation_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("PRIOR"), "transaction_timestamp"] = (
        pd.Timestamp("2024-09-13 09:00:00", tz="UTC")
    )

    assert detect_dormant_reactivation_windows(frame).empty


def test_dormant_reactivation_triggers_exactly_at_min_total_outbound_amount() -> None:
    output = detect_dormant_reactivation_windows(
        build_dormant_reactivation_only_transactions_fixture()
    )

    assert output.loc[0, "total_outbound_amount"] == 10000.0


def test_dormant_reactivation_does_not_trigger_below_total_outbound_amount() -> None:
    frame = build_dormant_reactivation_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("REACT"), "amount"] = 9999.0

    assert detect_dormant_reactivation_windows(frame).empty


def test_dormant_reactivation_triggers_at_outbound_transaction_count_threshold() -> None:
    output = detect_dormant_reactivation_windows(
        build_dormant_reactivation_only_transactions_fixture()
    )

    assert output.loc[0, "reactivation_transaction_count"] == 1


def test_dormant_reactivation_does_not_trigger_below_count_threshold() -> None:
    config = DormantReactivationRuleConfig(min_outbound_transaction_count=2)

    assert detect_dormant_reactivation_windows(
        build_dormant_reactivation_only_transactions_fixture(),
        config,
    ).empty


def test_high_value_risk_score_is_used_at_configured_multiplier() -> None:
    frame = build_dormant_reactivation_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("REACT"), "amount"] = 20000.0
    detections = detect_dormant_reactivation_windows(frame)

    alert = build_dormant_reactivation_alerts(
        detections,
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert alert.risk_score_rule == 90.0


def test_custom_dormancy_and_outbound_thresholds_change_detection_deterministically() -> None:
    frame = build_dormant_reactivation_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("PRIOR"), "transaction_timestamp"] = (
        pd.Timestamp("2024-12-20 09:00:00", tz="UTC")
    )
    config = DormantReactivationRuleConfig(dormant_days_threshold=20)

    assert run_dormant_reactivation_rule(
        frame,
        build_movement_dormancy_accounts_fixture(),
        config,
    )
    assert (
        run_dormant_reactivation_rule(
            frame,
            build_movement_dormancy_accounts_fixture(),
        )
        == ()
    )


def test_accounts_with_no_prior_activity_produce_no_dormant_alert() -> None:
    frame = build_dormant_reactivation_only_transactions_fixture()
    frame = frame.loc[frame["transaction_id"].str.contains("REACT")].copy()

    assert (
        run_dormant_reactivation_rule(
            frame,
            build_movement_dormancy_accounts_fixture(),
        )
        == ()
    )


def test_prior_inbound_and_prior_outbound_can_establish_activity_history() -> None:
    inbound = build_dormant_reactivation_only_transactions_fixture()
    outbound = inbound.copy(deep=True)
    outbound.loc[outbound["transaction_id"].str.contains("PRIOR"), "sender_account_id"] = (
        "ACC_DORMANT_001"
    )
    outbound.loc[outbound["transaction_id"].str.contains("PRIOR"), "receiver_account_id"] = (
        "ACC_MD_RECIPIENT_003"
    )

    assert not detect_dormant_reactivation_windows(inbound).empty
    assert not detect_dormant_reactivation_windows(
        pd.DataFrame(outbound.to_dict("records"), columns=TRANSACTION_COLUMNS)
    ).empty
