"""Fixture-based exact trigger tests for the structuring rule."""

from graph_aml.alerts import validate_alert_record
from graph_aml.rules import StructuringRuleConfig, run_structuring_rule


def test_exact_minimum_count_within_window_triggers_one_alert(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alerts = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )

    assert len(alerts) == 1


def test_alert_account_id_matches_sender_account(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert alert.account_id == "ACC_STRUCT_001"


def test_alert_customer_id_is_attached_from_accounts(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert alert.customer_id == "CUST_STRUCT_001"


def test_alert_typology_is_structuring(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert alert.typology == "structuring"


def test_alert_rule_name_is_structuring(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert alert.rule_name == "Structuring"


def test_alert_severity_is_high_by_default(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert alert.severity == "high"


def test_alert_risk_score_equals_base_score_for_normal_trigger(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert alert.risk_score_rule == StructuringRuleConfig().base_risk_score


def test_reason_code_includes_transaction_count_and_window(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert "8 transfers" in alert.reason_code
    assert "24 hours" in alert.reason_code


def test_evidence_ids_include_every_transaction_in_triggering_window(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert alert.evidence_ids == tuple(structuring_trigger_transactions_fixture["transaction_id"])


def test_detection_window_start_and_end_are_populated(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    assert alert.detection_window_start is not None
    assert alert.detection_window_end is not None


def test_generated_alert_validates_through_common_alert_schema(
    structuring_accounts_fixture,
    structuring_trigger_transactions_fixture,
) -> None:
    alert = run_structuring_rule(
        structuring_trigger_transactions_fixture,
        structuring_accounts_fixture,
    )[0]

    validate_alert_record(alert)
