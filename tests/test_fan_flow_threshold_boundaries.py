"""Shared fan-flow threshold boundary tests."""

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    detect_fan_in_windows,
    detect_fan_out_windows,
)
from tests.fixtures.fan_flow_fixtures import (
    build_fan_flow_accounts_fixture,
    build_fan_flow_duplicate_sender_recipient_fixture,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
)


def test_fan_in_triggers_exactly_at_min_unique_senders() -> None:
    output = detect_fan_in_windows(
        build_fan_in_only_transactions_fixture(),
        FanInRuleConfig(min_unique_senders=4),
    )

    assert output.loc[0, "unique_sender_count"] == 4


def test_fan_in_does_not_trigger_one_below_min_unique_senders() -> None:
    config = FanInRuleConfig(min_unique_senders=5)

    assert detect_fan_in_windows(build_fan_in_only_transactions_fixture(), config).empty


def test_fan_out_triggers_exactly_at_min_unique_recipients() -> None:
    output = detect_fan_out_windows(
        build_fan_out_only_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )

    assert output.loc[0, "unique_recipient_count"] == 4


def test_fan_out_does_not_trigger_one_below_min_unique_recipients() -> None:
    config = FanOutRuleConfig(min_unique_recipients=5)

    assert detect_fan_out_windows(build_fan_out_only_transactions_fixture(), config).empty


def test_repeated_fan_in_senders_do_not_inflate_unique_sender_count() -> None:
    config = FanInRuleConfig(min_unique_senders=4)

    assert detect_fan_in_windows(build_fan_flow_duplicate_sender_recipient_fixture(), config).empty


def test_repeated_fan_out_recipients_do_not_inflate_unique_recipient_count() -> None:
    config = FanOutRuleConfig(min_unique_recipients=4)

    assert detect_fan_out_windows(build_fan_flow_duplicate_sender_recipient_fixture(), config).empty


def test_fan_in_min_total_amount_filters_below_configured_total() -> None:
    config = FanInRuleConfig(min_unique_senders=4, min_total_amount=3000)

    assert detect_fan_in_windows(build_fan_in_only_transactions_fixture(), config).empty


def test_fan_out_min_total_amount_filters_below_configured_total() -> None:
    config = FanOutRuleConfig(min_unique_recipients=4, min_total_amount=3000)

    assert detect_fan_out_windows(build_fan_out_only_transactions_fixture(), config).empty


def test_custom_fan_in_thresholds_change_detection_deterministically() -> None:
    frame = build_fan_in_only_transactions_fixture()

    assert detect_fan_in_windows(frame, FanInRuleConfig(min_unique_senders=4)).shape[0] == 1
    assert detect_fan_in_windows(frame, FanInRuleConfig(min_unique_senders=5)).empty


def test_custom_fan_out_thresholds_change_detection_deterministically() -> None:
    frame = build_fan_out_only_transactions_fixture()

    assert detect_fan_out_windows(frame, FanOutRuleConfig(min_unique_recipients=4)).shape[0] == 1
    assert detect_fan_out_windows(frame, FanOutRuleConfig(min_unique_recipients=5)).empty


def test_account_fixture_is_available_for_threshold_alert_context() -> None:
    assert not build_fan_flow_accounts_fixture().empty
