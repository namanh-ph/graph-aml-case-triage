"""Deterministic fixtures for dormant reactivation rule tests."""

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


def build_dormant_reactivation_accounts_fixture() -> pd.DataFrame:
    """Return dormant, source, recipient, and benign account context."""

    rows = [
        _account_row("ACC_DORMANT_001", "CUST_DORMANT_001", "dormant"),
        _account_row("ACC_DORMANT_002", "CUST_DORMANT_002", "dormant"),
        _account_row("ACC_DORMANT_003", "CUST_DORMANT_003", "dormant"),
        _account_row("ACC_SOURCE_001", "CUST_SOURCE_001", "active"),
        _account_row("ACC_RECIPIENT_001", "CUST_RECIPIENT_001", "active"),
        _account_row("ACC_RECIPIENT_002", "CUST_RECIPIENT_002", "active"),
        _account_row("ACC_RECIPIENT_003", "CUST_RECIPIENT_003", "active"),
        _account_row("ACC_BENIGN_001", "CUST_BENIGN_001", "active"),
    ]
    return pd.DataFrame(rows)


def build_dormant_reactivation_trigger_transactions_fixture(
    account_id: str = "ACC_DORMANT_001",
    prior_timestamp: str = "2024-09-01 09:00:00",
    reactivation_timestamp: str = "2025-01-10 09:00:00",
    outbound_amount: float = 10000.0,
) -> pd.DataFrame:
    """Return one prior activity row followed by qualifying outbound reactivation."""

    prior = pd.Timestamp(prior_timestamp, tz="UTC")
    reactivation = pd.Timestamp(reactivation_timestamp, tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_DR_PRIOR_001",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id=account_id,
            counterparty_id=None,
            timestamp=prior,
            amount=250.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id="TXN_DR_REACT_001",
            sender_account_id=account_id,
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=reactivation,
            amount=outbound_amount,
            transaction_type="wire",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_dormant_reactivation_non_trigger_transactions_fixture() -> pd.DataFrame:
    """Return benign dormant-like rows that should not trigger."""

    rows = [
        _transaction_row(
            transaction_id="TXN_DR_NON_PRIOR_RECENT",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_BENIGN_001",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-01 09:00:00", tz="UTC"),
            amount=250.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_DR_NON_REACT_RECENT",
            sender_account_id="ACC_BENIGN_001",
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-10 09:00:00", tz="UTC"),
            amount=10000.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_DR_NON_REACT_LOW",
            sender_account_id="ACC_DORMANT_002",
            receiver_account_id="ACC_RECIPIENT_002",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-10 10:00:00", tz="UTC"),
            amount=5000.0,
            transaction_type="wire",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_dormant_reactivation_multi_account_transactions_fixture() -> pd.DataFrame:
    """Return two dormant accounts that reactivate independently."""

    rows = [
        *build_dormant_reactivation_trigger_transactions_fixture().to_dict(orient="records"),
        _transaction_row(
            transaction_id="TXN_DR_MULTI_B_PRIOR",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_DORMANT_002",
            counterparty_id=None,
            timestamp=pd.Timestamp("2024-08-25 09:00:00", tz="UTC"),
            amount=200.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id="TXN_DR_MULTI_B_REACT",
            sender_account_id="ACC_DORMANT_002",
            receiver_account_id="ACC_RECIPIENT_002",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-12 09:00:00", tz="UTC"),
            amount=15000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_dormant_reactivation_overlapping_window_transactions_fixture() -> pd.DataFrame:
    """Return same-timestamp reactivation candidates with deterministic deduplication."""

    prior = pd.Timestamp("2024-08-01 09:00:00", tz="UTC")
    react = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_DR_OVERLAP_PRIOR",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_DORMANT_001",
            counterparty_id=None,
            timestamp=prior,
            amount=150.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id="TXN_DR_OVERLAP_REACT_001",
            sender_account_id="ACC_DORMANT_001",
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=react,
            amount=10000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id="TXN_DR_OVERLAP_REACT_002",
            sender_account_id="ACC_DORMANT_001",
            receiver_account_id="ACC_RECIPIENT_002",
            counterparty_id=None,
            timestamp=react,
            amount=12000.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_dormant_reactivation_counterparty_transactions_fixture() -> pd.DataFrame:
    """Return dormant reactivation where the outflow recipient is a counterparty."""

    prior = pd.Timestamp("2024-09-01 09:00:00", tz="UTC")
    react = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    rows = [
        _transaction_row(
            transaction_id="TXN_DR_COUNTERPARTY_PRIOR",
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_DORMANT_001",
            counterparty_id=None,
            timestamp=prior,
            amount=250.0,
            transaction_type="transfer",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
        _transaction_row(
            transaction_id="TXN_DR_COUNTERPARTY_REACT",
            sender_account_id="ACC_DORMANT_001",
            receiver_account_id=None,
            counterparty_id="CP_DR_001",
            timestamp=react,
            amount=12000.0,
            transaction_type="wire",
            suspicious=True,
            typology_label="dormant_reactivation",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def build_dormant_reactivation_invalid_transactions_fixture() -> pd.DataFrame:
    """Return malformed rows that normalisation should drop or filters should exclude."""

    rows = [
        _transaction_row(
            transaction_id=None,
            sender_account_id="ACC_SOURCE_001",
            receiver_account_id="ACC_DORMANT_001",
            counterparty_id=None,
            timestamp=pd.Timestamp("2024-09-01 09:00:00", tz="UTC"),
            amount=250.0,
            transaction_type="transfer",
        ),
        _transaction_row(
            transaction_id="TXN_DR_INVALID_TIMESTAMP",
            sender_account_id="ACC_DORMANT_001",
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp="not-a-timestamp",
            amount=10000.0,
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_DR_INVALID_AMOUNT",
            sender_account_id="ACC_DORMANT_001",
            receiver_account_id="ACC_RECIPIENT_001",
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-10 09:00:00", tz="UTC"),
            amount="not-a-number",
            transaction_type="wire",
        ),
        _transaction_row(
            transaction_id="TXN_DR_INVALID_RECIPIENT",
            sender_account_id="ACC_DORMANT_001",
            receiver_account_id=None,
            counterparty_id=None,
            timestamp=pd.Timestamp("2025-01-10 10:00:00", tz="UTC"),
            amount=10000.0,
            transaction_type="wire",
        ),
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


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
        "device_id": "DEV_DR_001",
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
        "source_file": "dormant_reactivation_fixture",
    }
