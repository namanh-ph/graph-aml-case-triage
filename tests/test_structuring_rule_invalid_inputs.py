"""Fixture-based invalid-input tests for the structuring rule."""

import pandas as pd
import pytest

from graph_aml.rules import (
    RuleConfigurationError,
    RuleInputError,
    StructuringRuleConfig,
    detect_structuring_windows,
    run_structuring_rule,
)
from tests.fixtures.structuring_fixtures import (
    TRANSACTION_COLUMNS,
    build_structuring_accounts_fixture,
    build_structuring_invalid_transactions_fixture,
    build_structuring_trigger_transactions_fixture,
)


def test_missing_required_transaction_columns_raise_rule_input_error() -> None:
    with pytest.raises(RuleInputError):
        run_structuring_rule(
            pd.DataFrame({"transaction_id": ["TXN_1"]}),
            build_structuring_accounts_fixture(),
        )


def test_missing_account_id_column_in_accounts_raises_rule_input_error() -> None:
    with pytest.raises(RuleInputError):
        run_structuring_rule(
            build_structuring_trigger_transactions_fixture(),
            pd.DataFrame({"customer_id": ["CUST"]}),
        )


def test_empty_transaction_dataframe_returns_no_alerts_with_expected_empty_output() -> None:
    transactions = pd.DataFrame(columns=TRANSACTION_COLUMNS)

    assert run_structuring_rule(transactions, build_structuring_accounts_fixture()) == ()
    assert detect_structuring_windows(transactions).empty


def test_empty_accounts_dataframe_does_not_crash_when_customer_id_cannot_attach() -> None:
    alerts = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(),
        pd.DataFrame(columns=["account_id", "customer_id"]),
    )

    assert alerts[0].customer_id is None


def test_invalid_timestamps_are_dropped_by_normalisation() -> None:
    alerts = run_structuring_rule(
        build_structuring_invalid_transactions_fixture(),
        build_structuring_accounts_fixture(),
    )

    assert alerts == ()


def test_non_numeric_amounts_are_dropped_by_normalisation() -> None:
    frame = build_structuring_invalid_transactions_fixture()

    alerts = run_structuring_rule(frame, build_structuring_accounts_fixture())

    assert alerts == ()


def test_invalid_config_values_raise_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(window_hours=0)
