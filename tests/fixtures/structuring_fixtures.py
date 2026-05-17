"""Deterministic fixtures for structuring rule tests."""

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


def build_structuring_accounts_fixture() -> pd.DataFrame:
    """Return account context used to attach customers to structuring alerts."""

    return pd.DataFrame(
        [
            {
                "account_id": "ACC_STRUCT_001",
                "customer_id": "CUST_STRUCT_001",
                "account_type": "checking",
                "account_status": "active",
                "currency": "USD",
                "home_country": "US",
            },
            {
                "account_id": "ACC_STRUCT_002",
                "customer_id": "CUST_STRUCT_002",
                "account_type": "checking",
                "account_status": "active",
                "currency": "USD",
                "home_country": "US",
            },
            {
                "account_id": "ACC_BENIGN_001",
                "customer_id": "CUST_BENIGN_001",
                "account_type": "savings",
                "account_status": "active",
                "currency": "USD",
                "home_country": "US",
            },
            {
                "account_id": "ACC_INTERNAL_001",
                "customer_id": "CUST_INTERNAL_001",
                "account_type": "checking",
                "account_status": "active",
                "currency": "USD",
                "home_country": "US",
            },
        ]
    )


def build_structuring_trigger_transactions_fixture(
    account_id: str = "ACC_STRUCT_001",
    start_timestamp: str = "2025-01-10 09:00:00",
    count: int = 8,
    amount: float = 9500.0,
) -> pd.DataFrame:
    """Return exactly-count below-threshold outbound transfers that should trigger."""

    start = pd.Timestamp(start_timestamp, tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_STRUCT_TRIGGER_{index:03d}",
            sender_account_id=account_id,
            receiver_account_id="ACC_INTERNAL_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=amount,
            transaction_type="wire",
            typology_label="structuring",
            suspicious=True,
        )
        for index in range(1, count + 1)
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_structuring_non_trigger_transactions_fixture() -> pd.DataFrame:
    """Return benign and excluded transactions that should not trigger structuring."""

    start = pd.Timestamp("2025-01-11 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_STRUCT_NON_TRIGGER_{index:03d}",
            sender_account_id="ACC_BENIGN_001",
            receiver_account_id="ACC_INTERNAL_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=9500.0,
            transaction_type="wire",
        )
        for index in range(1, 8)
    ]
    rows.extend(
        [
            _transaction_row(
                transaction_id="TXN_STRUCT_NON_TRIGGER_ABOVE",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id="ACC_INTERNAL_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(days=3),
                amount=10500.0,
                transaction_type="wire",
            ),
            _transaction_row(
                transaction_id="TXN_STRUCT_NON_TRIGGER_AT_THRESHOLD",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id="ACC_INTERNAL_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(days=4),
                amount=10000.0,
                transaction_type="wire",
            ),
            _transaction_row(
                transaction_id="TXN_STRUCT_NON_TRIGGER_BELOW_MARGIN",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id="ACC_INTERNAL_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(days=5),
                amount=8999.99,
                transaction_type="wire",
            ),
            _transaction_row(
                transaction_id="TXN_STRUCT_NON_TRIGGER_TYPE",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id="ACC_INTERNAL_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(days=6),
                amount=9500.0,
                transaction_type="card",
            ),
        ]
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_structuring_boundary_transactions_fixture() -> pd.DataFrame:
    """Return threshold boundary examples around margin and reporting threshold."""

    start = pd.Timestamp("2025-01-12 09:00:00", tz="UTC")
    rows = [
        ("TXN_STRUCT_BOUNDARY_001", 8999.99),
        ("TXN_STRUCT_BOUNDARY_002", 9000.00),
        ("TXN_STRUCT_BOUNDARY_003", 9999.99),
        ("TXN_STRUCT_BOUNDARY_004", 10000.00),
        ("TXN_STRUCT_BOUNDARY_005", 10000.01),
    ]
    return pd.DataFrame(
        [
            _transaction_row(
                transaction_id=transaction_id,
                sender_account_id="ACC_STRUCT_001",
                receiver_account_id="ACC_INTERNAL_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(minutes=index),
                amount=amount,
                transaction_type="wire",
            )
            for index, (transaction_id, amount) in enumerate(rows)
        ],
        columns=TRANSACTION_COLUMNS,
    )


def build_structuring_multi_account_transactions_fixture() -> pd.DataFrame:
    """Return two triggering accounts plus one benign account with separable evidence."""

    start = pd.Timestamp("2025-01-13 09:00:00", tz="UTC")
    rows: list[dict[str, object]] = []
    for account_suffix, account_id in (("A", "ACC_STRUCT_001"), ("B", "ACC_STRUCT_002")):
        for index in range(1, 9):
            rows.append(
                _transaction_row(
                    transaction_id=f"TXN_STRUCT_MULTI_{account_suffix}_{index:03d}",
                    sender_account_id=account_id,
                    receiver_account_id="ACC_INTERNAL_001",
                    counterparty_id=None,
                    timestamp=start + pd.Timedelta(hours=index - 1),
                    amount=9500.0,
                    transaction_type="wire",
                    typology_label="structuring",
                    suspicious=True,
                )
            )
    for index in range(1, 8):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_STRUCT_MULTI_BENIGN_{index:03d}",
                sender_account_id="ACC_BENIGN_001",
                receiver_account_id="ACC_INTERNAL_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(hours=index - 1),
                amount=9500.0,
                transaction_type="wire",
            )
        )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_structuring_overlapping_window_transactions_fixture() -> pd.DataFrame:
    """Return overlapping candidate windows where the strongest window is deterministic."""

    start = pd.Timestamp("2025-01-14 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_STRUCT_OVERLAP_{index:03d}",
            sender_account_id="ACC_STRUCT_001",
            receiver_account_id="ACC_INTERNAL_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=9500.0 if index < 9 else 9600.0,
            transaction_type="wire",
            typology_label="structuring",
            suspicious=True,
        )
        for index in range(1, 10)
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_structuring_counterparty_transactions_fixture() -> pd.DataFrame:
    """Return external counterparty and internal receiver payments for inclusion tests."""

    start = pd.Timestamp("2025-01-15 09:00:00", tz="UTC")
    rows: list[dict[str, object]] = []
    for index in range(1, 5):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_STRUCT_CP_{index:03d}",
                sender_account_id="ACC_STRUCT_001",
                receiver_account_id=None,
                counterparty_id=f"CP_STRUCT_{index:03d}",
                timestamp=start + pd.Timedelta(hours=index - 1),
                amount=9500.0,
                transaction_type="wire",
                destination_country="GB",
                typology_label="structuring",
                suspicious=True,
            )
        )
    for index in range(1, 5):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_STRUCT_INTERNAL_{index:03d}",
                sender_account_id="ACC_STRUCT_001",
                receiver_account_id="ACC_INTERNAL_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(hours=4 + index),
                amount=9500.0,
                transaction_type="wire",
                typology_label="structuring",
                suspicious=True,
            )
        )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_structuring_invalid_transactions_fixture() -> pd.DataFrame:
    """Return malformed rows that normalisation should drop before rule detection."""

    start = pd.Timestamp("2025-01-16 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=None,
            sender_account_id="ACC_STRUCT_001",
            receiver_account_id="ACC_INTERNAL_001",
            counterparty_id=None,
            timestamp=start,
            amount=9500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_STRUCT_INVALID_SENDER",
            sender_account_id=None,
            receiver_account_id="ACC_INTERNAL_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=1),
            amount=9500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_STRUCT_INVALID_TIMESTAMP",
            sender_account_id="ACC_STRUCT_001",
            receiver_account_id="ACC_INTERNAL_001",
            counterparty_id=None,
            timestamp="not-a-timestamp",
            amount=9500.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_STRUCT_INVALID_AMOUNT_TEXT",
            sender_account_id="ACC_STRUCT_001",
            receiver_account_id="ACC_INTERNAL_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=3),
            amount="not-a-number",
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_STRUCT_INVALID_AMOUNT_NEGATIVE",
            sender_account_id="ACC_STRUCT_001",
            receiver_account_id="ACC_INTERNAL_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=4),
            amount=-10.0,
            transaction_type="wire",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def _transaction_row(
    *,
    transaction_id: str | None,
    sender_account_id: str | None,
    receiver_account_id: str | None,
    counterparty_id: str | None,
    timestamp: object,
    amount: object,
    transaction_type: str,
    destination_country: str = "US",
    typology_label: str | None = None,
    suspicious: bool = False,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender_account_id,
        "receiver_account_id": receiver_account_id,
        "counterparty_id": counterparty_id,
        "device_id": "DEV_STRUCT_001",
        "transaction_timestamp": timestamp,
        "amount": amount,
        "currency": "USD",
        "transaction_type": transaction_type,
        "channel": "online",
        "origin_country": "US",
        "destination_country": destination_country,
        "is_cross_border": destination_country != "US",
        "is_labelled_suspicious": suspicious,
        "typology_label": typology_label,
        "source_file": "structuring_fixture",
    }
