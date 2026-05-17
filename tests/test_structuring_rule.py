"""End-to-end tests for the deterministic structuring rule."""

import pandas as pd
import pytest

from graph_aml.rules import (
    RuleInputError,
    StructuringRuleConfig,
    run_structuring_rule,
)


def _transactions(
    account_id: str = "ACC_1",
    count: int = 3,
    amount: float = 9500.0,
    hour_step: int = 1,
) -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00Z")
    return pd.DataFrame(
        [
            {
                "transaction_id": f"{account_id}_TXN_{index}",
                "sender_account_id": account_id,
                "receiver_account_id": "ACC_TARGET",
                "counterparty_id": None,
                "transaction_timestamp": start + pd.Timedelta(hours=index * hour_step),
                "amount": amount,
                "transaction_type": "transfer",
            }
            for index in range(count)
        ]
    )


def _accounts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"account_id": "ACC_1", "customer_id": "CUST_1"},
            {"account_id": "ACC_2", "customer_id": "CUST_2"},
        ]
    )


def _config() -> StructuringRuleConfig:
    return StructuringRuleConfig(min_transaction_count=3, window_hours=3)


def test_run_structuring_rule_returns_no_alerts_for_benign_transactions() -> None:
    alerts = run_structuring_rule(_transactions(amount=100), _accounts(), _config())

    assert alerts == ()


def test_run_structuring_rule_returns_alerts_for_structuring_like_transactions() -> None:
    alerts = run_structuring_rule(_transactions(), _accounts(), _config())

    assert len(alerts) == 1


def test_run_structuring_rule_handles_multiple_accounts() -> None:
    frame = pd.concat([_transactions("ACC_1"), _transactions("ACC_2")], ignore_index=True)

    alerts = run_structuring_rule(frame, _accounts(), _config())

    assert [alert.account_id for alert in alerts] == ["ACC_1", "ACC_2"]


def test_run_structuring_rule_ignores_above_threshold_transactions() -> None:
    alerts = run_structuring_rule(_transactions(amount=10001), _accounts(), _config())

    assert alerts == ()


def test_run_structuring_rule_ignores_below_margin_transactions() -> None:
    alerts = run_structuring_rule(_transactions(amount=8999), _accounts(), _config())

    assert alerts == ()


def test_run_structuring_rule_respects_custom_threshold_and_window_config() -> None:
    config = StructuringRuleConfig(
        reporting_threshold=5000,
        below_threshold_margin=0.8,
        min_transaction_count=3,
        window_hours=2,
    )
    alerts = run_structuring_rule(_transactions(amount=4500), _accounts(), config)

    assert len(alerts) == 1


def test_run_structuring_rule_returns_deterministic_alert_ids() -> None:
    first = run_structuring_rule(_transactions(), _accounts(), _config())
    second = run_structuring_rule(_transactions(), _accounts(), _config())

    assert first[0].alert_id == second[0].alert_id


def test_run_structuring_rule_does_not_mutate_input_dataframes() -> None:
    transactions = _transactions()
    accounts = _accounts()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_structuring_rule(transactions, accounts, _config())

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_structuring_rule_raises_for_invalid_inputs() -> None:
    with pytest.raises(RuleInputError):
        run_structuring_rule(pd.DataFrame({"transaction_id": ["TXN"]}), _accounts(), _config())
