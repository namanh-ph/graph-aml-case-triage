"""Deterministic fixtures for fan-out rule tests."""

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


def build_fan_out_accounts_fixture() -> pd.DataFrame:
    """Return sending and receiving account context for fan-out alerts."""

    rows = [
        _account_row("ACC_DISPERSE_001", "CUST_DISPERSE_001"),
        _account_row("ACC_DISPERSE_002", "CUST_DISPERSE_002"),
        _account_row("ACC_BENIGN_001", "CUST_BENIGN_001"),
    ]
    rows.extend(
        _account_row(f"ACC_FAN_RECIPIENT_{index:03d}", f"CUST_FAN_RECIPIENT_{index:03d}")
        for index in range(1, 41)
    )
    return pd.DataFrame(rows)


def build_fan_out_trigger_transactions_fixture(
    sender_account_id: str = "ACC_DISPERSE_001",
    start_timestamp: str = "2025-01-20 09:00:00",
    unique_recipient_count: int = 20,
    amount: float = 500.0,
) -> pd.DataFrame:
    """Return exactly-threshold unique recipients from one sending account."""

    start = pd.Timestamp(start_timestamp, tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_FAN_OUT_TRIGGER_{index:03d}",
            sender_account_id=sender_account_id,
            receiver_account_id=f"ACC_FAN_RECIPIENT_{index:03d}",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=amount,
            transaction_type="transfer",
            suspicious=True,
            typology_label="fan_out",
        )
        for index in range(1, unique_recipient_count + 1)
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_out_non_trigger_transactions_fixture() -> pd.DataFrame:
    """Return benign or excluded transactions that should not trigger fan-out."""

    start = pd.Timestamp("2025-01-21 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_FAN_OUT_NON_TRIGGER_{index:03d}",
            sender_account_id="ACC_BENIGN_001",
            receiver_account_id=f"ACC_FAN_RECIPIENT_{index:03d}",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=500.0,
            transaction_type="transfer",
        )
        for index in range(1, 20)
    ]
    rows.extend(
        [
            _transaction_row(
                transaction_id="TXN_FAN_OUT_NON_TRIGGER_SELF",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id="ACC_BENIGN_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(days=2),
                amount=500.0,
                transaction_type="transfer",
            ),
            _transaction_row(
                transaction_id="TXN_FAN_OUT_NON_TRIGGER_TYPE",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id="ACC_FAN_RECIPIENT_020",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(days=3),
                amount=500.0,
                transaction_type="card",
            ),
        ]
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_out_multi_sender_transactions_fixture() -> pd.DataFrame:
    """Return two triggering sending accounts plus benign activity."""

    start = pd.Timestamp("2025-01-22 09:00:00", tz="UTC")
    rows: list[dict[str, object]] = []
    for sender_marker, sender_account_id, recipient_offset in (
        ("A", "ACC_DISPERSE_001", 0),
        ("B", "ACC_DISPERSE_002", 20),
    ):
        for index in range(1, 21):
            recipient_index = recipient_offset + index
            rows.append(
                _transaction_row(
                    transaction_id=f"TXN_FAN_OUT_MULTI_{sender_marker}_{index:03d}",
                    sender_account_id=sender_account_id,
                    receiver_account_id=f"ACC_FAN_RECIPIENT_{recipient_index:03d}",
                    counterparty_id=None,
                    timestamp=start + pd.Timedelta(hours=index - 1),
                    amount=500.0,
                    transaction_type="wire",
                    suspicious=True,
                    typology_label="fan_out",
                )
            )
    for index in range(1, 5):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_FAN_OUT_MULTI_BENIGN_{index:03d}",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id=f"ACC_FAN_RECIPIENT_{index:03d}",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(hours=index - 1),
                amount=500.0,
                transaction_type="wire",
            )
        )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_out_overlapping_window_transactions_fixture() -> pd.DataFrame:
    """Return overlapping fan-out windows where strongest selection is deterministic."""

    start = pd.Timestamp("2025-01-23 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_FAN_OUT_OVERLAP_{index:03d}",
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id=f"ACC_FAN_RECIPIENT_{index:03d}",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=500.0 if index < 21 else 750.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="fan_out",
        )
        for index in range(1, 22)
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_out_counterparty_transactions_fixture() -> pd.DataFrame:
    """Return external counterparty recipients for fan-out candidate tests."""

    start = pd.Timestamp("2025-01-24 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_FAN_OUT_COUNTERPARTY_{index:03d}",
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id=None,
            counterparty_id=f"CP_FAN_OUT_{index:03d}",
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=500.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="fan_out",
        )
        for index in range(1, 21)
    ]
    rows.append(
        _transaction_row(
            transaction_id="TXN_FAN_OUT_COUNTERPARTY_INTERNAL",
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id="ACC_FAN_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=21),
            amount=500.0,
            transaction_type="transfer",
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_out_invalid_transactions_fixture() -> pd.DataFrame:
    """Return malformed fan-out rows that normalisation should drop."""

    start = pd.Timestamp("2025-01-25 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=None,
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id="ACC_FAN_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start,
            amount=500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_FAN_OUT_INVALID_SENDER",
            sender_account_id=None,
            receiver_account_id="ACC_FAN_RECIPIENT_002",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=1),
            amount=500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_FAN_OUT_INVALID_RECIPIENT",
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id=None,
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=2),
            amount=500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_FAN_OUT_INVALID_TIMESTAMP",
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id="ACC_FAN_RECIPIENT_003",
            counterparty_id=None,
            timestamp="not-a-timestamp",
            amount=500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_FAN_OUT_INVALID_AMOUNT",
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id="ACC_FAN_RECIPIENT_004",
            counterparty_id=None,
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
        "device_id": "DEV_FAN_OUT_001",
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
        "source_file": "fan_out_fixture",
    }
