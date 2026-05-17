"""Evidence isolation tests for rapid movement and dormant reactivation."""

from graph_aml.rules import (
    build_dormant_reactivation_alerts,
    build_rapid_movement_alerts,
    detect_dormant_reactivation_windows,
    detect_rapid_movement_windows,
)
from tests.fixtures.movement_dormancy_fixtures import (
    build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
    build_movement_dormancy_overlapping_window_transactions_fixture,
)


def test_rapid_evidence_contains_only_detected_pass_through_window_transactions() -> None:
    output = detect_rapid_movement_windows(
        build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    )

    assert output.loc[0, "evidence_ids"] == ("TXN_MD_RM_IN_001", "TXN_MD_RM_OUT_001")


def test_dormant_evidence_contains_prior_and_reactivation_transactions() -> None:
    output = detect_dormant_reactivation_windows(
        build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    )

    assert output.loc[0, "evidence_ids"] == ("TXN_MD_DR_PRIOR_001", "TXN_MD_DR_REACT_001")


def test_rapid_evidence_does_not_leak_across_pass_through_accounts() -> None:
    output = detect_rapid_movement_windows(
        build_movement_dormancy_overlapping_window_transactions_fixture()
    )

    evidence = set(output.loc[0, "evidence_ids"])
    assert all("ACC_PASS_002" not in value for value in evidence)


def test_dormant_evidence_does_not_leak_across_dormant_accounts() -> None:
    output = detect_dormant_reactivation_windows(
        build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    )

    assert all("RM_" not in evidence_id for evidence_id in output.loc[0, "evidence_ids"])


def test_rapid_evidence_excludes_unrelated_dormant_only_transactions() -> None:
    output = detect_rapid_movement_windows(
        build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    )

    assert all("DR_" not in evidence_id for evidence_id in output.loc[0, "evidence_ids"])


def test_dormant_evidence_excludes_unrelated_rapid_only_transactions() -> None:
    output = detect_dormant_reactivation_windows(
        build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    )

    assert all("RM_" not in evidence_id for evidence_id in output.loc[0, "evidence_ids"])


def test_evidence_ids_are_unique_for_each_alert() -> None:
    accounts = build_movement_dormancy_accounts_fixture()
    transactions = build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    alerts = (
        *build_rapid_movement_alerts(detect_rapid_movement_windows(transactions), accounts),
        *build_dormant_reactivation_alerts(
            detect_dormant_reactivation_windows(transactions),
            accounts,
        ),
    )

    assert all(len(alert.evidence_ids) == len(set(alert.evidence_ids)) for alert in alerts)


def test_evidence_ids_are_tuples_after_alert_construction() -> None:
    accounts = build_movement_dormancy_accounts_fixture()
    rapid = build_rapid_movement_alerts(
        detect_rapid_movement_windows(
            build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
        ),
        accounts,
    )[0]
    dormant = build_dormant_reactivation_alerts(
        detect_dormant_reactivation_windows(
            build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
        ),
        accounts,
    )[0]

    assert isinstance(rapid.evidence_ids, tuple)
    assert isinstance(dormant.evidence_ids, tuple)


def test_rapid_detection_counts_match_inbound_plus_outbound_evidence() -> None:
    output = detect_rapid_movement_windows(
        build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    )
    row = output.loc[0]

    assert row["inbound_transaction_count"] + row["outbound_transaction_count"] == len(
        row["evidence_ids"]
    )


def test_dormant_evidence_places_prior_activity_before_reactivation_evidence() -> None:
    output = detect_dormant_reactivation_windows(
        build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    )

    assert output.loc[0, "evidence_ids"][0] == "TXN_MD_DR_PRIOR_001"
    assert output.loc[0, "evidence_ids"][1:] == output.loc[0, "reactivation_evidence_ids"]
