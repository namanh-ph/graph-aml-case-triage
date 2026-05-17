"""Tests for raw-to-staging transformation functions."""

import pandas as pd

from graph_aml.staging.transform import (
    transform_accounts,
    transform_counterparties,
    transform_countries,
    transform_customers,
    transform_devices,
    transform_raw_dataset,
    transform_transactions,
)


def test_countries_transform_produces_required_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "country_code": "au",
                "country_name": "Australia",
                "region": "",
                "is_high_risk": "0",
                "risk_score": 120,
            }
        ]
    )

    output = transform_countries(frame)

    assert list(output.columns) == [
        "country_code",
        "country_name",
        "region",
        "is_high_risk",
        "risk_score",
    ]
    assert output.loc[0, "country_code"] == "AU"
    assert output.loc[0, "risk_score"] == 100.0


def test_customers_transform_standardises_customer_fields() -> None:
    frame = pd.DataFrame(
        [
            {
                "customer_id": " cust_001 ",
                "customer_type": "Individual",
                "customer_segment": "Retail",
                "jurisdiction": "au",
                "occupation": "Engineer",
                "industry_code": None,
                "customer_risk_rating": None,
                "customer_risk_score": "55",
                "onboarded_at": "2025-01-01T00:00:00Z",
            }
        ]
    )

    output = transform_customers(frame)

    assert output.loc[0, "customer_id"] == "CUST_001"
    assert output.loc[0, "customer_type"] == "individual"
    assert output.loc[0, "jurisdiction"] == "AU"
    assert output.loc[0, "customer_risk_rating"] == "low"


def test_accounts_transform_standardises_account_fields() -> None:
    frame = pd.DataFrame(
        [
            {
                "account_id": "acc_001",
                "customer_id": "cust_001",
                "account_type": "Current",
                "account_status": None,
                "currency": "aud",
                "opened_at": "2025-01-01T00:00:00Z",
                "closed_at": None,
                "home_country": "au",
            }
        ]
    )

    output = transform_accounts(frame)

    assert output.loc[0, "account_id"] == "ACC_001"
    assert output.loc[0, "account_status"] == "active"
    assert output.loc[0, "currency"] == "AUD"


def test_counterparties_transform_standardises_counterparty_fields() -> None:
    frame = pd.DataFrame(
        [
            {
                "counterparty_id": "cp_001",
                "counterparty_type": "Merchant",
                "counterparty_name": "Shop",
                "country_code": "nz",
                "institution_name": "Bank",
                "external_account_ref": "ref",
                "risk_score": "-5",
            }
        ]
    )

    output = transform_counterparties(frame)

    assert output.loc[0, "counterparty_id"] == "CP_001"
    assert output.loc[0, "counterparty_type"] == "merchant"
    assert output.loc[0, "country_code"] == "NZ"
    assert output.loc[0, "risk_score"] == 0.0


def test_devices_transform_standardises_device_fields() -> None:
    frame = pd.DataFrame(
        [
            {
                "device_id": " dev_001 ",
                "device_type": "Mobile",
                "ip_address": "",
                "ip_cluster": "cluster",
                "phone_hash": "phone",
                "browser_fingerprint": "browser",
            }
        ]
    )

    output = transform_devices(frame)

    assert output.loc[0, "device_id"] == "DEV_001"
    assert output.loc[0, "device_type"] == "mobile"
    assert output.loc[0, "ip_address"] is None


def test_transactions_transform_parses_timestamps_and_positive_amounts() -> None:
    frame = pd.DataFrame(
        [
            {
                "transaction_id": "txn_001",
                "sender_account_id": "acc_001",
                "receiver_account_id": "acc_002",
                "counterparty_id": None,
                "device_id": "dev_001",
                "transaction_timestamp": "2025-01-01T00:00:00Z",
                "amount": "10.50",
                "currency": "aud",
                "transaction_type": "Transfer",
                "channel": "Online",
                "origin_country": "au",
                "destination_country": "nz",
                "is_labelled_suspicious": "yes",
                "typology_label": "Structuring",
                "source_file": "reference",
            }
        ]
    )

    output = transform_transactions(frame)

    assert output.loc[0, "transaction_timestamp"].year == 2025
    assert output.loc[0, "amount"] == 10.5
    assert output.loc[0, "currency"] == "AUD"
    assert output.loc[0, "typology_label"] == "structuring"


def test_transactions_transform_recalculates_is_cross_border() -> None:
    frame = _transaction_frame(origin_country="au", destination_country="nz")

    output = transform_transactions(frame)

    assert bool(output.loc[0, "is_cross_border"]) is True


def test_transforms_drop_records_with_missing_primary_keys() -> None:
    assert transform_countries(pd.DataFrame([{"country_code": None}])).empty
    assert transform_customers(pd.DataFrame([{"customer_id": None}])).empty
    assert transform_accounts(pd.DataFrame([{"account_id": "A", "customer_id": None}])).empty
    assert transform_counterparties(pd.DataFrame([{"counterparty_id": None}])).empty
    assert transform_devices(pd.DataFrame([{"device_id": None}])).empty
    assert transform_transactions(pd.DataFrame([{"transaction_id": None}])).empty


def test_transforms_deduplicate_by_primary_key() -> None:
    frame = pd.DataFrame(
        [
            {"country_code": "au", "country_name": "Old", "risk_score": 1, "raw_record_id": 1},
            {"country_code": "AU", "country_name": "New", "risk_score": 2, "raw_record_id": 2},
        ]
    )

    output = transform_countries(frame)

    assert len(output) == 1
    assert output.loc[0, "country_name"] == "New"


def test_transform_raw_dataset_returns_all_expected_tables() -> None:
    raw_dataset = {
        "countries": pd.DataFrame(
            {"raw_payload": [{"country_code": "AU", "country_name": "Australia"}]}
        ),
        "customers": pd.DataFrame({"raw_payload": [{"customer_id": "CUST_001"}]}),
        "accounts": pd.DataFrame(
            {"raw_payload": [{"account_id": "ACC_001", "customer_id": "CUST_001"}]}
        ),
        "counterparties": pd.DataFrame({"raw_payload": [{"counterparty_id": "CP_001"}]}),
        "devices": pd.DataFrame({"raw_payload": [{"device_id": "DEV_001"}]}),
        "transactions": pd.DataFrame({"raw_payload": [_transaction_payload()]}),
    }

    output = transform_raw_dataset(raw_dataset)

    assert set(output) == {
        "countries",
        "customers",
        "accounts",
        "counterparties",
        "devices",
        "transactions",
    }


def test_input_dataframes_are_not_mutated() -> None:
    frame = pd.DataFrame([{"country_code": "au", "country_name": "Australia"}])
    before = frame.copy(deep=True)

    transform_countries(frame)

    pd.testing.assert_frame_equal(frame, before)


def _transaction_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "transaction_id": "TXN_001",
        "sender_account_id": "ACC_001",
        "receiver_account_id": "ACC_002",
        "counterparty_id": None,
        "device_id": "DEV_001",
        "transaction_timestamp": "2025-01-01T00:00:00Z",
        "amount": 10,
        "currency": "USD",
        "transaction_type": "transfer",
        "channel": "online",
        "origin_country": "AU",
        "destination_country": "NZ",
        "is_labelled_suspicious": False,
        "typology_label": None,
        "source_file": "reference",
    }
    payload.update(overrides)
    return payload


def _transaction_frame(**overrides: object) -> pd.DataFrame:
    return pd.DataFrame([_transaction_payload(**overrides)])
