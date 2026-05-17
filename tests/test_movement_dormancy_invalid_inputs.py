"""Invalid-input tests for rapid movement and dormant reactivation fixtures."""

import pandas as pd
import pytest

from graph_aml.rules import (
    DormantReactivationRuleConfig,
    RapidMovementRuleConfig,
    RuleConfigurationError,
    RuleInputError,
    detect_dormant_reactivation_windows,
    detect_rapid_movement_windows,
    run_dormant_reactivation_rule,
    run_rapid_movement_rule,
)
from tests.fixtures.movement_dormancy_fixtures import (
    TRANSACTION_COLUMNS,
    build_movement_dormancy_accounts_fixture,
    build_movement_dormancy_invalid_transactions_fixture,
    build_rapid_movement_only_transactions_fixture,
)


def test_missing_required_rapid_transaction_columns_raise_rule_input_error() -> None:
    frame = build_rapid_movement_only_transactions_fixture().drop(columns=["counterparty_id"])

    with pytest.raises(RuleInputError):
        run_rapid_movement_rule(frame, build_movement_dormancy_accounts_fixture())


def test_missing_required_dormant_transaction_columns_raise_rule_input_error() -> None:
    frame = build_rapid_movement_only_transactions_fixture().drop(columns=["counterparty_id"])

    with pytest.raises(RuleInputError):
        run_dormant_reactivation_rule(frame, build_movement_dormancy_accounts_fixture())


def test_missing_account_id_column_in_rapid_accounts_raises() -> None:
    accounts = build_movement_dormancy_accounts_fixture().drop(columns=["account_id"])

    with pytest.raises(RuleInputError):
        run_rapid_movement_rule(build_rapid_movement_only_transactions_fixture(), accounts)


def test_missing_account_id_column_in_dormant_accounts_raises() -> None:
    accounts = build_movement_dormancy_accounts_fixture().drop(columns=["account_id"])

    with pytest.raises(RuleInputError):
        run_dormant_reactivation_rule(build_rapid_movement_only_transactions_fixture(), accounts)


def test_empty_transactions_return_no_rapid_alerts_and_empty_detections() -> None:
    frame = pd.DataFrame(columns=TRANSACTION_COLUMNS)
    accounts = build_movement_dormancy_accounts_fixture()

    assert detect_rapid_movement_windows(frame).empty
    assert run_rapid_movement_rule(frame, accounts) == ()


def test_empty_transactions_return_no_dormant_alerts_and_empty_detections() -> None:
    frame = pd.DataFrame(columns=TRANSACTION_COLUMNS)
    accounts = build_movement_dormancy_accounts_fixture()

    assert detect_dormant_reactivation_windows(frame).empty
    assert run_dormant_reactivation_rule(frame, accounts) == ()


def test_empty_accounts_do_not_crash_alert_construction_when_customer_ids_missing() -> None:
    accounts = pd.DataFrame(columns=["account_id"])

    alert = run_rapid_movement_rule(
        build_rapid_movement_only_transactions_fixture(),
        accounts,
    )[0]

    assert alert.customer_id is None


def test_invalid_timestamps_are_dropped_by_normalisation() -> None:
    frame = build_movement_dormancy_invalid_transactions_fixture()

    assert detect_rapid_movement_windows(frame).empty
    assert detect_dormant_reactivation_windows(frame).empty


def test_non_numeric_amounts_are_dropped_by_normalisation() -> None:
    frame = build_movement_dormancy_invalid_transactions_fixture()

    assert "TXN_MD_INVALID_AMOUNT" not in set(
        detect_rapid_movement_windows(frame).get("evidence_ids", pd.Series(dtype=object))
    )


def test_invalid_rapid_movement_config_values_raise() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(min_outflow_ratio=0)


def test_invalid_dormant_reactivation_config_values_raise() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(dormant_days_threshold=0)
