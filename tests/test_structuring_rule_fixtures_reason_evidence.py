"""Fixture-based reason code and evidence ID tests."""

from graph_aml.rules import (
    build_rule_reason_code,
    build_structuring_alerts,
    detect_structuring_windows,
    run_structuring_rule,
)
from tests.fixtures.structuring_fixtures import (
    build_structuring_accounts_fixture,
    build_structuring_trigger_transactions_fixture,
)


def _detection():
    return detect_structuring_windows(build_structuring_trigger_transactions_fixture())


def test_reason_code_uses_configured_transaction_count() -> None:
    alert = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(),
        build_structuring_accounts_fixture(),
    )[0]

    assert alert.reason_code.startswith("8 transfers")


def test_reason_code_uses_configured_window_hours() -> None:
    alert = run_structuring_rule(
        build_structuring_trigger_transactions_fixture(),
        build_structuring_accounts_fixture(),
    )[0]

    assert alert.reason_code.endswith("24 hours")


def test_custom_reason_code_template_works() -> None:
    reason = build_rule_reason_code(
        8,
        10000,
        24,
        template="{count} near {threshold} during {window_hours}h",
    )

    assert reason == "8 near 10000 during 24h"


def test_evidence_ids_are_non_empty() -> None:
    assert _detection().loc[0, "evidence_ids"]


def test_evidence_ids_are_unique() -> None:
    evidence_ids = _detection().loc[0, "evidence_ids"]

    assert len(evidence_ids) == len(set(evidence_ids))


def test_evidence_ids_are_ordered_deterministically() -> None:
    evidence_ids = _detection().loc[0, "evidence_ids"]

    assert evidence_ids == tuple(f"TXN_STRUCT_TRIGGER_{index:03d}" for index in range(1, 9))


def test_alert_evidence_ids_match_detection_evidence_ids() -> None:
    detection = _detection()
    alert = build_structuring_alerts(detection, build_structuring_accounts_fixture())[0]

    assert alert.evidence_ids == detection.loc[0, "evidence_ids"]


def test_alert_evidence_ids_are_tuples_after_alert_construction() -> None:
    alert = build_structuring_alerts(_detection(), build_structuring_accounts_fixture())[0]

    assert isinstance(alert.evidence_ids, tuple)


def test_detection_transaction_count_equals_evidence_id_count() -> None:
    detection = _detection()

    assert detection.loc[0, "transaction_count"] == len(detection.loc[0, "evidence_ids"])
