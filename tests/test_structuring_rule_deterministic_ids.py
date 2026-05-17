"""Regression tests for deterministic structuring alert IDs."""

from graph_aml.rules import (
    build_structuring_alerts,
    detect_structuring_windows,
    run_structuring_rule,
)
from tests.fixtures.structuring_fixtures import (
    build_structuring_accounts_fixture,
    build_structuring_trigger_transactions_fixture,
)


def test_same_fixture_twice_produces_identical_alert_ids() -> None:
    accounts = build_structuring_accounts_fixture()

    first = run_structuring_rule(build_structuring_trigger_transactions_fixture(), accounts)
    second = run_structuring_rule(build_structuring_trigger_transactions_fixture(), accounts)

    assert first[0].alert_id == second[0].alert_id


def test_reordering_input_transactions_does_not_change_alert_ids() -> None:
    accounts = build_structuring_accounts_fixture()
    transactions = build_structuring_trigger_transactions_fixture()

    first = run_structuring_rule(transactions, accounts)
    second = run_structuring_rule(transactions.sample(frac=1, random_state=11), accounts)

    assert first[0].alert_id == second[0].alert_id


def test_reordering_evidence_ids_inside_equivalent_detections_does_not_change_alert_ids() -> None:
    accounts = build_structuring_accounts_fixture()
    detection = detect_structuring_windows(build_structuring_trigger_transactions_fixture())
    reversed_detection = detection.copy(deep=True)
    reversed_detection.at[0, "evidence_ids"] = tuple(reversed(detection.loc[0, "evidence_ids"]))

    first = build_structuring_alerts(detection, accounts)
    second = build_structuring_alerts(reversed_detection, accounts)

    assert first[0].alert_id == second[0].alert_id


def test_changing_account_id_changes_alert_id() -> None:
    accounts = build_structuring_accounts_fixture()

    first = run_structuring_rule(build_structuring_trigger_transactions_fixture(), accounts)
    second = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(account_id="ACC_STRUCT_002"),
        accounts,
    )

    assert first[0].alert_id != second[0].alert_id


def test_changing_detection_window_changes_alert_id() -> None:
    accounts = build_structuring_accounts_fixture()

    first = run_structuring_rule(build_structuring_trigger_transactions_fixture(), accounts)
    second = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(start_timestamp="2025-01-11 09:00:00"),
        accounts,
    )

    assert first[0].alert_id != second[0].alert_id


def test_changing_evidence_transactions_changes_alert_id() -> None:
    accounts = build_structuring_accounts_fixture()
    transactions = build_structuring_trigger_transactions_fixture()
    changed = transactions.copy(deep=True)
    changed.loc[0, "transaction_id"] = "TXN_STRUCT_TRIGGER_CHANGED"

    first = run_structuring_rule(transactions, accounts)
    second = run_structuring_rule(changed, accounts)

    assert first[0].alert_id != second[0].alert_id
