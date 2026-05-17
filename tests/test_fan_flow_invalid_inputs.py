"""Invalid-input tests for fan-in and fan-out."""

import pandas as pd
import pytest

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    RuleConfigurationError,
    RuleInputError,
    detect_fan_in_windows,
    detect_fan_out_windows,
    run_fan_in_rule,
    run_fan_out_rule,
)
from tests.fixtures.fan_flow_fixtures import (
    TRANSACTION_COLUMNS,
    build_fan_flow_accounts_fixture,
    build_fan_flow_invalid_transactions_fixture,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
)


def test_missing_required_fan_in_transaction_columns_raise_rule_input_error() -> None:
    with pytest.raises(RuleInputError):
        run_fan_in_rule(
            pd.DataFrame({"transaction_id": ["TXN"]}), build_fan_flow_accounts_fixture()
        )


def test_missing_required_fan_out_transaction_columns_raise_rule_input_error() -> None:
    with pytest.raises(RuleInputError):
        run_fan_out_rule(
            pd.DataFrame({"transaction_id": ["TXN"]}), build_fan_flow_accounts_fixture()
        )


def test_missing_account_id_column_in_fan_in_accounts_raises_rule_input_error() -> None:
    with pytest.raises(RuleInputError):
        run_fan_in_rule(
            build_fan_in_only_transactions_fixture(),
            pd.DataFrame({"customer_id": ["CUST"]}),
            FanInRuleConfig(min_unique_senders=4),
        )


def test_missing_account_id_column_in_fan_out_accounts_raises_rule_input_error() -> None:
    with pytest.raises(RuleInputError):
        run_fan_out_rule(
            build_fan_out_only_transactions_fixture(),
            pd.DataFrame({"customer_id": ["CUST"]}),
            FanOutRuleConfig(min_unique_recipients=4),
        )


def test_empty_transaction_dataframe_returns_no_fan_in_alerts_and_empty_detections() -> None:
    frame = pd.DataFrame(columns=TRANSACTION_COLUMNS)
    config = FanInRuleConfig(min_unique_senders=4)

    assert run_fan_in_rule(frame, build_fan_flow_accounts_fixture(), config) == ()
    assert detect_fan_in_windows(frame, config).empty


def test_empty_transaction_dataframe_returns_no_fan_out_alerts_and_empty_detections() -> None:
    frame = pd.DataFrame(columns=TRANSACTION_COLUMNS)
    config = FanOutRuleConfig(min_unique_recipients=4)

    assert run_fan_out_rule(frame, build_fan_flow_accounts_fixture(), config) == ()
    assert detect_fan_out_windows(frame, config).empty


def test_empty_accounts_dataframe_does_not_crash_when_customer_ids_cannot_attach() -> None:
    accounts = pd.DataFrame({"account_id": []})

    fan_in_alert = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        accounts,
        FanInRuleConfig(min_unique_senders=4),
    )[0]
    fan_out_alert = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        accounts,
        FanOutRuleConfig(min_unique_recipients=4),
    )[0]

    assert fan_in_alert.customer_id is None
    assert fan_out_alert.customer_id is None


def test_invalid_timestamps_are_dropped_by_normalisation() -> None:
    assert detect_fan_in_windows(
        build_fan_flow_invalid_transactions_fixture(),
        FanInRuleConfig(min_unique_senders=2),
    ).empty


def test_non_numeric_amounts_are_dropped_by_normalisation() -> None:
    assert detect_fan_out_windows(
        build_fan_flow_invalid_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=2),
    ).empty


def test_invalid_fan_in_config_values_raise_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(min_unique_senders=1)


def test_invalid_fan_out_config_values_raise_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(min_unique_recipients=1)
