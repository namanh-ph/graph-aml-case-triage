"""Deterministic fixtures for circular flow detection tests."""

from __future__ import annotations

import pandas as pd

TRANSACTION_COLUMNS = (
    "transaction_id",
    "sender_account_id",
    "receiver_account_id",
    "counterparty_id",
    "device_id",
    "transaction_timestamp",
    "amount",
    "currency",
    "transaction_type",
    "channel",
    "origin_country",
    "destination_country",
    "is_cross_border",
    "is_labelled_suspicious",
    "typology_label",
    "source_file",
)


def build_circular_flow_accounts_fixture() -> pd.DataFrame:
    """Return account context for later circular-flow alert conversion tests."""

    return pd.DataFrame(
        [
            _account_row("ACC_CF_A", "CUST_CF_A"),
            _account_row("ACC_CF_B", "CUST_CF_B"),
            _account_row("ACC_CF_C", "CUST_CF_C"),
            _account_row("ACC_CF_D", "CUST_CF_D"),
            _account_row("ACC_CF_E", "CUST_CF_E"),
            _account_row("ACC_CF_BENIGN", "CUST_CF_BENIGN"),
        ]
    )


def build_circular_flow_two_hop_transactions_fixture() -> pd.DataFrame:
    """Return a compact two-hop directed cycle fixture."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row("TXN_CF_2HOP_001", "ACC_CF_A", "ACC_CF_B", None, start, 5000.0),
        _transaction_row(
            "TXN_CF_2HOP_002",
            "ACC_CF_B",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=1),
            5000.0,
        ),
    ]
    return _frame(rows)


def build_circular_flow_three_hop_transactions_fixture() -> pd.DataFrame:
    """Return a compact three-hop directed cycle fixture."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row("TXN_CF_3HOP_001", "ACC_CF_A", "ACC_CF_B", None, start, 4000.0),
        _transaction_row(
            "TXN_CF_3HOP_002",
            "ACC_CF_B",
            "ACC_CF_C",
            None,
            start + pd.Timedelta(hours=1),
            4000.0,
        ),
        _transaction_row(
            "TXN_CF_3HOP_003",
            "ACC_CF_C",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=2),
            4000.0,
        ),
    ]
    return _frame(rows)


def build_circular_flow_four_hop_transactions_fixture() -> pd.DataFrame:
    """Return a compact four-hop directed cycle fixture."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row("TXN_CF_4HOP_001", "ACC_CF_A", "ACC_CF_B", None, start, 3000.0),
        _transaction_row(
            "TXN_CF_4HOP_002",
            "ACC_CF_B",
            "ACC_CF_C",
            None,
            start + pd.Timedelta(hours=1),
            3000.0,
        ),
        _transaction_row(
            "TXN_CF_4HOP_003",
            "ACC_CF_C",
            "ACC_CF_D",
            None,
            start + pd.Timedelta(hours=2),
            3000.0,
        ),
        _transaction_row(
            "TXN_CF_4HOP_004",
            "ACC_CF_D",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=3),
            3000.0,
        ),
    ]
    return _frame(rows)


def build_circular_flow_non_trigger_transactions_fixture() -> pd.DataFrame:
    """Return an acyclic transaction chain fixture."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row("TXN_CF_BENIGN_001", "ACC_CF_A", "ACC_CF_B", None, start, 2000.0),
        _transaction_row(
            "TXN_CF_BENIGN_002",
            "ACC_CF_B",
            "ACC_CF_C",
            None,
            start + pd.Timedelta(hours=1),
            2000.0,
        ),
        _transaction_row(
            "TXN_CF_BENIGN_003",
            "ACC_CF_D",
            "ACC_CF_E",
            None,
            start + pd.Timedelta(hours=2),
            2000.0,
        ),
    ]
    return _frame(rows)


def build_circular_flow_overlong_cycle_transactions_fixture() -> pd.DataFrame:
    """Return a five-hop directed cycle that exceeds the default hop limit."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row("TXN_CF_OVERLONG_001", "ACC_CF_A", "ACC_CF_B", None, start, 1000.0),
        _transaction_row(
            "TXN_CF_OVERLONG_002",
            "ACC_CF_B",
            "ACC_CF_C",
            None,
            start + pd.Timedelta(hours=1),
            1000.0,
        ),
        _transaction_row(
            "TXN_CF_OVERLONG_003",
            "ACC_CF_C",
            "ACC_CF_D",
            None,
            start + pd.Timedelta(hours=2),
            1000.0,
        ),
        _transaction_row(
            "TXN_CF_OVERLONG_004",
            "ACC_CF_D",
            "ACC_CF_E",
            None,
            start + pd.Timedelta(hours=3),
            1000.0,
        ),
        _transaction_row(
            "TXN_CF_OVERLONG_005",
            "ACC_CF_E",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=4),
            1000.0,
        ),
    ]
    return _frame(rows)


def build_circular_flow_time_span_boundary_transactions_fixture() -> pd.DataFrame:
    """Return cycles exactly at and just beyond the default time-span boundary."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row("TXN_CF_BOUNDARY_001", "ACC_CF_A", "ACC_CF_B", None, start, 5000.0),
        _transaction_row(
            "TXN_CF_BOUNDARY_002",
            "ACC_CF_B",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=168),
            5000.0,
        ),
        _transaction_row("TXN_CF_BOUNDARY_LATE_001", "ACC_CF_C", "ACC_CF_D", None, start, 5000.0),
        _transaction_row(
            "TXN_CF_BOUNDARY_LATE_002",
            "ACC_CF_D",
            "ACC_CF_C",
            None,
            start + pd.Timedelta(hours=168, seconds=1),
            5000.0,
        ),
    ]
    return _frame(rows)


def build_circular_flow_multi_cycle_transactions_fixture() -> pd.DataFrame:
    """Return several small cycles for ordering and limit tests."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row("TXN_CF_MULTI_AB_001", "ACC_CF_A", "ACC_CF_B", None, start, 1000.0),
        _transaction_row(
            "TXN_CF_MULTI_AB_002",
            "ACC_CF_B",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=1),
            1000.0,
        ),
        _transaction_row(
            "TXN_CF_MULTI_AC_001",
            "ACC_CF_A",
            "ACC_CF_C",
            None,
            start + pd.Timedelta(hours=2),
            2000.0,
        ),
        _transaction_row(
            "TXN_CF_MULTI_AC_002",
            "ACC_CF_C",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=3),
            2000.0,
        ),
        _transaction_row(
            "TXN_CF_MULTI_AD_001",
            "ACC_CF_A",
            "ACC_CF_D",
            None,
            start + pd.Timedelta(hours=4),
            3000.0,
        ),
        _transaction_row(
            "TXN_CF_MULTI_AD_002",
            "ACC_CF_D",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=5),
            3000.0,
        ),
        _transaction_row(
            "TXN_CF_MULTI_BE_001",
            "ACC_CF_B",
            "ACC_CF_E",
            None,
            start + pd.Timedelta(hours=6),
            4000.0,
        ),
        _transaction_row(
            "TXN_CF_MULTI_BE_002",
            "ACC_CF_E",
            "ACC_CF_B",
            None,
            start + pd.Timedelta(hours=7),
            4000.0,
        ),
    ]
    return _frame(rows)


def build_circular_flow_counterparty_transactions_fixture() -> pd.DataFrame:
    """Return a counterparty-like cycle that only closes when those edges are enabled."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            "TXN_CF_COUNTERPARTY_001",
            "ACC_CF_A",
            None,
            "CP_CF_001",
            start,
            2500.0,
        ),
        _transaction_row(
            "TXN_CF_COUNTERPARTY_002",
            "CP:CP_CF_001",
            "ACC_CF_A",
            None,
            start + pd.Timedelta(hours=1),
            2500.0,
        ),
    ]
    return _frame(rows)


def build_circular_flow_invalid_transactions_fixture() -> pd.DataFrame:
    """Return malformed rows for preparation and invalid-input tests."""

    rows = [
        _transaction_row(None, "ACC_CF_A", "ACC_CF_B", None, "not-a-timestamp", 1000.0),
        _transaction_row(
            "TXN_CF_INVALID_AMOUNT",
            "ACC_CF_A",
            "ACC_CF_B",
            None,
            pd.Timestamp("2025-01-10 09:00:00", tz="UTC"),
            "not-a-number",
        ),
        _transaction_row(
            "TXN_CF_INVALID_TYPE",
            "ACC_CF_A",
            "ACC_CF_B",
            None,
            pd.Timestamp("2025-01-10 10:00:00", tz="UTC"),
            1000.0,
            transaction_type="cash_deposit",
        ),
    ]
    return _frame(rows)


def _account_row(account_id: str, customer_id: str) -> dict[str, object]:
    return {
        "account_id": account_id,
        "customer_id": customer_id,
        "account_type": "checking",
        "account_status": "active",
        "currency": "USD",
        "home_country": "US",
    }


def _transaction_row(
    transaction_id: str | None,
    sender_account_id: str | None,
    receiver_account_id: str | None,
    counterparty_id: str | None,
    timestamp: object,
    amount: object,
    transaction_type: str = "transfer",
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender_account_id,
        "receiver_account_id": receiver_account_id,
        "counterparty_id": counterparty_id,
        "device_id": "DEV_CF_001",
        "transaction_timestamp": timestamp,
        "amount": amount,
        "currency": "USD",
        "transaction_type": transaction_type,
        "channel": "online",
        "origin_country": "US",
        "destination_country": "US",
        "is_cross_border": False,
        "is_labelled_suspicious": True,
        "typology_label": "circular_flow",
        "source_file": "circular_flow_fixture",
    }


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)
