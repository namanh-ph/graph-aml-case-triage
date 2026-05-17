"""Deterministic fixtures for rapid movement rule tests."""

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


def build_rapid_movement_accounts_fixture() -> pd.DataFrame:
    """Return pass-through, source, recipient, and benign account context."""

    rows = [
        _account_row("ACC_PASS_001", "CUST_PASS_001"),
        _account_row("ACC_PASS_002", "CUST_PASS_002"),
        _account_row("ACC_SOURCE_001", "CUST_SOURCE_001"),
        _account_row("ACC_SOURCE_002", "CUST_SOURCE_002"),
        _account_row("ACC_RECIPIENT_001", "CUST_RECIPIENT_001"),
        _account_row("ACC_RECIPIENT_002", "CUST_RECIPIENT_002"),
        _account_row("ACC_RECIPIENT_003", "CUST_RECIPIENT_003"),
        _account_row("ACC_BENIGN_001", "CUST_BENIGN_001"),
    ]
    return pd.DataFrame(rows)


def build_rapid_movement_trigger_transactions_fixture(
    account_id: str = "ACC_PASS_001",
    start_timestamp: str = "2025-01-25 09:00:00",
    received_amount: float = 10000.0,
    sent_amount: float = 9000.0,
) -> pd.DataFrame:
    """Return one inbound transfer followed by sufficient outbound movement."""

    start = pd.Timestamp(start_timestamp, tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_RM_IN_001",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id=account_id,
            counterparty_id=None,
            timestamp=start,
            amount=received_amount,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_OUT_001",
            sender_account_id=account_id,
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=4),
            amount=sent_amount,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_rapid_movement_non_trigger_transactions_fixture() -> pd.DataFrame:
    """Return benign or excluded activity that should not trigger rapid movement."""

    start = pd.Timestamp("2025-01-26 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_RM_NON_TRIGGER_IN",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_BENIGN_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_RM_NON_TRIGGER_LOW_OUT",
            sender_account_id="ACC_BENIGN_001",
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=5),
            amount=5000.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_RM_NON_TRIGGER_LATE_OUT",
            sender_account_id="ACC_BENIGN_001",
            receiver_account_id="ACC_RECIPIENT_002",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=60),
            amount=9000.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_RM_NON_TRIGGER_TYPE",
            sender_account_id="ACC_BENIGN_001",
            receiver_account_id="ACC_RECIPIENT_003",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=6),
            amount=9000.0,
            transaction_type="card",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_rapid_movement_multi_account_transactions_fixture() -> pd.DataFrame:
    """Return two distinct pass-through accounts plus benign activity."""

    start = pd.Timestamp("2025-01-27 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_RM_MULTI_A_IN",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_MULTI_A_OUT",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=3),
            amount=9200.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_MULTI_B_IN",
            sender_account_id="ACC_SOURCE_002",
            receiver_account_id="ACC_PASS_002",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=1),
            amount=8000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_MULTI_B_OUT",
            sender_account_id="ACC_PASS_002",
            receiver_account_id="ACC_RECIPIENT_002",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=4),
            amount=7600.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_MULTI_BENIGN",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_BENIGN_001",
            counterparty_id=None,
            timestamp=start,
            amount=500.0,
            transaction_type="transfer",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_rapid_movement_overlapping_window_transactions_fixture() -> pd.DataFrame:
    """Return overlapping rapid movement windows with deterministic strongest selection."""

    start = pd.Timestamp("2025-01-28 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_RM_OVERLAP_IN_001",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_OVERLAP_OUT_001",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=4),
            amount=9000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_OVERLAP_IN_002",
            sender_account_id="ACC_SOURCE_002",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=8),
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_OVERLAP_OUT_002",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_RECIPIENT_002",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=12),
            amount=19200.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_rapid_movement_counterparty_transactions_fixture() -> pd.DataFrame:
    """Return rapid movement where the outflow recipient is an external counterparty."""

    start = pd.Timestamp("2025-01-29 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_RM_COUNTERPARTY_IN",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_RM_COUNTERPARTY_OUT",
            sender_account_id="ACC_PASS_001",
            receiver_account_id=None,
            counterparty_id="CP_RM_001",
            timestamp=start + pd.Timedelta(hours=2),
            amount=9500.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_rapid_movement_invalid_transactions_fixture() -> pd.DataFrame:
    """Return malformed rapid movement rows that normalisation should drop."""

    start = pd.Timestamp("2025-01-30 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=None,
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_RM_INVALID_TIMESTAMP",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp="not-a-timestamp",
            amount=10000.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_RM_INVALID_AMOUNT",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=1),
            amount="not-a-number",
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_RM_INVALID_RECIPIENT",
            sender_account_id="ACC_PASS_001",
            receiver_account_id=None,
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=2),
            amount=9000.0,
            transaction_type="wire",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


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
    *,
    transaction_id: str | None,
    sender_account_id: str | None,
    receiver_account_id: str | None,
    counterparty_id: str | None,
    timestamp: object,
    amount: object,
    transaction_type: str,
    suspicious: bool = False,
    typology_label: str | None = None,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender_account_id,
        "receiver_account_id": receiver_account_id,
        "counterparty_id": counterparty_id,
        "device_id": "DEV_RM_001",
        "transaction_timestamp": timestamp,
        "amount": amount,
        "currency": "USD",
        "transaction_type": transaction_type,
        "channel": "online",
        "origin_country": "US",
        "destination_country": "US",
        "is_cross_border": False,
        "is_labelled_suspicious": suspicious,
        "typology_label": typology_label,
        "source_file": "rapid_movement_fixture",
    }
