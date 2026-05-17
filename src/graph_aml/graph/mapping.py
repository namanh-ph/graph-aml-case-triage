"""Map staged relational rows into Neo4j node and relationship rows."""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

import pandas as pd

from graph_aml.graph.exceptions import GraphMappingError

_NULL_STRINGS = {"", "nan", "nat", "none", "null", "<na>"}


def normalise_graph_scalar(value: object) -> object | None:
    """Normalise a scalar value for Neo4j parameter payloads."""

    if value is None:
        return None
    if isinstance(value, list):
        return [normalise_graph_scalar(item) for item in value]
    if isinstance(value, tuple | set):
        return [normalise_graph_scalar(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item") and not isinstance(value, str):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date | pd.Timestamp):
        return normalise_graph_timestamp(value)
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in _NULL_STRINGS:
            return None
        return stripped
    return value


def normalise_graph_timestamp(value: object) -> str | None:
    """Convert timestamp-like values to deterministic ISO strings."""

    scalar = normalise_graph_scalar(value) if not isinstance(value, datetime | date) else value
    if scalar is None:
        return None
    try:
        timestamp = pd.to_datetime(scalar, utc=True, errors="coerce")
    except Exception as exc:
        raise GraphMappingError(f"Invalid timestamp value: {value}") from exc
    if pd.isna(timestamp):
        return None
    return str(pd.Timestamp(timestamp).isoformat())


def normalise_graph_bool(value: object) -> bool | None:
    """Convert bool-like values to Python bools."""

    scalar = normalise_graph_scalar(value)
    if scalar is None:
        return None
    if isinstance(scalar, bool):
        return scalar
    if isinstance(scalar, int | float):
        return bool(scalar)
    if isinstance(scalar, str):
        lowered = scalar.strip().lower()
        if lowered in {"true", "t", "1", "yes", "y"}:
            return True
        if lowered in {"false", "f", "0", "no", "n"}:
            return False
    raise GraphMappingError(f"Invalid boolean value: {value}")


def normalise_graph_float(value: object) -> float | None:
    """Convert numeric values to Python floats."""

    scalar = normalise_graph_scalar(value)
    if scalar is None:
        return None
    try:
        result = float(cast(Any, scalar))
    except (TypeError, ValueError) as exc:
        raise GraphMappingError(f"Invalid float value: {value}") from exc
    if math.isnan(result):
        return None
    return result


def dataframe_to_graph_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Convert a DataFrame into normalised graph parameter rows."""

    if not isinstance(frame, pd.DataFrame):
        raise GraphMappingError("frame must be a pandas DataFrame")
    rows: list[dict[str, object]] = []
    for record in frame.copy(deep=True).to_dict(orient="records"):
        rows.append({key: normalise_graph_scalar(value) for key, value in record.items()})
    return rows


def _first_present(record: dict[str, object], names: Iterable[str]) -> object | None:
    for name in names:
        if name in record:
            value = normalise_graph_scalar(record[name])
            if value is not None:
                return value
    return None


def _row_from_record(
    record: dict[str, object],
    mapping: dict[str, tuple[str, ...]],
    *,
    timestamp_fields: tuple[str, ...] = (),
    float_fields: tuple[str, ...] = (),
    bool_fields: tuple[str, ...] = (),
) -> dict[str, object]:
    row: dict[str, object] = {}
    for output_key, aliases in mapping.items():
        value = _first_present(record, aliases)
        if output_key in timestamp_fields:
            value = normalise_graph_timestamp(value)
        elif output_key in float_fields:
            value = normalise_graph_float(value)
        elif output_key in bool_fields:
            value = normalise_graph_bool(value)
        row[output_key] = value
    return {key: value for key, value in row.items() if value is not None}


def _dedupe_rows(
    rows: list[dict[str, object]],
    key_fields: tuple[str, ...],
) -> list[dict[str, object]]:
    seen: dict[tuple[object, ...], dict[str, object]] = {}
    for row in rows:
        identity = tuple(row.get(field) for field in key_fields)
        if any(value is None for value in identity):
            continue
        seen.setdefault(identity, row)
    return [seen[key] for key in sorted(seen, key=lambda values: tuple(str(v) for v in values))]


def _build_nodes(
    frame: pd.DataFrame,
    mapping: dict[str, tuple[str, ...]],
    key_field: str,
    *,
    timestamp_fields: tuple[str, ...] = (),
    float_fields: tuple[str, ...] = (),
    bool_fields: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    if not isinstance(frame, pd.DataFrame):
        raise GraphMappingError("node input must be a pandas DataFrame")
    rows = [
        _row_from_record(
            record,
            mapping,
            timestamp_fields=timestamp_fields,
            float_fields=float_fields,
            bool_fields=bool_fields,
        )
        for record in frame.copy(deep=True).to_dict(orient="records")
    ]
    return _dedupe_rows(rows, (key_field,))


def build_customer_nodes(customers: pd.DataFrame) -> list[dict[str, object]]:
    """Build Customer node rows."""

    return _build_nodes(
        customers,
        {
            "customer_id": ("customer_id",),
            "customer_type": ("customer_type",),
            "segment": ("segment", "customer_segment"),
            "jurisdiction": ("jurisdiction",),
            "occupation": ("occupation",),
            "risk_rating": ("risk_rating", "customer_risk_rating"),
        },
        "customer_id",
    )


def build_account_nodes(accounts: pd.DataFrame) -> list[dict[str, object]]:
    """Build Account node rows."""

    return _build_nodes(
        accounts,
        {
            "account_id": ("account_id",),
            "customer_id": ("customer_id",),
            "account_type": ("account_type",),
            "opened_at": ("opened_at",),
            "status": ("status", "account_status"),
            "currency": ("currency",),
            "country_code": ("country_code", "home_country"),
        },
        "account_id",
        timestamp_fields=("opened_at",),
    )


def build_transaction_nodes(transactions: pd.DataFrame) -> list[dict[str, object]]:
    """Build Transaction node rows."""

    return _build_nodes(
        transactions,
        {
            "transaction_id": ("transaction_id",),
            "transaction_timestamp": ("transaction_timestamp",),
            "amount": ("amount",),
            "currency": ("currency",),
            "transaction_type": ("transaction_type",),
            "channel": ("channel",),
            "country_code": ("country_code", "destination_country", "origin_country"),
        },
        "transaction_id",
        timestamp_fields=("transaction_timestamp",),
        float_fields=("amount",),
    )


def build_counterparty_nodes(
    counterparties: pd.DataFrame,
    transactions: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    """Build Counterparty node rows, inferring missing nodes from transactions."""

    explicit = _build_nodes(
        counterparties,
        {
            "counterparty_id": ("counterparty_id",),
            "counterparty_type": ("counterparty_type",),
            "name": ("name", "counterparty_name"),
            "country_code": ("country_code",),
            "risk_rating": ("risk_rating", "risk_score"),
        },
        "counterparty_id",
    )
    inferred: list[dict[str, object]] = []
    if transactions is not None and isinstance(transactions, pd.DataFrame):
        for record in transactions.copy(deep=True).to_dict(orient="records"):
            counterparty_id = _first_present(record, ("counterparty_id",))
            if counterparty_id is not None:
                country_code = _first_present(record, ("destination_country", "country_code"))
                row = {"counterparty_id": counterparty_id}
                if country_code is not None:
                    row["country_code"] = country_code
                inferred.append(row)
    return _dedupe_rows([*explicit, *inferred], ("counterparty_id",))


def build_country_nodes(
    countries: pd.DataFrame,
    transactions: pd.DataFrame | None = None,
    counterparties: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    """Build Country node rows, inferring missing nodes from graph inputs."""

    explicit = _build_nodes(
        countries,
        {
            "country_code": ("country_code",),
            "country_name": ("country_name",),
            "high_risk_flag": ("high_risk_flag", "is_high_risk"),
            "region": ("region",),
        },
        "country_code",
        bool_fields=("high_risk_flag",),
    )
    inferred: list[dict[str, object]] = []
    for frame, columns in (
        (transactions, ("country_code", "origin_country", "destination_country")),
        (counterparties, ("country_code",)),
    ):
        if frame is None or not isinstance(frame, pd.DataFrame):
            continue
        for record in frame.copy(deep=True).to_dict(orient="records"):
            for column in columns:
                country_code = _first_present(record, (column,))
                if country_code is not None:
                    inferred.append({"country_code": country_code})
    return _dedupe_rows([*explicit, *inferred], ("country_code",))


def _normalise_evidence_ids(value: object) -> list[str]:
    scalar = normalise_graph_scalar(value)
    if scalar is None:
        return []
    if isinstance(scalar, str):
        stripped = scalar.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            parts = stripped[1:-1].split(",")
            return [part.strip().strip('"') for part in parts if part.strip()]
        if stripped.startswith("[") and stripped.endswith("]"):
            parts = stripped[1:-1].split(",")
            return [part.strip().strip("'\"") for part in parts if part.strip()]
        return [stripped]
    if isinstance(scalar, Iterable):
        return [str(item) for item in scalar if normalise_graph_scalar(item) is not None]
    return [str(scalar)]


def build_alert_nodes(alerts: pd.DataFrame) -> list[dict[str, object]]:
    """Build Alert node rows."""

    if not isinstance(alerts, pd.DataFrame):
        raise GraphMappingError("alerts must be a pandas DataFrame")
    rows: list[dict[str, object]] = []
    for record in alerts.copy(deep=True).to_dict(orient="records"):
        row = _row_from_record(
            record,
            {
                "alert_id": ("alert_id",),
                "account_id": ("account_id",),
                "customer_id": ("customer_id",),
                "rule_name": ("rule_name",),
                "typology": ("typology",),
                "severity": ("severity",),
                "risk_score_rule": ("risk_score_rule",),
                "reason_code": ("reason_code",),
                "created_at": ("created_at",),
            },
            timestamp_fields=("created_at",),
            float_fields=("risk_score_rule",),
        )
        evidence_ids = _normalise_evidence_ids(record.get("evidence_ids"))
        if evidence_ids:
            row["evidence_ids"] = evidence_ids
        rows.append(row)
    return _dedupe_rows(rows, ("alert_id",))


def build_all_graph_nodes(inputs: dict[str, pd.DataFrame]) -> dict[str, list[dict[str, object]]]:
    """Build all graph node groups from staged inputs."""

    try:
        return {
            "Customer": build_customer_nodes(inputs.get("customers", pd.DataFrame())),
            "Account": build_account_nodes(inputs.get("accounts", pd.DataFrame())),
            "Country": build_country_nodes(
                inputs.get("countries", pd.DataFrame()),
                inputs.get("transactions", pd.DataFrame()),
                inputs.get("counterparties", pd.DataFrame()),
            ),
            "Counterparty": build_counterparty_nodes(
                inputs.get("counterparties", pd.DataFrame()),
                inputs.get("transactions", pd.DataFrame()),
            ),
            "Transaction": build_transaction_nodes(inputs.get("transactions", pd.DataFrame())),
            "Alert": build_alert_nodes(inputs.get("alerts", pd.DataFrame())),
        }
    except GraphMappingError:
        raise
    except Exception as exc:
        raise GraphMappingError(f"Failed to build graph nodes: {exc}") from exc


def _build_relationships(
    frame: pd.DataFrame,
    mapping: dict[str, tuple[str, ...]],
    key_fields: tuple[str, ...],
    *,
    timestamp_fields: tuple[str, ...] = (),
    float_fields: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    if not isinstance(frame, pd.DataFrame):
        raise GraphMappingError("relationship input must be a pandas DataFrame")
    rows = [
        _row_from_record(
            record,
            mapping,
            timestamp_fields=timestamp_fields,
            float_fields=float_fields,
        )
        for record in frame.copy(deep=True).to_dict(orient="records")
    ]
    return _dedupe_rows(rows, key_fields)


def build_owns_relationships(accounts: pd.DataFrame) -> list[dict[str, object]]:
    """Build Customer-[:OWNS]->Account rows."""

    return _build_relationships(
        accounts,
        {"customer_id": ("customer_id",), "account_id": ("account_id",)},
        ("customer_id", "account_id"),
    )


def build_sent_relationships(transactions: pd.DataFrame) -> list[dict[str, object]]:
    """Build Account-[:SENT]->Transaction rows."""

    return _build_relationships(
        transactions,
        {
            "account_id": ("sender_account_id",),
            "transaction_id": ("transaction_id",),
            "amount": ("amount",),
            "currency": ("currency",),
            "transaction_type": ("transaction_type",),
            "transaction_timestamp": ("transaction_timestamp",),
        },
        ("account_id", "transaction_id"),
        timestamp_fields=("transaction_timestamp",),
        float_fields=("amount",),
    )


def build_received_relationships(transactions: pd.DataFrame) -> list[dict[str, object]]:
    """Build Transaction-[:RECEIVED]->Account rows."""

    return _build_relationships(
        transactions,
        {
            "transaction_id": ("transaction_id",),
            "account_id": ("receiver_account_id",),
            "amount": ("amount",),
            "currency": ("currency",),
            "transaction_type": ("transaction_type",),
            "transaction_timestamp": ("transaction_timestamp",),
        },
        ("transaction_id", "account_id"),
        timestamp_fields=("transaction_timestamp",),
        float_fields=("amount",),
    )


def build_paid_to_relationships(transactions: pd.DataFrame) -> list[dict[str, object]]:
    """Build Transaction-[:PAID_TO]->Counterparty rows."""

    return _build_relationships(
        transactions,
        {
            "transaction_id": ("transaction_id",),
            "counterparty_id": ("counterparty_id",),
            "amount": ("amount",),
            "currency": ("currency",),
            "transaction_type": ("transaction_type",),
            "transaction_timestamp": ("transaction_timestamp",),
        },
        ("transaction_id", "counterparty_id"),
        timestamp_fields=("transaction_timestamp",),
        float_fields=("amount",),
    )


def build_country_relationships(
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    counterparties: pd.DataFrame,
) -> list[dict[str, object]]:
    """Build entity-[:LOCATED_IN]->Country rows."""

    rows: list[dict[str, object]] = []
    sources: tuple[tuple[pd.DataFrame, str, str, tuple[str, ...]], ...] = (
        (customers, "Customer", "customer_id", ("jurisdiction",)),
        (accounts, "Account", "account_id", ("country_code", "home_country")),
        (
            transactions,
            "Transaction",
            "transaction_id",
            ("country_code", "destination_country", "origin_country"),
        ),
        (counterparties, "Counterparty", "counterparty_id", ("country_code",)),
    )
    for frame, label, id_column, country_columns in sources:
        if not isinstance(frame, pd.DataFrame):
            raise GraphMappingError("country relationship inputs must be DataFrames")
        for record in frame.copy(deep=True).to_dict(orient="records"):
            source_id = _first_present(record, (id_column,))
            country_code = _first_present(record, country_columns)
            if source_id is not None and country_code is not None:
                rows.append(
                    {
                        "source_label": label,
                        "source_id": source_id,
                        "country_code": country_code,
                    }
                )
    return _dedupe_rows(rows, ("source_label", "source_id", "country_code"))


def build_alert_relationships(alerts: pd.DataFrame) -> dict[str, list[dict[str, object]]]:
    """Build alert-to-account and alert-to-transaction relationship rows."""

    if not isinstance(alerts, pd.DataFrame):
        raise GraphMappingError("alerts must be a pandas DataFrame")
    flags: list[dict[str, object]] = []
    involves: list[dict[str, object]] = []
    triggers: list[dict[str, object]] = []
    for record in alerts.copy(deep=True).to_dict(orient="records"):
        alert_id = _first_present(record, ("alert_id",))
        account_id = _first_present(record, ("account_id",))
        rule_name = _first_present(record, ("rule_name",))
        typology = _first_present(record, ("typology",))
        if alert_id is None:
            continue
        base_props = {"alert_id": alert_id}
        if rule_name is not None:
            base_props["rule_name"] = rule_name
        if typology is not None:
            base_props["typology"] = typology
        if account_id is not None:
            flags.append({**base_props, "account_id": account_id})
        for transaction_id in _normalise_evidence_ids(record.get("evidence_ids")):
            involves.append({**base_props, "transaction_id": transaction_id})
            triggers.append({"transaction_id": transaction_id, **base_props})
    return {
        "FLAGS_ACCOUNT": _dedupe_rows(flags, ("alert_id", "account_id")),
        "INVOLVES_TRANSACTION": _dedupe_rows(involves, ("alert_id", "transaction_id")),
        "TRIGGERS": _dedupe_rows(triggers, ("transaction_id", "alert_id")),
    }


def build_all_graph_relationships(
    inputs: dict[str, pd.DataFrame],
) -> dict[str, list[dict[str, object]]]:
    """Build all graph relationship groups from staged inputs."""

    try:
        accounts = inputs.get("accounts", pd.DataFrame())
        transactions = inputs.get("transactions", pd.DataFrame())
        alerts = inputs.get("alerts", pd.DataFrame())
        alert_relationships = build_alert_relationships(alerts)
        return {
            "OWNS": build_owns_relationships(accounts),
            "SENT": build_sent_relationships(transactions),
            "RECEIVED": build_received_relationships(transactions),
            "PAID_TO": build_paid_to_relationships(transactions),
            "LOCATED_IN": build_country_relationships(
                inputs.get("customers", pd.DataFrame()),
                accounts,
                transactions,
                inputs.get("counterparties", pd.DataFrame()),
            ),
            **alert_relationships,
        }
    except GraphMappingError:
        raise
    except Exception as exc:
        raise GraphMappingError(f"Failed to build graph relationships: {exc}") from exc
