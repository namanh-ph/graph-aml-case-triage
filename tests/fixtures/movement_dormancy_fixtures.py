"""Joint deterministic fixtures for rapid movement and dormant reactivation tests."""

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


def build_movement_dormancy_accounts_fixture() -> pd.DataFrame:
    """Return account context for joint rapid movement and dormant reactivation tests."""

    rows = [
        _account_row("ACC_PASS_001", "CUST_PASS_001", "active"),
        _account_row("ACC_PASS_002", "CUST_PASS_002", "active"),
        _account_row("ACC_PASS_003", "CUST_PASS_003", "active"),
        _account_row("ACC_DORMANT_001", "CUST_DORMANT_001", "dormant"),
        _account_row("ACC_DORMANT_002", "CUST_DORMANT_002", "dormant"),
        _account_row("ACC_DORMANT_003", "CUST_DORMANT_003", "dormant"),
        _account_row("ACC_MD_HISTORY_001", "CUST_MD_HISTORY_001", "active"),
        _account_row("ACC_MD_SOURCE_001", "CUST_MD_SOURCE_001", "active"),
        _account_row("ACC_MD_SOURCE_002", "CUST_MD_SOURCE_002", "active"),
        _account_row("ACC_MD_RECIPIENT_001", "CUST_MD_RECIPIENT_001", "active"),
        _account_row("ACC_MD_RECIPIENT_002", "CUST_MD_RECIPIENT_002", "active"),
        _account_row("ACC_MD_RECIPIENT_003", "CUST_MD_RECIPIENT_003", "active"),
        _account_row("ACC_MD_COUNTERPARTY_ONLY", "CUST_MD_COUNTERPARTY_ONLY", "active"),
        _account_row("ACC_BENIGN_001", "CUST_BENIGN_001", "active"),
    ]
    return pd.DataFrame(rows)


def build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture() -> pd.DataFrame:
    """Return a joint rapid movement and dormant reactivation trigger fixture."""

    rows = [
        *_rapid_movement_rows(
            prefix="TXN_MD_RM",
            account_id="ACC_PASS_001",
            start=pd.Timestamp("2025-01-10 09:00:00", tz="UTC"),
        ),
        *_dormant_reactivation_rows(
            prefix="TXN_MD_DR",
            account_id="ACC_DORMANT_001",
            prior=pd.Timestamp("2024-09-01 09:00:00", tz="UTC"),
            react=pd.Timestamp("2025-01-10 09:00:00", tz="UTC"),
        ),
    ]
    return _frame(rows)


def build_rapid_movement_only_transactions_fixture() -> pd.DataFrame:
    """Return a rapid-movement-only fixture with pass-through activity."""

    return _frame(
        _rapid_movement_rows(
            prefix="TXN_MD_RM_ONLY",
            account_id="ACC_PASS_001",
            start=pd.Timestamp("2025-01-11 09:00:00", tz="UTC"),
        )
    )


def build_dormant_reactivation_only_transactions_fixture() -> pd.DataFrame:
    """Return a dormant-reactivation-only fixture with prior activity and reactivation."""

    return _frame(
        _dormant_reactivation_rows(
            prefix="TXN_MD_DR_ONLY",
            account_id="ACC_DORMANT_001",
            prior=pd.Timestamp("2024-09-01 09:00:00", tz="UTC"),
            react=pd.Timestamp("2025-01-10 09:00:00", tz="UTC"),
        )
    )


def build_cross_rule_benign_transactions_fixture() -> pd.DataFrame:
    """Return a cross-rule benign fixture that should trigger neither rule."""

    start = pd.Timestamp("2025-01-12 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_MD_BENIGN_IN_001",
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id="ACC_BENIGN_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_MD_BENIGN_OUT_001",
            sender_account_id="ACC_BENIGN_001",
            receiver_account_id="ACC_MD_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=4),
            amount=5000.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_MD_BENIGN_DR_PRIOR",
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id="ACC_DORMANT_002",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-01 09:00:00", tz="UTC"),
            amount=200.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_MD_BENIGN_DR_REACT",
            sender_account_id="ACC_DORMANT_002",
            receiver_account_id="ACC_MD_RECIPIENT_002",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-10 09:00:00", tz="UTC"),
            amount=5000.0,
            transaction_type="wire",
        ),
    ]
    return _frame(rows)


def build_movement_dormancy_window_boundary_transactions_fixture() -> pd.DataFrame:
    """Return a window boundary fixture for both rapid movement and dormant reactivation."""

    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_MD_BOUNDARY_RM_IN_START",
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_BOUNDARY_RM_OUT_START",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_MD_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start,
            amount=9000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_BOUNDARY_RM_IN_END",
            sender_account_id="ACC_MD_SOURCE_002",
            receiver_account_id="ACC_PASS_002",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(days=1),
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_BOUNDARY_RM_OUT_END",
            sender_account_id="ACC_PASS_002",
            receiver_account_id="ACC_MD_RECIPIENT_002",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(days=3),
            amount=9000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_BOUNDARY_RM_IN_LATE",
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id="ACC_PASS_003",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(days=2),
            amount=10000.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_MD_BOUNDARY_RM_OUT_LATE",
            sender_account_id="ACC_PASS_003",
            receiver_account_id="ACC_MD_RECIPIENT_003",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(days=4, seconds=1),
            amount=9000.0,
            transaction_type="wire",
        ),
        *_dormant_reactivation_rows(
            prefix="TXN_MD_BOUNDARY_DR",
            account_id="ACC_DORMANT_001",
            prior=pd.Timestamp("2024-09-01 09:00:00", tz="UTC"),
            react=start,
            second_react=start + pd.Timedelta(days=7),
        ),
        *_dormant_reactivation_rows(
            prefix="TXN_MD_BOUNDARY_DR_LATE",
            account_id="ACC_DORMANT_002",
            prior=pd.Timestamp("2024-09-01 09:00:00", tz="UTC"),
            react=start + pd.Timedelta(hours=1),
            second_react=start + pd.Timedelta(days=7, hours=1, seconds=1),
        ),
    ]
    return _frame(rows)


def build_movement_dormancy_overlapping_window_transactions_fixture() -> pd.DataFrame:
    """Return an overlapping-window fixture for both rules."""

    start = pd.Timestamp("2025-01-15 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_MD_OVERLAP_RM_IN_001",
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_OVERLAP_RM_OUT_001",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_MD_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=4),
            amount=9000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_OVERLAP_RM_IN_002",
            sender_account_id="ACC_MD_SOURCE_002",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=8),
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_OVERLAP_RM_OUT_002",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_MD_RECIPIENT_002",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=12),
            amount=19200.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        *_dormant_reactivation_rows(
            prefix="TXN_MD_OVERLAP_DR",
            account_id="ACC_DORMANT_001",
            prior=pd.Timestamp("2024-08-01 09:00:00", tz="UTC"),
            react=start,
            second_react=start,
            second_amount=12000.0,
        ),
    ]
    return _frame(rows)


def build_movement_dormancy_counterparty_mixed_transactions_fixture() -> pd.DataFrame:
    """Return a counterparty mixed fixture with internal and external outflows."""

    start = pd.Timestamp("2025-01-16 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_MD_COUNTER_RM_IN",
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_COUNTER_RM_OUT_INTERNAL",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_MD_RECIPIENT_001",
            counterparty_id=None,
            timestamp=start + pd.Timedelta(hours=2),
            amount=4500.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_COUNTER_RM_OUT_EXTERNAL",
            sender_account_id="ACC_PASS_001",
            receiver_account_id=None,
            counterparty_id="CP_MD_RM_001",
            timestamp=start + pd.Timedelta(hours=3),
            amount=5000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id="TXN_MD_COUNTER_DR_PRIOR",
            sender_account_id="ACC_MD_HISTORY_001",
            receiver_account_id="ACC_DORMANT_001",
            counterparty_id=None,
            timestamp=pd.Timestamp("2024-09-01 09:00:00", tz="UTC"),
            amount=200.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id="TXN_MD_COUNTER_DR_REACT_INTERNAL",
            sender_account_id="ACC_DORMANT_001",
            receiver_account_id="ACC_MD_RECIPIENT_002",
            counterparty_id=None,
            timestamp=start,
            amount=10000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id="TXN_MD_COUNTER_DR_REACT_EXTERNAL",
            sender_account_id="ACC_DORMANT_002",
            receiver_account_id=None,
            counterparty_id="CP_MD_DR_001",
            timestamp=start,
            amount=10000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id="TXN_MD_COUNTER_DR_PRIOR_EXTERNAL",
            sender_account_id="ACC_MD_HISTORY_001",
            receiver_account_id="ACC_DORMANT_002",
            counterparty_id=None,
            timestamp=pd.Timestamp("2024-09-01 09:00:00", tz="UTC"),
            amount=200.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
    ]
    return _frame(rows)


def build_movement_dormancy_high_value_transactions_fixture() -> pd.DataFrame:
    """Return a high-value fixture for high risk score paths."""

    rows = [
        *_rapid_movement_rows(
            prefix="TXN_MD_HIGH_RM",
            account_id="ACC_PASS_001",
            start=pd.Timestamp("2025-01-17 09:00:00", tz="UTC"),
            received_amount=10000.0,
            sent_amount=9900.0,
        ),
        *_dormant_reactivation_rows(
            prefix="TXN_MD_HIGH_DR",
            account_id="ACC_DORMANT_001",
            prior=pd.Timestamp("2024-09-01 09:00:00", tz="UTC"),
            react=pd.Timestamp("2025-01-17 09:00:00", tz="UTC"),
            amount=20000.0,
        ),
    ]
    return _frame(rows)


def build_movement_dormancy_invalid_transactions_fixture() -> pd.DataFrame:
    """Return an invalid-input fixture with malformed transaction values."""

    rows = [
        _transaction_row(
            transaction_id=None,
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-18 09:00:00", tz="UTC"),
            amount=10000.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_MD_INVALID_TIMESTAMP",
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id="ACC_PASS_001",
            counterparty_id=None,
            timestamp="not-a-timestamp",
            amount=10000.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_MD_INVALID_AMOUNT",
            sender_account_id="ACC_PASS_001",
            receiver_account_id="ACC_MD_RECIPIENT_001",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-18 10:00:00", tz="UTC"),
            amount="not-a-number",
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_MD_INVALID_RECIPIENT",
            sender_account_id="ACC_DORMANT_001",
            receiver_account_id=None,
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-18 11:00:00", tz="UTC"),
            amount=10000.0,
            transaction_type="wire",
        ),
    ]
    return _frame(rows)


def _rapid_movement_rows(
    *,
    prefix: str,
    account_id: str,
    start: pd.Timestamp,
    received_amount: float = 10000.0,
    sent_amount: float = 9000.0,
    counterparty: bool = False,
) -> list[dict[str, object]]:
    return [
        _transaction_row(
            transaction_id=f"{prefix}_IN_001",
            sender_account_id="ACC_MD_SOURCE_001",
            receiver_account_id=account_id,
            counterparty_id=None,
            timestamp=start,
            amount=received_amount,
            transaction_type="transfer",
            suspicious=True,
            typology_label="rapid_movement",
        ),
        _transaction_row(
            transaction_id=f"{prefix}_OUT_001",
            sender_account_id=account_id,
            receiver_account_id=None if counterparty else "ACC_MD_RECIPIENT_001",
            counterparty_id="CP_MD_RM_001" if counterparty else None,
            timestamp=start + pd.Timedelta(hours=4),
            amount=sent_amount,
            transaction_type="wire",
            suspicious=True,
            typology_label="rapid_movement",
        ),
    ]


def _dormant_reactivation_rows(
    *,
    prefix: str,
    account_id: str,
    prior: pd.Timestamp,
    react: pd.Timestamp,
    amount: float = 10000.0,
    second_react: pd.Timestamp | None = None,
    second_amount: float = 10000.0,
    counterparty: bool = False,
) -> list[dict[str, object]]:
    rows = [
        _transaction_row(
            transaction_id=f"{prefix}_PRIOR_001",
            sender_account_id="ACC_MD_HISTORY_001",
            receiver_account_id=account_id,
            counterparty_id=None,
            timestamp=prior,
            amount=200.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id=f"{prefix}_REACT_001",
            sender_account_id=account_id,
            receiver_account_id=None if counterparty else "ACC_MD_RECIPIENT_002",
            counterparty_id="CP_MD_DR_001" if counterparty else None,
            timestamp=react,
            amount=amount,
            transaction_type="wire",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
    ]
    if second_react is not None:
        rows.append(
            _transaction_row(
                transaction_id=f"{prefix}_REACT_002",
                sender_account_id=account_id,
                receiver_account_id="ACC_MD_RECIPIENT_003",
                counterparty_id=None,
                timestamp=second_react,
                amount=second_amount,
                transaction_type="wire",
                suspicious=True,
                typology_label="dormant_reactivation",
            )
        )
    return rows


def _account_row(account_id: str, customer_id: str, status: str) -> dict[str, object]:
    return {
        "account_id": account_id,
        "customer_id": customer_id,
        "account_type": "checking",
        "account_status": status,
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
        "device_id": "DEV_MD_001",
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
        "source_file": "movement_dormancy_fixture",
    }


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)
