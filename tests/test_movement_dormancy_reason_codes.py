"""Reason-code tests for rapid movement and dormant reactivation."""

from graph_aml.rules import (
    build_dormant_reactivation_reason_code,
    build_rapid_movement_reason_code,
    run_dormant_reactivation_rule,
    run_rapid_movement_rule,
)
from tests.fixtures.movement_dormancy_fixtures import (
    build_dormant_reactivation_only_transactions_fixture,
    build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
    build_rapid_movement_only_transactions_fixture,
)


def test_rapid_reason_codes_include_outflow_percentage() -> None:
    alert = run_rapid_movement_rule(
        build_rapid_movement_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert "90 percent" in alert.reason_code


def test_rapid_reason_codes_include_outflow_window_hours() -> None:
    alert = run_rapid_movement_rule(
        build_rapid_movement_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert "48 hours" in alert.reason_code


def test_dormant_reason_codes_include_dormant_days() -> None:
    alert = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert "131 inactive days" in alert.reason_code


def test_dormant_reason_codes_include_formatted_outbound_value() -> None:
    alert = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert "10000.00" in alert.reason_code


def test_dormant_reason_codes_include_reactivation_window_days() -> None:
    alert = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )[0]

    assert "7 days" in alert.reason_code


def test_rapid_reason_codes_are_deterministic() -> None:
    accounts = build_movement_dormancy_accounts_fixture()

    first = run_rapid_movement_rule(build_rapid_movement_only_transactions_fixture(), accounts)
    second = run_rapid_movement_rule(build_rapid_movement_only_transactions_fixture(), accounts)

    assert first[0].reason_code == second[0].reason_code


def test_dormant_reason_codes_are_deterministic() -> None:
    accounts = build_movement_dormancy_accounts_fixture()

    first = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        accounts,
    )
    second = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        accounts,
    )

    assert first[0].reason_code == second[0].reason_code


def test_custom_rapid_reason_code_templates_work() -> None:
    assert (
        build_rapid_movement_reason_code(
            0.9,
            48,
            "{outflow_percentage}|{window_hours}",
        )
        == "90|48"
    )


def test_custom_dormant_reason_code_templates_work() -> None:
    assert (
        build_dormant_reactivation_reason_code(
            120,
            10000,
            7,
            "{dormant_days}|{total_outbound_amount_formatted}|{reactivation_window_days}",
        )
        == "120|10000.00|7"
    )


def test_reason_code_text_is_non_empty_for_every_generated_alert() -> None:
    transactions = build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()
    alerts = (
        *run_rapid_movement_rule(transactions, accounts),
        *run_dormant_reactivation_rule(transactions, accounts),
    )

    assert alerts
    assert all(alert.reason_code for alert in alerts)
