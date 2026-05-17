"""Deterministic joint fan-in and fan-out fixtures."""

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


def build_fan_flow_accounts_fixture() -> pd.DataFrame:
    """Return account context shared by joint fan-in and fan-out tests."""

    rows = [
        _account_row("ACC_COLLECT_001", "CUST_COLLECT_001"),
        _account_row("ACC_COLLECT_002", "CUST_COLLECT_002"),
        _account_row("ACC_DISPERSE_001", "CUST_DISPERSE_001"),
        _account_row("ACC_DISPERSE_002", "CUST_DISPERSE_002"),
        _account_row("ACC_BENIGN_001", "CUST_BENIGN_001"),
    ]
    rows.extend(
        _account_row(f"ACC_FLOW_SENDER_{index:03d}", f"CUST_FLOW_SENDER_{index:03d}")
        for index in range(1, 12)
    )
    rows.extend(
        _account_row(f"ACC_FLOW_RECEIVER_{index:03d}", f"CUST_FLOW_RECEIVER_{index:03d}")
        for index in range(1, 12)
    )
    return pd.DataFrame(rows)


def build_joint_fan_in_and_fan_out_transactions_fixture() -> pd.DataFrame:
    """Return separate fan-in and fan-out trigger patterns in one fixture."""

    rows = _fan_in_rows(
        prefix="TXN_FLOW_IN",
        receiver_account_id="ACC_COLLECT_001",
        start_timestamp="2025-02-01 09:00:00",
        count=4,
    )
    rows.extend(
        _fan_out_rows(
            prefix="TXN_FLOW_OUT",
            sender_account_id="ACC_DISPERSE_001",
            start_timestamp="2025-02-02 09:00:00",
            count=4,
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_in_only_transactions_fixture() -> pd.DataFrame:
    """Return a receiving-account concentration pattern only."""

    return pd.DataFrame(
        _fan_in_rows(
            prefix="TXN_FLOW_IN_ONLY",
            receiver_account_id="ACC_COLLECT_001",
            start_timestamp="2025-02-03 09:00:00",
            count=4,
        ),
        columns=TRANSACTION_COLUMNS,
    )


def build_fan_out_only_transactions_fixture() -> pd.DataFrame:
    """Return a sending-account dispersion pattern only."""

    return pd.DataFrame(
        _fan_out_rows(
            prefix="TXN_FLOW_OUT_ONLY",
            sender_account_id="ACC_DISPERSE_001",
            start_timestamp="2025-02-04 09:00:00",
            count=4,
        ),
        columns=TRANSACTION_COLUMNS,
    )


def build_cross_rule_non_trigger_transactions_fixture() -> pd.DataFrame:
    """Return benign fan-flow activity below both fan-in and fan-out thresholds."""

    rows = _fan_in_rows(
        prefix="TXN_FLOW_NON_TRIGGER_IN",
        receiver_account_id="ACC_COLLECT_001",
        start_timestamp="2025-02-05 09:00:00",
        count=3,
        suspicious=False,
        typology_label=None,
    )
    rows.extend(
        _fan_out_rows(
            prefix="TXN_FLOW_NON_TRIGGER_OUT",
            sender_account_id="ACC_DISPERSE_001",
            start_timestamp="2025-02-06 09:00:00",
            count=3,
            suspicious=False,
            typology_label=None,
        )
    )
    rows.append(
        _transaction_row(
            transaction_id="TXN_FLOW_NON_TRIGGER_SELF",
            sender_account_id="ACC_BENIGN_001",
            receiver_account_id="ACC_BENIGN_001",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-02-07 09:00:00", tz="UTC"),
            amount=250.0,
            transaction_type="transfer",
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_flow_boundary_transactions_fixture() -> pd.DataFrame:
    """Return exact-threshold and one-below-threshold fan-flow examples."""

    rows = _fan_in_rows(
        prefix="TXN_FLOW_BOUNDARY_IN_EXACT",
        receiver_account_id="ACC_COLLECT_001",
        start_timestamp="2025-02-08 09:00:00",
        count=4,
    )
    rows.extend(
        _fan_in_rows(
            prefix="TXN_FLOW_BOUNDARY_IN_BELOW",
            receiver_account_id="ACC_COLLECT_002",
            start_timestamp="2025-02-09 09:00:00",
            count=3,
            sender_offset=4,
            suspicious=False,
            typology_label=None,
        )
    )
    rows.extend(
        _fan_out_rows(
            prefix="TXN_FLOW_BOUNDARY_OUT_EXACT",
            sender_account_id="ACC_DISPERSE_001",
            start_timestamp="2025-02-10 09:00:00",
            count=4,
        )
    )
    rows.extend(
        _fan_out_rows(
            prefix="TXN_FLOW_BOUNDARY_OUT_BELOW",
            sender_account_id="ACC_DISPERSE_002",
            start_timestamp="2025-02-11 09:00:00",
            count=3,
            receiver_offset=4,
            suspicious=False,
            typology_label=None,
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_flow_overlapping_window_transactions_fixture() -> pd.DataFrame:
    """Return overlapping candidate windows for both rules."""

    start = pd.Timestamp("2025-02-12 09:00:00", tz="UTC")
    rows: list[dict[str, object]] = []
    for index in range(1, 6):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_FLOW_OVERLAP_IN_{index:03d}",
                sender_account_id=f"ACC_FLOW_SENDER_{index:03d}",
                receiver_account_id="ACC_COLLECT_001",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(hours=index - 1),
                amount=500.0 if index < 5 else 750.0,
                transaction_type="wire",
                suspicious=True,
                typology_label="fan_in",
            )
        )
    out_start = pd.Timestamp("2025-02-13 09:00:00", tz="UTC")
    for index in range(1, 6):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_FLOW_OVERLAP_OUT_{index:03d}",
                sender_account_id="ACC_DISPERSE_001",
                receiver_account_id=f"ACC_FLOW_RECEIVER_{index:03d}",
                counterparty_id=None,
                timestamp=out_start + pd.Timedelta(hours=index - 1),
                amount=500.0 if index < 5 else 750.0,
                transaction_type="wire",
                suspicious=True,
                typology_label="fan_out",
            )
        )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_flow_counterparty_mixed_transactions_fixture() -> pd.DataFrame:
    """Return mixed internal and external recipients for fan-out tests."""

    start = pd.Timestamp("2025-02-14 09:00:00", tz="UTC")
    rows: list[dict[str, object]] = []
    for index in range(1, 3):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_FLOW_MIXED_INTERNAL_{index:03d}",
                sender_account_id="ACC_DISPERSE_001",
                receiver_account_id=f"ACC_FLOW_RECEIVER_{index:03d}",
                counterparty_id=None,
                timestamp=start + pd.Timedelta(hours=index - 1),
                amount=500.0,
                transaction_type="transfer",
                suspicious=True,
                typology_label="fan_out",
            )
        )
    for index in range(1, 3):
        rows.append(
            _transaction_row(
                transaction_id=f"TXN_FLOW_MIXED_COUNTERPARTY_{index:03d}",
                sender_account_id="ACC_DISPERSE_001",
                receiver_account_id=None,
                counterparty_id=f"CP_FLOW_RECIPIENT_{index:03d}",
                timestamp=start + pd.Timedelta(hours=index + 1),
                amount=500.0,
                transaction_type="transfer",
                suspicious=True,
                typology_label="fan_out",
            )
        )
    rows.append(
        _transaction_row(
            transaction_id="TXN_FLOW_MIXED_NO_RECEIVER",
            sender_account_id="ACC_FLOW_SENDER_001",
            receiver_account_id=None,
            counterparty_id="CP_FLOW_ONLY",
            timestamp=start + pd.Timedelta(days=1),
            amount=500.0,
            transaction_type="transfer",
        )
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_flow_duplicate_sender_recipient_fixture() -> pd.DataFrame:
    """Return duplicate sender and recipient rows that should not inflate unique counts."""

    start = pd.Timestamp("2025-02-15 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=f"TXN_FLOW_DUP_IN_{index:03d}",
            sender_account_id="ACC_FLOW_SENDER_001",
            receiver_account_id="ACC_COLLECT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=500.0,
            transaction_type="transfer",
        )
        for index in range(1, 5)
    ]
    rows.extend(
        _transaction_row(
            transaction_id=f"TXN_FLOW_DUP_OUT_{index:03d}",
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id="ACC_FLOW_RECEIVER_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index + 4),
            amount=500.0,
            transaction_type="transfer",
        )
        for index in range(1, 5)
    )
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_fan_flow_invalid_transactions_fixture() -> pd.DataFrame:
    """Return malformed fan-flow rows for controlled invalid-input tests."""

    start = pd.Timestamp("2025-02-16 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id=None,
            sender_account_id="ACC_FLOW_SENDER_001",
            receiver_account_id="ACC_COLLECT_001",
            counterparty_id=None,
            timestamp=start,
            amount=500.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_FLOW_INVALID_SENDER",
            sender_account_id=None,
            receiver_account_id="ACC_COLLECT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=1),
            amount=500.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_FLOW_INVALID_TIMESTAMP",
            sender_account_id="ACC_FLOW_SENDER_002",
            receiver_account_id="ACC_COLLECT_001",
            counterparty_id=None,
            timestamp="not-a-timestamp",
            amount=500.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_FLOW_INVALID_AMOUNT",
            sender_account_id="ACC_FLOW_SENDER_003",
            receiver_account_id="ACC_COLLECT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=3),
            amount="not-a-number",
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_FLOW_INVALID_RECIPIENT",
            sender_account_id="ACC_DISPERSE_001",
            receiver_account_id=None,
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=4),
            amount=500.0,
            transaction_type="transfer",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def _fan_in_rows(
    *,
    prefix: str,
    receiver_account_id: str,
    start_timestamp: str,
    count: int,
    sender_offset: int = 0,
    amount: float = 500.0,
    suspicious: bool = True,
    typology_label: str | None = "fan_in",
) -> list[dict[str, object]]:
    start = pd.Timestamp(start_timestamp, tz="UTC")
    return [
        _transaction_row(
            transaction_id=f"{prefix}_{index:03d}",
            sender_account_id=f"ACC_FLOW_SENDER_{sender_offset + index:03d}",
            receiver_account_id=receiver_account_id,
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=amount,
            transaction_type="transfer",
            suspicious=suspicious,
            typology_label=typology_label,
        )
        for index in range(1, count + 1)
    ]


def _fan_out_rows(
    *,
    prefix: str,
    sender_account_id: str,
    start_timestamp: str,
    count: int,
    receiver_offset: int = 0,
    amount: float = 500.0,
    suspicious: bool = True,
    typology_label: str | None = "fan_out",
) -> list[dict[str, object]]:
    start = pd.Timestamp(start_timestamp, tz="UTC")
    return [
        _transaction_row(
            transaction_id=f"{prefix}_{index:03d}",
            sender_account_id=sender_account_id,
            receiver_account_id=f"ACC_FLOW_RECEIVER_{receiver_offset + index:03d}",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=index - 1),
            amount=amount,
            transaction_type="transfer",
            suspicious=suspicious,
            typology_label=typology_label,
        )
        for index in range(1, count + 1)
    ]


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
        "device_id": "DEV_FAN_FLOW_001",
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
        "source_file": "fan_flow_fixture",
    }
