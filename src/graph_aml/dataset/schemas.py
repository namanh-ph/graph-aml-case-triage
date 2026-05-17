"""Typed reference dataset container and lightweight integrity checks."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class AmlDataset:
    """Container for generated reference AML-style tables."""

    countries: pd.DataFrame
    customers: pd.DataFrame
    accounts: pd.DataFrame
    counterparties: pd.DataFrame
    devices: pd.DataFrame
    transactions: pd.DataFrame
    scenario_manifest: pd.DataFrame | None = None


REQUIRED_COLUMNS = {
    "countries": {
        "country_code",
        "country_name",
        "region",
        "is_high_risk",
        "risk_score",
    },
    "customers": {
        "customer_id",
        "customer_type",
        "customer_segment",
        "jurisdiction",
        "occupation",
        "industry_code",
        "customer_risk_rating",
        "customer_risk_score",
        "onboarded_at",
    },
    "accounts": {
        "account_id",
        "customer_id",
        "account_type",
        "account_status",
        "currency",
        "opened_at",
        "closed_at",
        "home_country",
    },
    "counterparties": {
        "counterparty_id",
        "counterparty_type",
        "counterparty_name",
        "country_code",
        "institution_name",
        "external_account_ref",
        "risk_score",
    },
    "devices": {
        "device_id",
        "device_type",
        "ip_address",
        "ip_cluster",
        "phone_hash",
        "browser_fingerprint",
    },
    "transactions": {
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
        "scenario_id",
        "scenario_role",
        "scenario_sequence",
        "scenario_injected",
    },
}


def dataset_table_names() -> tuple[str, ...]:
    """Return generated reference dataset table names in canonical order."""

    return (
        "countries",
        "customers",
        "accounts",
        "counterparties",
        "devices",
        "transactions",
    )


def _dataset_frames(dataset: AmlDataset) -> dict[str, pd.DataFrame]:
    return {
        "countries": dataset.countries,
        "customers": dataset.customers,
        "accounts": dataset.accounts,
        "counterparties": dataset.counterparties,
        "devices": dataset.devices,
        "transactions": dataset.transactions,
    }


def _require_columns(table_name: str, frame: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS[table_name].difference(frame.columns)
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {sorted(missing)}")


def _non_null_values(series: pd.Series) -> set[str]:
    return set(series.dropna().astype(str))


def _assert_subset(values: set[str], allowed_values: set[str], label: str) -> None:
    invalid = values.difference(allowed_values)
    if invalid:
        raise ValueError(f"{label} contains unknown IDs: {sorted(invalid)[:5]}")


def _manifest_values(manifest: pd.DataFrame, column: str) -> set[str]:
    from graph_aml.dataset.scenario_manifest import as_tuple

    values: set[str] = set()
    for item in manifest[column]:
        values.update(as_tuple(item))
    return values


def validate_synthetic_dataset(dataset: AmlDataset) -> None:
    """Validate core integrity of generated reference data without Pandera."""

    frames = _dataset_frames(dataset)
    for table_name in dataset_table_names():
        frame = frames[table_name]
        if frame.empty:
            raise ValueError(f"{table_name} must not be empty")
        _require_columns(table_name, frame)

    countries = set(dataset.countries["country_code"].astype(str))
    customers = set(dataset.customers["customer_id"].astype(str))
    accounts = set(dataset.accounts["account_id"].astype(str))
    counterparties = set(dataset.counterparties["counterparty_id"].astype(str))
    devices = set(dataset.devices["device_id"].astype(str))

    if not dataset.customers["customer_id"].is_unique:
        raise ValueError("customer_id values must be unique")
    if not dataset.accounts["account_id"].is_unique:
        raise ValueError("account_id values must be unique")
    if not dataset.transactions["transaction_id"].is_unique:
        raise ValueError("transaction_id values must be unique")

    if (pd.to_numeric(dataset.transactions["amount"]) <= 0).any():
        raise ValueError("transaction amounts must be positive")
    if dataset.transactions["transaction_timestamp"].isna().any():
        raise ValueError("transaction timestamps must be populated")

    _assert_subset(_non_null_values(dataset.customers["jurisdiction"]), countries, "customers")
    _assert_subset(_non_null_values(dataset.accounts["customer_id"]), customers, "accounts")
    _assert_subset(_non_null_values(dataset.accounts["home_country"]), countries, "accounts")
    _assert_subset(
        _non_null_values(dataset.counterparties["country_code"]),
        countries,
        "counterparties",
    )
    _assert_subset(
        _non_null_values(dataset.transactions["sender_account_id"]),
        accounts,
        "transaction senders",
    )
    _assert_subset(
        _non_null_values(dataset.transactions["receiver_account_id"]),
        accounts,
        "transaction receivers",
    )
    _assert_subset(
        _non_null_values(dataset.transactions["counterparty_id"]),
        counterparties,
        "transaction counterparties",
    )
    _assert_subset(
        _non_null_values(dataset.transactions["device_id"]),
        devices,
        "transaction devices",
    )
    _assert_subset(
        _non_null_values(dataset.transactions["origin_country"]),
        countries,
        "transaction origin countries",
    )
    _assert_subset(
        _non_null_values(dataset.transactions["destination_country"]),
        countries,
        "transaction destination countries",
    )

    expected_cross_border = dataset.transactions["origin_country"].astype(
        str
    ) != dataset.transactions["destination_country"].astype(str)
    actual_cross_border = dataset.transactions["is_cross_border"].astype(bool)
    if not expected_cross_border.equals(actual_cross_border):
        raise ValueError("is_cross_border values must match origin and destination countries")

    suspicious = dataset.transactions["is_labelled_suspicious"].astype(bool)
    if suspicious.any() and dataset.transactions.loc[suspicious, "typology_label"].isna().any():
        raise ValueError("suspicious transactions must have typology labels")

    if dataset.scenario_manifest is not None:
        from graph_aml.dataset.scenario_manifest import validate_scenario_manifest

        validate_scenario_manifest(dataset.scenario_manifest)
        scenario_ids = set(dataset.scenario_manifest["scenario_id"].astype(str))
        scenario_transaction_ids = _non_null_values(dataset.transactions["scenario_id"])
        _assert_subset(scenario_transaction_ids, scenario_ids, "transaction scenario IDs")

        evidence_ids = _manifest_values(dataset.scenario_manifest, "evidence_transaction_ids")
        _assert_subset(
            evidence_ids,
            set(dataset.transactions["transaction_id"].astype(str)),
            "manifest evidence",
        )

        manifest_accounts = _manifest_values(dataset.scenario_manifest, "involved_account_ids")
        manifest_accounts.update(_non_null_values(dataset.scenario_manifest["primary_account_id"]))
        _assert_subset(manifest_accounts, accounts, "manifest accounts")

        manifest_counterparties = _manifest_values(
            dataset.scenario_manifest,
            "involved_counterparty_ids",
        )
        _assert_subset(manifest_counterparties, counterparties, "manifest counterparties")
