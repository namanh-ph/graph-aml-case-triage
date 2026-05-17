"""Tests for circular flow cycle canonicalisation helpers."""

import pytest

from graph_aml.rules import (
    RuleInputError,
    build_cycle_id,
    canonicalise_cycle_accounts,
    normalise_cycle_path,
)


def test_canonicalisation_rotates_to_lexicographically_smallest_account() -> None:
    assert canonicalise_cycle_accounts(("ACC_C", "ACC_A", "ACC_B")) == (
        "ACC_A",
        "ACC_B",
        "ACC_C",
    )


def test_canonicalisation_preserves_direction() -> None:
    assert canonicalise_cycle_accounts(("ACC_B", "ACC_A", "ACC_C")) == (
        "ACC_A",
        "ACC_C",
        "ACC_B",
    )


def test_canonicalisation_removes_duplicated_closing_node() -> None:
    assert canonicalise_cycle_accounts(("ACC_A", "ACC_B", "ACC_A")) == (
        "ACC_A",
        "ACC_B",
    )


def test_equivalent_rotations_produce_same_canonical_cycle() -> None:
    assert canonicalise_cycle_accounts(("ACC_A", "ACC_B", "ACC_C")) == (
        canonicalise_cycle_accounts(("ACC_B", "ACC_C", "ACC_A"))
    )


def test_reversed_cycles_remain_distinct() -> None:
    assert canonicalise_cycle_accounts(("ACC_A", "ACC_B", "ACC_C")) != (
        canonicalise_cycle_accounts(("ACC_A", "ACC_C", "ACC_B"))
    )


def test_normalise_cycle_path_appends_starting_account_at_end() -> None:
    assert normalise_cycle_path(("ACC_B", "ACC_A")) == "ACC_A -> ACC_B -> ACC_A"


def test_build_cycle_id_is_deterministic_for_equivalent_cycles() -> None:
    first = build_cycle_id(("ACC_A", "ACC_B"), ("TXN_2", "TXN_1"))
    second = build_cycle_id(("ACC_B", "ACC_A"), ("TXN_1", "TXN_2"))

    assert first == second
    assert first.startswith("CF_")


def test_changing_evidence_ids_changes_cycle_id() -> None:
    first = build_cycle_id(("ACC_A", "ACC_B"), ("TXN_1", "TXN_2"))
    second = build_cycle_id(("ACC_A", "ACC_B"), ("TXN_1", "TXN_3"))

    assert first != second


@pytest.mark.parametrize(
    "cycle",
    [
        (),
        ("ACC_A",),
        ("ACC_A", ""),
        ("ACC_A", "ACC_B", "ACC_B"),
    ],
)
def test_invalid_cycle_inputs_raise(cycle: tuple[str, ...]) -> None:
    with pytest.raises(RuleInputError):
        canonicalise_cycle_accounts(cycle)


def test_build_cycle_id_requires_evidence_ids() -> None:
    with pytest.raises(RuleInputError):
        build_cycle_id(("ACC_A", "ACC_B"), ())
