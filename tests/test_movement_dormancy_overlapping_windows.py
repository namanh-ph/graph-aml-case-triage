"""Overlapping-window selection tests for movement and dormancy rules."""

from graph_aml.rules import (
    detect_dormant_reactivation_windows,
    detect_rapid_movement_windows,
)
from graph_aml.rules.dormant_reactivation import _dormant_reactivation_window_strength_key
from graph_aml.rules.rapid_movement import _rapid_movement_window_strength_key
from tests.fixtures.movement_dormancy_fixtures import (
    build_movement_dormancy_overlapping_window_transactions_fixture,
)


def test_rapid_overlapping_windows_are_deduplicated_deterministically() -> None:
    output = detect_rapid_movement_windows(
        build_movement_dormancy_overlapping_window_transactions_fixture()
    )

    assert len(output.loc[output["account_id"].eq("ACC_PASS_001")]) == 1


def test_rapid_strongest_window_prioritises_highest_outflow_ratio() -> None:
    output = detect_rapid_movement_windows(
        build_movement_dormancy_overlapping_window_transactions_fixture()
    )

    assert output.loc[0, "outflow_ratio"] == 1.92


def test_rapid_ties_prioritise_highest_total_sent_out() -> None:
    first = _rapid_item(outflow_ratio=0.9, total_sent_out=9000, total_received=10000)
    second = _rapid_item(outflow_ratio=0.9, total_sent_out=12000, total_received=14000)

    assert sorted([first, second], key=_rapid_movement_window_strength_key)[0] is second


def test_rapid_remaining_ties_prioritise_highest_total_received() -> None:
    first = _rapid_item(outflow_ratio=0.9, total_sent_out=9000, total_received=10000)
    second = _rapid_item(outflow_ratio=0.9, total_sent_out=9000, total_received=12000)

    assert sorted([first, second], key=_rapid_movement_window_strength_key)[0] is second


def test_rapid_final_ties_prioritise_earliest_window_start() -> None:
    first = _rapid_item(window_start="2025-01-01T00:00:00+00:00")
    second = _rapid_item(window_start="2025-01-02T00:00:00+00:00")

    assert sorted([second, first], key=_rapid_movement_window_strength_key)[0] is first


def test_dormant_overlapping_windows_are_deduplicated_deterministically() -> None:
    output = detect_dormant_reactivation_windows(
        build_movement_dormancy_overlapping_window_transactions_fixture()
    )

    assert len(output.loc[output["account_id"].eq("ACC_DORMANT_001")]) == 1


def test_dormant_strongest_window_prioritises_highest_dormant_days() -> None:
    first = _dormant_item(dormant_days=120)
    second = _dormant_item(dormant_days=150)

    assert sorted([first, second], key=_dormant_reactivation_window_strength_key)[0] is second


def test_dormant_ties_prioritise_highest_total_outbound_amount() -> None:
    first = _dormant_item(dormant_days=120, total_outbound=10000)
    second = _dormant_item(dormant_days=120, total_outbound=15000)

    assert sorted([first, second], key=_dormant_reactivation_window_strength_key)[0] is second


def test_dormant_remaining_ties_prioritise_highest_transaction_count() -> None:
    first = _dormant_item(transaction_count=1)
    second = _dormant_item(transaction_count=2)

    assert sorted([first, second], key=_dormant_reactivation_window_strength_key)[0] is second


def test_dormant_final_ties_prioritise_earliest_window_start() -> None:
    first = _dormant_item(window_start="2025-01-01T00:00:00+00:00")
    second = _dormant_item(window_start="2025-01-02T00:00:00+00:00")

    assert sorted([second, first], key=_dormant_reactivation_window_strength_key)[0] is first


def _rapid_item(
    *,
    outflow_ratio: float = 0.9,
    total_sent_out: float = 9000.0,
    total_received: float = 10000.0,
    window_start: str = "2025-01-01T00:00:00+00:00",
) -> dict[str, object]:
    return {
        "outflow_ratio": outflow_ratio,
        "total_sent_out": total_sent_out,
        "total_received": total_received,
        "detection_window_start": window_start,
    }


def _dormant_item(
    *,
    dormant_days: int = 120,
    total_outbound: float = 10000.0,
    transaction_count: int = 1,
    window_start: str = "2025-01-01T00:00:00+00:00",
) -> dict[str, object]:
    return {
        "dormant_days_before_activity": dormant_days,
        "total_outbound_amount": total_outbound,
        "reactivation_transaction_count": transaction_count,
        "detection_window_start": window_start,
    }
