"""Rapid movement threshold and ratio tests using joint fixtures."""

from graph_aml.rules import (
    RapidMovementRuleConfig,
    build_rapid_movement_alerts,
    detect_rapid_movement_windows,
    run_rapid_movement_rule,
)
from tests.fixtures.movement_dormancy_fixtures import (
    build_movement_dormancy_accounts_fixture,
    build_rapid_movement_only_transactions_fixture,
)


def test_rapid_movement_triggers_exactly_at_min_outflow_ratio() -> None:
    output = detect_rapid_movement_windows(build_rapid_movement_only_transactions_fixture())

    assert output.loc[0, "outflow_ratio"] == 0.9


def test_rapid_movement_does_not_trigger_just_below_min_outflow_ratio() -> None:
    frame = build_rapid_movement_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("OUT"), "amount"] = 8999.0

    assert detect_rapid_movement_windows(frame).empty


def test_rapid_movement_triggers_when_retained_ratio_equals_maximum() -> None:
    output = detect_rapid_movement_windows(build_rapid_movement_only_transactions_fixture())

    assert output.loc[0, "retained_ratio"] == 0.1


def test_rapid_movement_does_not_trigger_when_retained_ratio_above_maximum() -> None:
    frame = build_rapid_movement_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("OUT"), "amount"] = 8500.0
    config = RapidMovementRuleConfig(min_outflow_ratio=0.8, max_retained_ratio=0.1)

    assert detect_rapid_movement_windows(frame, config).empty


def test_rapid_movement_does_not_trigger_when_total_received_below_threshold() -> None:
    config = RapidMovementRuleConfig(min_total_received=11000.0)

    assert detect_rapid_movement_windows(
        build_rapid_movement_only_transactions_fixture(),
        config,
    ).empty


def test_rapid_movement_does_not_trigger_below_outgoing_count_threshold() -> None:
    config = RapidMovementRuleConfig(min_outgoing_transaction_count=2)

    assert detect_rapid_movement_windows(
        build_rapid_movement_only_transactions_fixture(),
        config,
    ).empty


def test_high_ratio_risk_score_is_used_at_threshold() -> None:
    frame = build_rapid_movement_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("OUT"), "amount"] = 9800.0
    detections = detect_rapid_movement_windows(frame)

    alert = build_rapid_movement_alerts(
        detections,
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert alert.risk_score_rule == 90.0


def test_custom_rapid_thresholds_change_detection_deterministically() -> None:
    frame = build_rapid_movement_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("OUT"), "amount"] = 8000.0
    config = RapidMovementRuleConfig(min_outflow_ratio=0.8, max_retained_ratio=0.2)

    assert run_rapid_movement_rule(
        frame,
        build_movement_dormancy_accounts_fixture(),
        config,
    )
    assert run_rapid_movement_rule(frame, build_movement_dormancy_accounts_fixture()) == ()


def test_negative_retained_amount_is_allowed_when_sent_exceeds_received() -> None:
    frame = build_rapid_movement_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("OUT"), "amount"] = 11000.0

    output = detect_rapid_movement_windows(frame)

    assert output.loc[0, "retained_amount"] == -1000.0


def test_retained_ratio_uses_non_negative_retained_value() -> None:
    frame = build_rapid_movement_only_transactions_fixture()
    frame.loc[frame["transaction_id"].str.contains("OUT"), "amount"] = 11000.0

    output = detect_rapid_movement_windows(frame)

    assert output.loc[0, "retained_ratio"] == 0.0
