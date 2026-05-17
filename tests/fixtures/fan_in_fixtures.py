"""Deterministic fixtures for fan-in rule tests."""

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


def build_fan_in_accounts_fixture() -> pd.DataFrame:
    """Return receiving and sending account context for fan-in alerts."""

    rows = [
        _account_row("ACC_COLLECT_001", "CUST_COLLECT_001"),
        _account_row("ACC_COLLECT_002", "CUST_COLLECT_002"),
        _account_row("ACC_BENIGN_001", "CUST_BENIGN_001"),
    ]
    rows.extend(
        _account_row(f"ACC_FAN_SENDER_{index:03d}", f"CUST_FAN_SENDER_{index:03d}")
        for index in range(1, 31)
    )
    return pd.DataFrame(rows)


def build_fan_in_trigger_transactions_fixture(
    receiver_account_id: str = "ACC_COLLECT_001",
    start_timestamp: str = "2025-01-15 09:00:00",
    unique_sender_count: int = 15,
    amount: float = 500.0,
) -> pd.DataFrame:
    """Return exactly-threshold unique senders into one receiving account."""

    start = pd.Timestamp(start_timestamp, tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_FAN_IN_TRIGGER_{index:03d}",
            sender_account_id=f"ACC_FAN_SENDER_{index:03d}",
            receiver_account_id=receiver_account_id,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=amount,
            transaction_type="transfer",
            suspicious=True,
            typology_label="fan_in",
        )
        for index in range(1, unique_sender_count + 1)
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_in_non_trigger_transactions_fixture() -> pd.DataFrame:
    """Return benign or excluded transactions that should not trigger fan-in."""

    start = pd.Timestamp("2025-01-16 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_FAN_IN_NON_TRIGGER_{index:03d}",
            sender_account_id=f"ACC_FAN_SENDER_{index:03d}",
            receiver_account_id="ACC_BENIGN_001",
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=500.0,
            transaction_type="transfer",
        )
        for index in range(1, 15)
    ]
    rows.extend(
        [
            _transaction_row(
                transaction_id="TXN_FAN_IN_NON_TRIGGER_SELF",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id="ACC_BENIGN_001",
                timestamp=start + pd.Timedelta(days=2),
                amount=500.0,
                transaction_type="transfer",
            ),
            _transaction_row(
                transaction_id="TXN_FAN_IN_NON_TRIGGER_TYPE",
                sender_account_id="ACC_FAN_SENDER_020",
                receiver_account_id="ACC_BENIGN_001",
                timestamp=start + pd.Timedelta(days=3),
                amount=500.0,
                transaction_type="card",
            ),
        ]
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_in_multi_receiver_transactions_fixture() -> pd.DataFrame:
    """Return two triggering receiver accounts plus benign activity."""

    start = pd.Timestamp("2025-01-17 09:00:00", tz="UTC")
    rows: list[dict[str, object]] = []
    for receiver_marker, receiver_account_id, sender_offset in (
        ("A", "ACC_COLLECT_001", 0),
        ("B", "ACC_COLLECT_002", 15),
    ):
        for index in range(1, 16):
            sender_index = sender_offset + index
            rows.append(
                _transaction_row(
                    transaction_id=f"TXN_FAN_IN_MULTI_{receiver_marker}_{index:03d}",
                    sender_account_id=f"ACC_FAN_SENDER_{sender_index:03d}",
                    receiver_account_id=receiver_account_id,
                    timestamp=start + pd.Timedelta(hours=index - 1),
                    amount=500.0,
                    transaction_type="wire",
                    suspicious=True,
                    typology_label="fan_in",
                )
            )
    for index in range(1, 5):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_FAN_IN_MULTI_BENIGN_{index:03d}",
                sender_account_id=f"ACC_FAN_SENDER_{index:03d}",
                receiver_account_id="ACC_BENIGN_001",
                timestamp=start + pd.Timedelta(hours=index - 1),
                amount=500.0,
                transaction_type="wire",
            )
        )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_in_overlapping_window_transactions_fixture() -> pd.DataFrame:
    """Return overlapping fan-in windows where strongest selection is deterministic."""

    start = pd.Timestamp("2025-01-18 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_FAN_IN_OVERLAP_{index:03d}",
            sender_account_id=f"ACC_FAN_SENDER_{index:03d}",
            receiver_account_id="ACC_COLLECT_001",
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=500.0 if index < 16 else 750.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="fan_in",
        )
        for index in range(1, 17)
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_in_invalid_transactions_fixture() -> pd.DataFrame:
    """Return malformed fan-in rows that normalisation should drop."""

    start = pd.Timestamp("2025-01-19 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=None,
            sender_account_id="ACC_FAN_SENDER_001",
            receiver_account_id="ACC_COLLECT_001",
            timestamp=start,
            amount=500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_FAN_IN_INVALID_SENDER",
            sender_account_id=None,
            receiver_account_id="ACC_COLLECT_001",
            timestamp=start + pd.Timedelta(hours=1),
            amount=500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_FAN_IN_INVALID_RECEIVER",
            sender_account_id="ACC_FAN_SENDER_002",
            receiver_account_id=None,
            timestamp=start + pd.Timedelta(hours=2),
            amount=500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_FAN_IN_INVALID_TIMESTAMP",
            sender_account_id="ACC_FAN_SENDER_003",
            receiver_account_id="ACC_COLLECT_001",
            timestamp="not-a-timestamp",
            amount=500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_FAN_IN_INVALID_AMOUNT",
            sender_account_id="ACC_FAN_SENDER_004",
            receiver_account_id="ACC_COLLECT_001",
            timestamp=start + pd.Timedelta(hours=4),
            amount="not-a-number",
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
        "counterparty_id": None,
        "device_id": "DEV_FAN_IN_001",
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
        "source_file": "fan_in_fixture",
    }
