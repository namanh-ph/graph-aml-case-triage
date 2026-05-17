"""Deterministic alert grouping strategies for AML case generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

import pandas as pd

from graph_aml.cases.config import CaseGenerationConfig
from graph_aml.cases.exceptions import CaseGroupingError

CASE_GROUP_COLUMNS = (
    "case_group_id",
    "grouping_strategy",
    "primary_account_id",
    "primary_customer_id",
    "alert_ids",
    "account_ids",
    "customer_ids",
    "transaction_ids",
    "typologies",
    "rule_names",
    "case_group_key",
)

CASE_RECORD_COLUMNS = (
    "case_id",
    "case_version",
    "primary_account_id",
    "primary_customer_id",
    "related_accounts",
    "related_customers",
    "alert_ids",
    "typologies",
    "rule_names",
    "total_transaction_value",
    "alert_count",
    "unique_typology_count",
    "evidence_transaction_count",
    "max_rule_risk_score",
    "mean_rule_risk_score",
    "max_account_risk_score",
    "priority_score",
    "severity",
    "status",
    "grouping_strategy",
    "case_group_key",
    "summary",
    "created_at",
    "updated_at",
)

CASE_ALERT_LINK_COLUMNS = ("case_id", "alert_id")

CASE_ENTITY_LINK_COLUMNS = ("case_id", "entity_type", "entity_id", "relationship")

_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _empty_groups() -> pd.DataFrame:
    return pd.DataFrame(columns=CASE_GROUP_COLUMNS)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _stable_unique(values: Iterable[object]) -> tuple[str, ...]:
    cleaned = {
        str(value).strip() for value in values if not _is_missing(value) and str(value).strip()
    }
    return tuple(sorted(cleaned))


def normalise_case_list(value: object) -> tuple[str, ...]:
    """Normalise scalar, CSV, JSON, tuple, or list evidence values into a stable tuple."""

    try:
        if _is_missing(value):
            return ()
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return ()
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise CaseGroupingError(f"malformed JSON list: {text}") from exc
                if not isinstance(parsed, list):
                    raise CaseGroupingError("JSON evidence payload must be a list")
                return _stable_unique(parsed)
            if "," in text:
                return _stable_unique(part.strip() for part in text.split(","))
            return (text,)
        if isinstance(value, dict):
            raise CaseGroupingError("case list values cannot be mappings")
        if isinstance(value, Iterable):
            return _stable_unique(value)
        return (str(value),)
    except CaseGroupingError:
        raise
    except Exception as exc:
        raise CaseGroupingError(f"failed to normalise case list: {exc}") from exc


def explode_alert_evidence_ids(alerts: pd.DataFrame) -> pd.DataFrame:
    """Return one row per alert evidence identifier."""

    if "alert_id" not in alerts.columns:
        raise CaseGroupingError("alerts must include alert_id")
    evidence_col = "evidence_ids" if "evidence_ids" in alerts.columns else None
    rows: list[dict[str, object]] = []
    try:
        for row in alerts.copy(deep=True).to_dict("records"):
            alert_id = str(row.get("alert_id", "")).strip()
            if not alert_id:
                continue
            values = normalise_case_list(row.get(evidence_col)) if evidence_col else ()
            for evidence_id in values:
                rows.append({"alert_id": alert_id, "evidence_id": evidence_id})
        return pd.DataFrame(rows, columns=("alert_id", "evidence_id"))
    except CaseGroupingError:
        raise
    except Exception as exc:
        raise CaseGroupingError(f"failed to explode alert evidence IDs: {exc}") from exc


def _safe_id_part(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_") or "case"


def build_case_group_id(
    grouping_strategy: str,
    case_group_key: str,
    alert_ids: tuple[str, ...] | list[str],
) -> str:
    """Build a deterministic case group ID."""

    alerts = "|".join(sorted(str(alert_id) for alert_id in alert_ids))
    payload = f"{grouping_strategy}|{case_group_key}|{alerts}"
    suffix = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"CASE_GROUP_{_safe_id_part(grouping_strategy).upper()}_{suffix}"


def build_case_id(case_group_id: str, case_version: str) -> str:
    """Build a deterministic case ID from group ID and case version."""

    payload = f"{case_version}|{case_group_id}"
    suffix = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"CASE_{_safe_id_part(case_version).upper()}_{suffix}"


def _alert_sort_frame(alerts: pd.DataFrame) -> pd.DataFrame:
    frame = alerts.copy(deep=True)
    frame["_severity_rank"] = (
        frame.get("severity", "").astype(str).str.lower().map(_SEVERITY_RANK).fillna(0)
    )
    frame["_rule_score"] = pd.to_numeric(frame.get("risk_score_rule", 0), errors="coerce").fillna(0)
    return frame.sort_values(
        by=["_severity_rank", "_rule_score", "alert_id"],
        ascending=[False, False, True],
        kind="mergesort",
    )


def _prepare_alerts(alerts: pd.DataFrame, config: CaseGenerationConfig) -> pd.DataFrame:
    if alerts.empty:
        return alerts.copy(deep=True)
    if "alert_id" not in alerts.columns or "account_id" not in alerts.columns:
        raise CaseGroupingError("alerts must include alert_id and account_id")
    frame = alerts.copy(deep=True)
    frame["alert_id"] = frame["alert_id"].astype(str)
    frame["account_id"] = frame["account_id"].astype(str)
    if "customer_id" not in frame.columns:
        frame["customer_id"] = None
    if "evidence_ids" not in frame.columns:
        frame["evidence_ids"] = [[] for _ in range(len(frame))]
    if "typology" not in frame.columns:
        frame["typology"] = ""
    if "rule_name" not in frame.columns:
        frame["rule_name"] = ""
    if "risk_score_rule" not in frame.columns:
        frame["risk_score_rule"] = 0.0
    return frame


def _truncate_alerts(alerts: pd.DataFrame, config: CaseGenerationConfig) -> pd.DataFrame:
    ordered = _alert_sort_frame(alerts)
    return ordered.head(config.thresholds.max_alerts_per_case).drop(
        columns=["_severity_rank", "_rule_score"],
        errors="ignore",
    )


def _make_group(
    grouping_strategy: str,
    case_group_key: str,
    alerts: pd.DataFrame,
    config: CaseGenerationConfig,
    account_ids: tuple[str, ...] | None = None,
    customer_ids: tuple[str, ...] | None = None,
) -> dict[str, object] | None:
    truncated = _truncate_alerts(alerts, config)
    if len(truncated) < config.thresholds.min_alerts_per_case:
        return None
    alert_ids = _stable_unique(truncated["alert_id"].tolist())
    accounts = account_ids or _stable_unique(truncated["account_id"].tolist())
    customers = customer_ids or _stable_unique(
        truncated.get("customer_id", pd.Series(dtype=object)).dropna().tolist()
    )
    transactions: list[str] = []
    for value in truncated.get("evidence_ids", pd.Series(dtype=object)).tolist():
        transactions.extend(normalise_case_list(value))
    typologies = _stable_unique(truncated.get("typology", pd.Series(dtype=object)).tolist())
    rule_names = _stable_unique(truncated.get("rule_name", pd.Series(dtype=object)).tolist())
    primary_account_id = accounts[0] if accounts else None
    primary_customer_id = customers[0] if customers else None
    group_id = build_case_group_id(grouping_strategy, case_group_key, alert_ids)
    return {
        "case_group_id": group_id,
        "grouping_strategy": grouping_strategy,
        "primary_account_id": primary_account_id,
        "primary_customer_id": primary_customer_id,
        "alert_ids": list(alert_ids),
        "account_ids": list(accounts),
        "customer_ids": list(customers),
        "transaction_ids": list(_stable_unique(transactions)),
        "typologies": list(typologies),
        "rule_names": list(rule_names),
        "case_group_key": case_group_key,
    }


def group_alerts_by_account(
    alerts: pd.DataFrame,
    accounts: pd.DataFrame | None = None,
    config: CaseGenerationConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseGenerationConfig() if config is None else config
    prepared = _prepare_alerts(alerts, resolved)
    if prepared.empty:
        return _empty_groups()
    try:
        if accounts is not None and not accounts.empty and "customer_id" in accounts.columns:
            mapping = accounts[["account_id", "customer_id"]].drop_duplicates("account_id")
            prepared = prepared.merge(
                mapping, on="account_id", how="left", suffixes=("", "_account")
            )
            prepared["customer_id"] = prepared["customer_id"].fillna(
                prepared.get("customer_id_account")
            )
        rows = []
        for account_id, group in prepared.groupby("account_id", sort=True):
            row = _make_group("account", str(account_id), group, resolved)
            if row is not None:
                rows.append(row)
        return pd.DataFrame(rows, columns=CASE_GROUP_COLUMNS)
    except CaseGroupingError:
        raise
    except Exception as exc:
        raise CaseGroupingError(f"failed to group alerts by account: {exc}") from exc


def group_alerts_by_customer(
    alerts: pd.DataFrame,
    accounts: pd.DataFrame,
    config: CaseGenerationConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseGenerationConfig() if config is None else config
    prepared = _prepare_alerts(alerts, resolved)
    if prepared.empty:
        return _empty_groups()
    if "account_id" not in accounts.columns or "customer_id" not in accounts.columns:
        raise CaseGroupingError("accounts must include account_id and customer_id")
    try:
        account_map = accounts[["account_id", "customer_id"]].drop_duplicates("account_id")
        frame = prepared.merge(account_map, on="account_id", how="left", suffixes=("", "_account"))
        frame["customer_id"] = frame["customer_id"].fillna(frame["customer_id_account"])
        frame = frame[frame["customer_id"].notna()]
        rows = []
        for customer_id, group in frame.groupby("customer_id", sort=True):
            customer_accounts = _stable_unique(
                accounts.loc[accounts["customer_id"] == customer_id, "account_id"].tolist()
            )
            row = _make_group(
                "customer", str(customer_id), group, resolved, account_ids=customer_accounts
            )
            if row is not None:
                rows.append(row)
        return pd.DataFrame(rows, columns=CASE_GROUP_COLUMNS)
    except CaseGroupingError:
        raise
    except Exception as exc:
        raise CaseGroupingError(f"failed to group alerts by customer: {exc}") from exc


def group_alerts_by_graph_community(
    alerts: pd.DataFrame,
    graph_features: pd.DataFrame,
    config: CaseGenerationConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseGenerationConfig() if config is None else config
    prepared = _prepare_alerts(alerts, resolved)
    if prepared.empty or graph_features.empty:
        return _empty_groups()
    if "account_id" not in graph_features.columns or "community_id" not in graph_features.columns:
        raise CaseGroupingError("graph_features must include account_id and community_id")
    try:
        graph = graph_features[["account_id", "community_id"]].drop_duplicates("account_id")
        frame = prepared.merge(graph, on="account_id", how="left")
        frame = frame[frame["community_id"].notna()]
        rows = []
        for community_id, group in frame.groupby("community_id", sort=True):
            community_value = (
                int(community_id) if float(community_id).is_integer() else community_id
            )
            key = f"community:{community_value}"
            row = _make_group("graph_community", key, group, resolved)
            if row is not None:
                rows.append(row)
        return pd.DataFrame(rows, columns=CASE_GROUP_COLUMNS)
    except CaseGroupingError:
        raise
    except Exception as exc:
        raise CaseGroupingError(f"failed to group alerts by graph community: {exc}") from exc


def group_alerts_by_circular_flow(
    alerts: pd.DataFrame,
    config: CaseGenerationConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseGenerationConfig() if config is None else config
    prepared = _prepare_alerts(alerts, resolved)
    if prepared.empty:
        return _empty_groups()
    try:
        typology = prepared.get("typology", "").astype(str).str.lower().str.replace(" ", "_")
        rule_name = prepared.get("rule_name", "").astype(str).str.lower()
        frame = prepared[
            (typology == "circular_flow") | (rule_name.isin(("circular flow", "circular_flow")))
        ]
        if frame.empty:
            return _empty_groups()
        keyed_rows: list[dict[str, Any]] = []
        for row in frame.to_dict("records"):
            metadata = row.get("metadata")
            metadata_payload = metadata if isinstance(metadata, dict) else {}
            cycle_accounts = (
                normalise_case_list(metadata_payload.get("cycle_accounts"))
                if metadata_payload
                else ()
            )
            evidence = normalise_case_list(row.get("evidence_ids"))
            if cycle_accounts:
                key = "cycle_accounts:" + "|".join(cycle_accounts)
            elif evidence:
                key = "evidence:" + "|".join(evidence)
            else:
                key = "account:" + str(row.get("account_id", ""))
            copied = dict(row)
            copied["_case_key"] = key
            keyed_rows.append(copied)
        keyed = pd.DataFrame(keyed_rows)
        rows = []
        for key, group in keyed.groupby("_case_key", sort=True):
            row = _make_group("circular_flow", str(key), group, resolved)
            if row is not None:
                rows.append(row)
        return pd.DataFrame(rows, columns=CASE_GROUP_COLUMNS)
    except CaseGroupingError:
        raise
    except Exception as exc:
        raise CaseGroupingError(f"failed to group circular flow alerts: {exc}") from exc


def group_alerts_by_common_counterparty(
    alerts: pd.DataFrame,
    transactions: pd.DataFrame,
    config: CaseGenerationConfig | None = None,
) -> pd.DataFrame:
    resolved = CaseGenerationConfig() if config is None else config
    prepared = _prepare_alerts(alerts, resolved)
    if prepared.empty or transactions.empty:
        return _empty_groups()
    if (
        "transaction_id" not in transactions.columns
        or "counterparty_id" not in transactions.columns
    ):
        raise CaseGroupingError("transactions must include transaction_id and counterparty_id")
    try:
        evidence = explode_alert_evidence_ids(prepared)
        if evidence.empty:
            return _empty_groups()
        tx = transactions[["transaction_id", "counterparty_id"]].copy(deep=True)
        joined = evidence.merge(tx, left_on="evidence_id", right_on="transaction_id", how="left")
        joined = joined[joined["counterparty_id"].notna()]
        if joined.empty:
            return _empty_groups()
        alert_counterparties = joined[["alert_id", "counterparty_id"]].drop_duplicates()
        frame = prepared.merge(alert_counterparties, on="alert_id", how="inner")
        rows = []
        for counterparty_id, group in frame.groupby("counterparty_id", sort=True):
            row = _make_group("common_counterparty", str(counterparty_id), group, resolved)
            if row is not None:
                rows.append(row)
        return pd.DataFrame(rows, columns=CASE_GROUP_COLUMNS)
    except CaseGroupingError:
        raise
    except Exception as exc:
        raise CaseGroupingError(f"failed to group alerts by common counterparty: {exc}") from exc


def _drop_equivalent_groups(groups: pd.DataFrame) -> pd.DataFrame:
    if groups.empty:
        return groups
    frame = groups.copy(deep=True)
    frame["_alert_key"] = frame["alert_ids"].apply(
        lambda value: "|".join(normalise_case_list(value))
    )
    frame = frame.sort_values(
        ["grouping_strategy", "_alert_key", "case_group_id"], kind="mergesort"
    )
    frame = frame.drop_duplicates(["grouping_strategy", "_alert_key"], keep="first")
    return frame.drop(columns=["_alert_key"])


def build_case_groups(
    alerts: pd.DataFrame,
    accounts: pd.DataFrame,
    graph_features: pd.DataFrame,
    transactions: pd.DataFrame,
    config: CaseGenerationConfig | None = None,
) -> pd.DataFrame:
    """Build deterministic case groups from enabled grouping strategies."""

    resolved = CaseGenerationConfig() if config is None else config
    if alerts.empty:
        return _empty_groups()
    try:
        frames: list[pd.DataFrame] = []
        if resolved.grouping.group_by_account:
            frames.append(group_alerts_by_account(alerts, accounts, resolved))
        if resolved.grouping.group_by_customer:
            frames.append(group_alerts_by_customer(alerts, accounts, resolved))
        if resolved.grouping.group_by_graph_community:
            frames.append(group_alerts_by_graph_community(alerts, graph_features, resolved))
        if resolved.grouping.group_by_circular_flow:
            frames.append(group_alerts_by_circular_flow(alerts, resolved))
        if resolved.grouping.group_by_common_counterparty:
            frames.append(group_alerts_by_common_counterparty(alerts, transactions, resolved))
        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return _empty_groups()
        combined = _drop_equivalent_groups(pd.concat(frames, ignore_index=True))
        combined = combined.sort_values(
            ["primary_account_id", "grouping_strategy", "case_group_id"],
            na_position="last",
            kind="mergesort",
        )
        combined["_account_case_order"] = (
            combined.groupby("primary_account_id", dropna=False).cumcount() + 1
        )
        combined = combined[
            combined["_account_case_order"] <= resolved.thresholds.max_cases_per_account
        ].drop(columns=["_account_case_order"])
        combined = combined.head(resolved.thresholds.max_cases_total)
        return combined.loc[:, CASE_GROUP_COLUMNS].reset_index(drop=True)
    except CaseGroupingError:
        raise
    except Exception as exc:
        raise CaseGroupingError(f"failed to build case groups: {exc}") from exc
