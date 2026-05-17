"""Reason-code tests for fan-in and fan-out."""

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    build_count_window_reason_code,
    run_fan_in_rule,
    run_fan_out_rule,
)
from tests.fixtures.fan_flow_fixtures import (
    build_fan_flow_accounts_fixture,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
)


def test_fan_in_reason_codes_include_unique_sender_count() -> None:
    alert = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanInRuleConfig(min_unique_senders=4),
    )[0]

    assert "4 unique senders" in alert.reason_code


def test_fan_in_reason_codes_include_window_days() -> None:
    alert = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanInRuleConfig(min_unique_senders=4),
    )[0]

    assert "7 days" in alert.reason_code


def test_fan_out_reason_codes_include_unique_recipient_count() -> None:
    alert = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )[0]

    assert "4 unique recipients" in alert.reason_code


def test_fan_out_reason_codes_include_window_days() -> None:
    alert = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )[0]

    assert "7 days" in alert.reason_code


def test_fan_in_reason_codes_are_deterministic() -> None:
    config = FanInRuleConfig(min_unique_senders=4)
    first = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        config,
    )[0]
    second = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        config,
    )[0]

    assert first.reason_code == second.reason_code


def test_fan_out_reason_codes_are_deterministic() -> None:
    config = FanOutRuleConfig(min_unique_recipients=4)
    first = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        config,
    )[0]
    second = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        config,
    )[0]

    assert first.reason_code == second.reason_code


def test_custom_shared_count_window_template_works_for_fan_in_text() -> None:
    reason = build_count_window_reason_code(
        4,
        "unique senders",
        7,
        "days",
        template="{count} {unit_label} during {window_value} {window_unit}",
    )

    assert reason == "4 unique senders during 7 days"


def test_custom_shared_count_window_template_works_for_fan_out_text() -> None:
    reason = build_count_window_reason_code(
        4,
        "unique recipients",
        7,
        "days",
        template="{count} {unit_label} during {window_value} {window_unit}",
    )

    assert reason == "4 unique recipients during 7 days"


def test_reason_code_text_is_non_empty_for_every_generated_alert() -> None:
    alerts = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanInRuleConfig(min_unique_senders=4),
    ) + run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )

    assert all(alert.reason_code for alert in alerts)
