"""Joint fan-in and fan-out trigger tests."""

from graph_aml.alerts import validate_alert_record
from graph_aml.rules import FanInRuleConfig, FanOutRuleConfig, run_fan_in_rule, run_fan_out_rule


def _fan_in_config() -> FanInRuleConfig:
    return FanInRuleConfig(min_unique_senders=4)


def _fan_out_config() -> FanOutRuleConfig:
    return FanOutRuleConfig(min_unique_recipients=4)


def test_joint_fixture_produces_fan_in_and_fan_out_alerts(
    fan_flow_accounts_fixture,
    joint_fan_flow_transactions_fixture,
) -> None:
    fan_in_alerts = run_fan_in_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_in_config(),
    )
    fan_out_alerts = run_fan_out_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_out_config(),
    )

    assert len(fan_in_alerts) >= 1
    assert len(fan_out_alerts) >= 1


def test_fan_in_alerts_use_receiving_account_ids(
    fan_flow_accounts_fixture,
    joint_fan_flow_transactions_fixture,
) -> None:
    alerts = run_fan_in_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_in_config(),
    )

    assert alerts[0].account_id == "ACC_COLLECT_001"


def test_fan_out_alerts_use_sending_account_ids(
    fan_flow_accounts_fixture,
    joint_fan_flow_transactions_fixture,
) -> None:
    alerts = run_fan_out_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_out_config(),
    )

    assert alerts[0].account_id == "ACC_DISPERSE_001"


def test_joint_alert_typologies_are_rule_specific(
    fan_flow_accounts_fixture,
    joint_fan_flow_transactions_fixture,
) -> None:
    fan_in_alert = run_fan_in_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_in_config(),
    )[0]
    fan_out_alert = run_fan_out_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_out_config(),
    )[0]

    assert fan_in_alert.typology == "fan_in"
    assert fan_out_alert.typology == "fan_out"


def test_joint_alert_rule_names_are_rule_specific(
    fan_flow_accounts_fixture,
    joint_fan_flow_transactions_fixture,
) -> None:
    fan_in_alert = run_fan_in_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_in_config(),
    )[0]
    fan_out_alert = run_fan_out_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_out_config(),
    )[0]

    assert fan_in_alert.rule_name == "Fan-in"
    assert fan_out_alert.rule_name == "Fan-out"


def test_joint_alert_customer_ids_attach_to_correct_rule_account(
    fan_flow_accounts_fixture,
    joint_fan_flow_transactions_fixture,
) -> None:
    fan_in_alert = run_fan_in_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_in_config(),
    )[0]
    fan_out_alert = run_fan_out_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_out_config(),
    )[0]

    assert fan_in_alert.customer_id == "CUST_COLLECT_001"
    assert fan_out_alert.customer_id == "CUST_DISPERSE_001"


def test_joint_alerts_validate_through_common_schema(
    fan_flow_accounts_fixture,
    joint_fan_flow_transactions_fixture,
) -> None:
    alerts = run_fan_in_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_in_config(),
    ) + run_fan_out_rule(
        joint_fan_flow_transactions_fixture,
        fan_flow_accounts_fixture,
        _fan_out_config(),
    )

    for alert in alerts:
        validate_alert_record(alert)
