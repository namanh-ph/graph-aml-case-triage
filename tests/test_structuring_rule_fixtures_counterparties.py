"""Fixture-based counterparty handling tests for structuring candidates."""

from graph_aml.rules import (
    StructuringRuleConfig,
    filter_structuring_candidate_transactions,
    run_structuring_rule,
)
from tests.fixtures.structuring_fixtures import (
    build_structuring_accounts_fixture,
    build_structuring_counterparty_transactions_fixture,
)


def test_counterparty_payments_are_included_when_enabled() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_counterparty_transactions_fixture()
    )

    assert "TXN_STRUCT_CP_001" in set(candidates["transaction_id"])


def test_counterparty_only_payments_are_excluded_when_disabled() -> None:
    config = StructuringRuleConfig(include_counterparty_payments=False)

    candidates = filter_structuring_candidate_transactions(
        build_structuring_counterparty_transactions_fixture(),
        config,
    )

    assert "TXN_STRUCT_CP_001" not in set(candidates["transaction_id"])


def test_internal_receiver_account_payments_are_included_when_counterparties_disabled() -> None:
    config = StructuringRuleConfig(include_counterparty_payments=False)

    candidates = filter_structuring_candidate_transactions(
        build_structuring_counterparty_transactions_fixture(),
        config,
    )

    assert "TXN_STRUCT_INTERNAL_001" in set(candidates["transaction_id"])


def test_evidence_ids_for_counterparty_payments_are_preserved() -> None:
    config = StructuringRuleConfig(min_transaction_count=4)
    frame = build_structuring_counterparty_transactions_fixture().head(4)

    alert = run_structuring_rule(frame, build_structuring_accounts_fixture(), config)[0]

    assert alert.evidence_ids == tuple(f"TXN_STRUCT_CP_{index:03d}" for index in range(1, 5))


def test_candidate_filtering_handles_null_receiver_account_id() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_counterparty_transactions_fixture()
    )

    assert candidates.loc[candidates["transaction_id"] == "TXN_STRUCT_CP_001"].shape[0] == 1


def test_candidate_filtering_handles_null_counterparty_id_when_receiver_exists() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_counterparty_transactions_fixture()
    )

    assert candidates.loc[candidates["transaction_id"] == "TXN_STRUCT_INTERNAL_001"].shape[0] == 1


def test_mixed_internal_and_external_outbound_payments_can_trigger_when_enabled() -> None:
    alerts = run_structuring_rule(
        build_structuring_counterparty_transactions_fixture(),
        build_structuring_accounts_fixture(),
    )

    assert len(alerts) == 1
