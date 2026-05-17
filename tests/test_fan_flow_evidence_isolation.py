"""Evidence isolation tests for fan-in and fan-out."""

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    detect_fan_in_windows,
    detect_fan_out_windows,
    run_fan_in_rule,
    run_fan_out_rule,
)
from tests.fixtures.fan_flow_fixtures import (
    build_fan_flow_accounts_fixture,
    build_joint_fan_in_and_fan_out_transactions_fixture,
)
from tests.fixtures.fan_in_fixtures import (
    build_fan_in_accounts_fixture,
    build_fan_in_multi_receiver_transactions_fixture,
)
from tests.fixtures.fan_out_fixtures import (
    build_fan_out_accounts_fixture,
    build_fan_out_multi_sender_transactions_fixture,
)


def _fan_in_config() -> FanInRuleConfig:
    return FanInRuleConfig(min_unique_senders=4)


def _fan_out_config() -> FanOutRuleConfig:
    return FanOutRuleConfig(min_unique_recipients=4)


def test_fan_in_evidence_contains_only_receiving_account_window_transactions() -> None:
    alert = run_fan_in_rule(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_in_config(),
    )[0]

    assert all(evidence_id.startswith("TXN_FLOW_IN_") for evidence_id in alert.evidence_ids)


def test_fan_out_evidence_contains_only_sending_account_window_transactions() -> None:
    alert = run_fan_out_rule(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_out_config(),
    )[0]

    assert all(evidence_id.startswith("TXN_FLOW_OUT_") for evidence_id in alert.evidence_ids)


def test_fan_in_evidence_ids_do_not_leak_across_receiving_accounts() -> None:
    alerts = run_fan_in_rule(
        build_fan_in_multi_receiver_transactions_fixture(),
        build_fan_in_accounts_fixture(),
    )

    for alert in alerts:
        marker = "_A_" if alert.account_id == "ACC_COLLECT_001" else "_B_"
        assert all(marker in evidence_id for evidence_id in alert.evidence_ids)


def test_fan_out_evidence_ids_do_not_leak_across_sending_accounts() -> None:
    alerts = run_fan_out_rule(
        build_fan_out_multi_sender_transactions_fixture(),
        build_fan_out_accounts_fixture(),
    )

    for alert in alerts:
        marker = "_A_" if alert.account_id == "ACC_DISPERSE_001" else "_B_"
        assert all(marker in evidence_id for evidence_id in alert.evidence_ids)


def test_fan_in_evidence_excludes_unrelated_fan_out_transactions() -> None:
    alert = run_fan_in_rule(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_in_config(),
    )[0]

    assert not any(evidence_id.startswith("TXN_FLOW_OUT_") for evidence_id in alert.evidence_ids)


def test_fan_out_evidence_excludes_unrelated_fan_in_transactions() -> None:
    alert = run_fan_out_rule(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_out_config(),
    )[0]

    assert not any(evidence_id.startswith("TXN_FLOW_IN_") for evidence_id in alert.evidence_ids)


def test_evidence_ids_are_unique_for_each_alert() -> None:
    alerts = run_fan_in_rule(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_in_config(),
    ) + run_fan_out_rule(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_out_config(),
    )

    for alert in alerts:
        assert len(alert.evidence_ids) == len(set(alert.evidence_ids))


def test_evidence_ids_are_tuples_after_alert_construction() -> None:
    alert = run_fan_out_rule(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_out_config(),
    )[0]

    assert isinstance(alert.evidence_ids, tuple)


def test_fan_in_detection_transaction_count_equals_evidence_count() -> None:
    detection = detect_fan_in_windows(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        _fan_in_config(),
    ).iloc[0]

    assert detection["transaction_count"] == len(detection["evidence_ids"])


def test_fan_out_detection_transaction_count_equals_evidence_count() -> None:
    detection = detect_fan_out_windows(
        build_joint_fan_in_and_fan_out_transactions_fixture(),
        _fan_out_config(),
    ).iloc[0]

    assert detection["transaction_count"] == len(detection["evidence_ids"])
