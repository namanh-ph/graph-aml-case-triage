"""Shared utilities for deterministic AML rules."""

from __future__ import annotations

import pandas as pd

from graph_aml.rules.exceptions import RuleInputError


def require_columns(frame: pd.DataFrame, columns: tuple[str, ...], frame_name: str) -> None:
    """Require a DataFrame to contain all expected columns."""

    missing = set(columns).difference(frame.columns)
    if missing:
        raise RuleInputError(f"{frame_name} is missing required columns: {sorted(missing)}")


def normalise_rule_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    """Prepare staged transactions for rule execution."""

    require_columns(
        transactions,
        (
            "transaction_id",
            "sender_account_id",
            "transaction_timestamp",
            "amount",
            "transaction_type",
        ),
        "transactions",
    )
    try:
        frame = transactions.copy()
        frame["transaction_id"] = frame["transaction_id"].apply(_normalise_identifier)
        frame["sender_account_id"] = frame["sender_account_id"].apply(_normalise_identifier)
        if "receiver_account_id" in frame.columns:
            frame["receiver_account_id"] = frame["receiver_account_id"].apply(_normalise_identifier)
        if "counterparty_id" in frame.columns:
            frame["counterparty_id"] = frame["counterparty_id"].apply(_normalise_identifier)
        frame["transaction_timestamp"] = pd.to_datetime(
            frame["transaction_timestamp"],
            utc=True,
            errors="coerce",
        )
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
        frame["transaction_type"] = frame["transaction_type"].apply(
            lambda value: None if pd.isna(value) else str(value).strip().lower()
        )
        frame = frame[
            frame["transaction_id"].notna()
            & frame["sender_account_id"].notna()
            & frame["transaction_timestamp"].notna()
            & frame["amount"].notna()
            & (frame["amount"] > 0)
        ].copy()
        return frame.sort_values(
            ["sender_account_id", "transaction_timestamp", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleInputError(f"Failed to normalise rule transactions: {exc}") from exc


def attach_customer_ids(
    alerts_frame: pd.DataFrame,
    accounts: pd.DataFrame,
) -> pd.DataFrame:
    """Attach customer IDs from staged accounts to alert candidate rows."""

    require_columns(alerts_frame, ("account_id",), "alerts_frame")
    try:
        output = alerts_frame.copy()
        if "customer_id" in output.columns:
            output = output.drop(columns=["customer_id"])
        if (
            accounts.empty
            or "account_id" not in accounts.columns
            or "customer_id" not in accounts.columns
        ):
            output["customer_id"] = pd.NA
            return output
        account_lookup = accounts.loc[:, ["account_id", "customer_id"]].copy()
        account_lookup["account_id"] = account_lookup["account_id"].apply(_normalise_identifier)
        return output.merge(
            account_lookup.drop_duplicates("account_id", keep="last"),
            on="account_id",
            how="left",
        )
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleInputError(f"Failed to attach customer IDs: {exc}") from exc


def build_rule_reason_code(
    count: int,
    threshold: float,
    window_hours: int,
    template: str | None = None,
) -> str:
    """Build deterministic human-readable rule reason text."""

    if template is not None:
        return template.format(
            count=count,
            threshold=threshold,
            window_hours=window_hours,
        )
    return f"{count} transfers below threshold within {window_hours} hours"


def build_count_window_reason_code(
    count: int,
    unit_label: str,
    window_value: int,
    window_unit: str,
    template: str | None = None,
) -> str:
    """Build deterministic count-within-window reason text for AML rules."""

    if count <= 0:
        raise RuleInputError("count must be positive")
    if window_value <= 0:
        raise RuleInputError("window_value must be positive")
    unit = str(unit_label).strip()
    window = str(window_unit).strip()
    if not unit:
        raise RuleInputError("unit_label must be non-empty")
    if not window:
        raise RuleInputError("window_unit must be non-empty")
    if template is not None:
        return template.format(
            count=count,
            unit_label=unit,
            window_value=window_value,
            window_unit=window,
        )
    return f"{count} {unit} within {window_value} {window}"


def _normalise_identifier(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text.upper()
