"""Raw payload to staging DataFrame transformations."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from graph_aml.staging.exceptions import StagingTransformationError
from graph_aml.staging.extract import extract_payload_frame
from graph_aml.staging.normalise import (
    ensure_columns,
    normalise_boolean,
    normalise_country_code,
    normalise_currency,
    normalise_identifier,
    normalise_numeric,
    normalise_string,
    parse_timestamp,
)

COUNTRY_COLUMNS = ("country_code", "country_name", "region", "is_high_risk", "risk_score")
CUSTOMER_COLUMNS = (
    "customer_id",
    "customer_type",
    "customer_segment",
    "jurisdiction",
    "occupation",
    "industry_code",
    "customer_risk_rating",
    "customer_risk_score",
    "onboarded_at",
)
ACCOUNT_COLUMNS = (
    "account_id",
    "customer_id",
    "account_type",
    "account_status",
    "currency",
    "opened_at",
    "closed_at",
    "home_country",
)
COUNTERPARTY_COLUMNS = (
    "counterparty_id",
    "counterparty_type",
    "counterparty_name",
    "country_code",
    "institution_name",
    "external_account_ref",
    "risk_score",
)
DEVICE_COLUMNS = (
    "device_id",
    "device_type",
    "ip_address",
    "ip_cluster",
    "phone_hash",
    "browser_fingerprint",
)
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
LOGICAL_TABLES = (
    "countries",
    "customers",
    "accounts",
    "counterparties",
    "devices",
    "transactions",
)


def _lower(value: object, default: str | None = None) -> str | None:
    text = normalise_string(value)
    if text is None:
        return default
    return text.lower()


def _clip_score(value: object, default: float = 0.0) -> float:
    parsed = normalise_numeric(value, default=default)
    if parsed is None:
        parsed = default
    return max(0.0, min(100.0, parsed))


def _deduplicate(frame: pd.DataFrame, primary_key: str) -> pd.DataFrame:
    if frame.empty:
        return frame.reset_index(drop=True)
    output = frame.copy()
    sort_columns: list[str] = []
    if "ingested_at" in output.columns:
        sort_columns.append("ingested_at")
    if "raw_record_id" in output.columns:
        sort_columns.append("raw_record_id")
    if sort_columns:
        output = output.sort_values(sort_columns, kind="mergesort")
    return output.drop_duplicates(subset=[primary_key], keep="last").reset_index(drop=True)


def _attach_lineage(output: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    frame = output.copy()
    for column in ("ingested_at", "raw_record_id"):
        if column in source.columns:
            frame[column] = source[column].to_numpy()
    return frame


def _order_by(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    available = [column for column in columns if column in frame.columns]
    if not available or frame.empty:
        return frame.reset_index(drop=True)
    return frame.sort_values(available, kind="mergesort").reset_index(drop=True)


def transform_countries(raw_payloads: pd.DataFrame) -> pd.DataFrame:
    """Transform country payloads into staging.countries rows."""

    frame = ensure_columns(raw_payloads, COUNTRY_COLUMNS)
    output = pd.DataFrame(
        {
            "country_code": frame["country_code"].apply(normalise_country_code),
            "country_name": frame["country_name"].apply(normalise_string),
            "region": frame["region"].apply(normalise_string),
            "is_high_risk": frame["is_high_risk"].apply(normalise_boolean),
            "risk_score": frame["risk_score"].apply(_clip_score),
        }
    )
    output = _attach_lineage(output, frame)
    output = output[output["country_code"].notna()]
    output = _deduplicate(output, "country_code")
    return _order_by(output.loc[:, COUNTRY_COLUMNS], ("country_code",))


def transform_customers(raw_payloads: pd.DataFrame) -> pd.DataFrame:
    """Transform customer payloads into staging.customers rows."""

    frame = ensure_columns(raw_payloads, CUSTOMER_COLUMNS)
    output = pd.DataFrame(
        {
            "customer_id": frame["customer_id"].apply(normalise_identifier),
            "customer_type": frame["customer_type"].apply(_lower),
            "customer_segment": frame["customer_segment"].apply(_lower),
            "jurisdiction": frame["jurisdiction"].apply(normalise_country_code),
            "occupation": frame["occupation"].apply(normalise_string),
            "industry_code": frame["industry_code"].apply(normalise_string),
            "customer_risk_rating": frame["customer_risk_rating"].apply(
                lambda value: _lower(value, default="low")
            ),
            "customer_risk_score": frame["customer_risk_score"].apply(_clip_score),
            "onboarded_at": frame["onboarded_at"].apply(parse_timestamp),
        }
    )
    output = _attach_lineage(output, frame)
    output = output[output["customer_id"].notna()]
    output = _deduplicate(output, "customer_id")
    return _order_by(output.loc[:, CUSTOMER_COLUMNS], ("customer_id",))


def transform_accounts(raw_payloads: pd.DataFrame) -> pd.DataFrame:
    """Transform account payloads into staging.accounts rows."""

    frame = ensure_columns(raw_payloads, ACCOUNT_COLUMNS)
    output = pd.DataFrame(
        {
            "account_id": frame["account_id"].apply(normalise_identifier),
            "customer_id": frame["customer_id"].apply(normalise_identifier),
            "account_type": frame["account_type"].apply(_lower),
            "account_status": frame["account_status"].apply(lambda value: _lower(value, "active")),
            "currency": frame["currency"].apply(normalise_currency),
            "opened_at": frame["opened_at"].apply(parse_timestamp),
            "closed_at": frame["closed_at"].apply(parse_timestamp),
            "home_country": frame["home_country"].apply(normalise_country_code),
        }
    )
    output = _attach_lineage(output, frame)
    output = output[output["account_id"].notna() & output["customer_id"].notna()]
    output = _deduplicate(output, "account_id")
    return _order_by(output.loc[:, ACCOUNT_COLUMNS], ("account_id",))


def transform_counterparties(raw_payloads: pd.DataFrame) -> pd.DataFrame:
    """Transform counterparty payloads into staging.counterparties rows."""

    frame = ensure_columns(raw_payloads, COUNTERPARTY_COLUMNS)
    output = pd.DataFrame(
        {
            "counterparty_id": frame["counterparty_id"].apply(normalise_identifier),
            "counterparty_type": frame["counterparty_type"].apply(_lower),
            "counterparty_name": frame["counterparty_name"].apply(normalise_string),
            "country_code": frame["country_code"].apply(normalise_country_code),
            "institution_name": frame["institution_name"].apply(normalise_string),
            "external_account_ref": frame["external_account_ref"].apply(normalise_string),
            "risk_score": frame["risk_score"].apply(_clip_score),
        }
    )
    output = _attach_lineage(output, frame)
    output = output[output["counterparty_id"].notna()]
    output = _deduplicate(output, "counterparty_id")
    return _order_by(output.loc[:, COUNTERPARTY_COLUMNS], ("counterparty_id",))


def transform_devices(raw_payloads: pd.DataFrame) -> pd.DataFrame:
    """Transform device payloads into staging.devices rows."""

    frame = ensure_columns(raw_payloads, DEVICE_COLUMNS)
    output = pd.DataFrame(
        {
            "device_id": frame["device_id"].apply(normalise_identifier),
            "device_type": frame["device_type"].apply(_lower),
            "ip_address": frame["ip_address"].apply(normalise_string),
            "ip_cluster": frame["ip_cluster"].apply(normalise_string),
            "phone_hash": frame["phone_hash"].apply(normalise_string),
            "browser_fingerprint": frame["browser_fingerprint"].apply(normalise_string),
        }
    )
    output = _attach_lineage(output, frame)
    output = output[output["device_id"].notna()]
    output = _deduplicate(output, "device_id")
    return _order_by(output.loc[:, DEVICE_COLUMNS], ("device_id",))


def _recalculate_cross_border(row: pd.Series) -> bool:
    origin = normalise_country_code(row.get("origin_country"))
    destination = normalise_country_code(row.get("destination_country"))
    if origin is None or destination is None:
        return False
    return origin != destination


def _source_file(frame: pd.DataFrame) -> pd.Series:
    if "source_file" in frame.columns:
        return frame["source_file"]
    if "raw_source_file" in frame.columns:
        return frame["raw_source_file"]
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def transform_transactions(raw_payloads: pd.DataFrame) -> pd.DataFrame:
    """Transform transaction payloads into staging.transactions rows."""

    frame = ensure_columns(raw_payloads, TRANSACTION_COLUMNS)
    output = pd.DataFrame(
        {
            "transaction_id": frame["transaction_id"].apply(normalise_identifier),
            "sender_account_id": frame["sender_account_id"].apply(normalise_identifier),
            "receiver_account_id": frame["receiver_account_id"].apply(normalise_identifier),
            "counterparty_id": frame["counterparty_id"].apply(normalise_identifier),
            "device_id": frame["device_id"].apply(normalise_identifier),
            "transaction_timestamp": frame["transaction_timestamp"].apply(parse_timestamp),
            "amount": frame["amount"].apply(normalise_numeric),
            "currency": frame["currency"].apply(normalise_currency),
            "transaction_type": frame["transaction_type"].apply(_lower),
            "channel": frame["channel"].apply(_lower),
            "origin_country": frame["origin_country"].apply(normalise_country_code),
            "destination_country": frame["destination_country"].apply(normalise_country_code),
            "is_cross_border": frame.apply(_recalculate_cross_border, axis=1),
            "is_labelled_suspicious": frame["is_labelled_suspicious"].apply(normalise_boolean),
            "typology_label": frame["typology_label"].apply(lambda value: _lower(value)),
            "source_file": _source_file(frame).apply(normalise_string),
        }
    )
    output = _attach_lineage(output, frame)
    output = output[
        output["transaction_id"].notna()
        & output["sender_account_id"].notna()
        & output["transaction_timestamp"].notna()
        & output["amount"].notna()
        & (output["amount"] > 0)
    ]
    output = _deduplicate(output, "transaction_id")
    return _order_by(
        output.loc[:, TRANSACTION_COLUMNS],
        ("transaction_timestamp", "transaction_id"),
    )


TRANSFORMERS: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "countries": transform_countries,
    "customers": transform_customers,
    "accounts": transform_accounts,
    "counterparties": transform_counterparties,
    "devices": transform_devices,
    "transactions": transform_transactions,
}


def transform_raw_dataset(raw_dataset: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Expand raw payloads and transform all logical staging tables."""

    try:
        staging_dataset: dict[str, pd.DataFrame] = {}
        for table_name in LOGICAL_TABLES:
            raw_frame = raw_dataset.get(table_name, pd.DataFrame())
            payload_frame = (
                extract_payload_frame(raw_frame) if "raw_payload" in raw_frame else raw_frame
            )
            staging_dataset[table_name] = TRANSFORMERS[table_name](payload_frame)
        return staging_dataset
    except StagingTransformationError:
        raise
    except Exception as exc:
        raise StagingTransformationError(f"Failed to transform raw dataset: {exc}") from exc


def validate_staging_dataset(staging_dataset: dict[str, pd.DataFrame]) -> None:
    """No-op staging-dataset validation (Pandera-based check is performed at the silver layer)."""

    return None
