"""Decision-to-label mapping and account label propagation."""

from __future__ import annotations

import pandas as pd

from graph_aml.labels.config import AnalystLabelConfig
from graph_aml.labels.exceptions import LabelMappingError

CASE_LABEL_COLUMNS = (
    "case_id",
    "label_version",
    "case_label",
    "label_name",
    "source_status",
    "source_action_type",
    "analyst_id",
    "decision_reason",
    "comment",
    "label_timestamp",
    "case_created_at",
    "case_updated_at",
    "metadata",
)

ACCOUNT_LABEL_COLUMNS = (
    "account_id",
    "label_version",
    "account_label",
    "label_name",
    "source_case_ids",
    "source_case_labels",
    "label_timestamp",
    "metadata",
)


def _config(config: AnalystLabelConfig | None) -> AnalystLabelConfig:
    return config or AnalystLabelConfig()


def _empty(columns: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _missing(value: object) -> bool:
    return (
        value is None
        or (isinstance(value, float) and pd.isna(value))
        or str(value).strip() == ""
    )


def normalise_label_status(value: object) -> str:
    """Trim lifecycle status labels deterministically."""

    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def map_status_to_binary_label(
    status: object,
    config: AnalystLabelConfig | None = None,
) -> int | None:
    """Map configured closure statuses to binary labels."""

    resolved = _config(config)
    clean = normalise_label_status(status)
    if not clean or clean in resolved.excluded_statuses:
        return None
    return resolved.decision_label_mapping.get(clean)


def label_name_from_binary_value(value: int | None) -> str:
    """Return a stable display name for a binary analyst label."""

    if value == 1:
        return "suspicious"
    if value == 0:
        return "false_positive"
    return "unlabelled"


def select_latest_eligible_decision_events(
    lifecycle_events: pd.DataFrame,
    config: AnalystLabelConfig | None = None,
) -> pd.DataFrame:
    """Select the latest eligible closure decision per case."""

    resolved = _config(config)
    if not isinstance(lifecycle_events, pd.DataFrame):
        raise LabelMappingError("lifecycle_events must be a DataFrame")
    if lifecycle_events.empty:
        return lifecycle_events.copy()
    required = {"case_id", "to_status", resolved.leakage_controls.label_timestamp_column}
    missing = required - set(lifecycle_events.columns)
    if missing:
        raise LabelMappingError(f"missing lifecycle event columns: {sorted(missing)}")
    frame = lifecycle_events.copy(deep=True)
    frame["_source_status"] = frame["to_status"].map(normalise_label_status)
    frame["_case_label"] = frame["_source_status"].map(
        lambda status: map_status_to_binary_label(status, resolved)
    )
    frame = frame[frame["_case_label"].notna()].copy()
    if frame.empty:
        drop_columns = [col for col in ("_source_status", "_case_label") if col in frame]
        return frame.drop(columns=drop_columns)
    timestamp_col = resolved.leakage_controls.label_timestamp_column
    frame["_label_timestamp_sort"] = pd.to_datetime(frame[timestamp_col], errors="coerce", utc=True)
    if frame["_label_timestamp_sort"].isna().any():
        raise LabelMappingError("eligible lifecycle events require label timestamps")
    if "action_id" not in frame.columns:
        frame["action_id"] = ""
    frame = frame.sort_values(
        ["case_id", "_label_timestamp_sort", "action_id"],
        ascending=[True, False, False],
        kind="mergesort",
    )
    selected = frame.drop_duplicates("case_id", keep="first").copy()
    return selected.drop(columns=["_label_timestamp_sort"])


def build_case_labels(
    cases: pd.DataFrame,
    lifecycle_events: pd.DataFrame,
    config: AnalystLabelConfig | None = None,
) -> pd.DataFrame:
    """Build one analyst case label per closed labelled case."""

    resolved = _config(config)
    if not isinstance(cases, pd.DataFrame) or not isinstance(lifecycle_events, pd.DataFrame):
        raise LabelMappingError("cases and lifecycle_events must be DataFrames")
    if cases.empty or lifecycle_events.empty:
        return _empty(CASE_LABEL_COLUMNS)
    if "case_id" not in cases.columns:
        raise LabelMappingError("cases must include case_id")
    latest = select_latest_eligible_decision_events(lifecycle_events, resolved)
    if latest.empty:
        return _empty(CASE_LABEL_COLUMNS)
    case_lookup = cases.copy(deep=True).drop_duplicates("case_id", keep="first")
    merged = latest.merge(case_lookup, on="case_id", how="left", suffixes=("_event", "_case"))
    rows: list[dict[str, object]] = []
    timestamp_col = resolved.leakage_controls.label_timestamp_column
    for row in merged.to_dict("records"):
        source_status = normalise_label_status(row.get("to_status"))
        label = map_status_to_binary_label(source_status, resolved)
        if label is None:
            continue
        reason = row.get("decision_reason")
        comment = row.get("comment")
        if resolved.label_quality.require_closure_reason and _missing(reason):
            raise LabelMappingError("closure labels require decision_reason")
        if resolved.label_quality.require_comment_for_closure and _missing(comment):
            raise LabelMappingError("closure labels require comment")
        label_timestamp = pd.to_datetime(row.get(timestamp_col), errors="coerce", utc=True)
        if pd.isna(label_timestamp):
            raise LabelMappingError("label timestamp is required")
        case_created_at = row.get("created_at")
        created_ts = pd.to_datetime(case_created_at, errors="coerce", utc=True)
        if (
            resolved.leakage_controls.enforce_label_timestamp_after_case_created
            and not pd.isna(created_ts)
            and label_timestamp < created_ts
        ):
            raise LabelMappingError("label timestamp is before case creation")
        rows.append(
            {
                "case_id": str(row["case_id"]),
                "label_version": resolved.label_version,
                "case_label": int(label),
                "label_name": label_name_from_binary_value(label),
                "source_status": source_status,
                "source_action_type": row.get("action_type"),
                "analyst_id": row.get("analyst_id"),
                "decision_reason": reason,
                "comment": comment,
                "label_timestamp": label_timestamp,
                "case_created_at": created_ts if not pd.isna(created_ts) else None,
                "case_updated_at": row.get("updated_at"),
                "metadata": {
                    "action_id": row.get("action_id"),
                    "label_source": "case_lifecycle_event",
                },
            }
        )
    return (
        pd.DataFrame(rows, columns=CASE_LABEL_COLUMNS)
        .sort_values("case_id")
        .reset_index(drop=True)
    )


def _case_account_links(
    case_labels: pd.DataFrame,
    cases: pd.DataFrame,
    case_entities: pd.DataFrame,
    config: AnalystLabelConfig,
) -> pd.DataFrame:
    links: list[dict[str, object]] = []
    label_case_ids = set(case_labels["case_id"].astype(str))
    if config.propagation.include_primary_account and "primary_account_id" in cases.columns:
        for row in cases[cases["case_id"].astype(str).isin(label_case_ids)].to_dict("records"):
            account_id = row.get("primary_account_id")
            if not _missing(account_id):
                links.append(
                    {
                        "case_id": str(row["case_id"]),
                        "account_id": str(account_id),
                        "relationship": "primary_account",
                    }
                )
    if config.propagation.include_related_accounts and not case_entities.empty:
        required = {"case_id", "entity_type", "entity_id"}
        if not required.issubset(case_entities.columns):
            raise LabelMappingError("case_entities must include case_id, entity_type, entity_id")
        frame = case_entities.copy(deep=True)
        mask = frame["case_id"].astype(str).isin(label_case_ids)
        mask &= frame["entity_type"].astype(str).str.lower().eq("account")
        for row in frame[mask].to_dict("records"):
            account_id = row.get("entity_id")
            if not _missing(account_id):
                links.append(
                    {
                        "case_id": str(row["case_id"]),
                        "account_id": str(account_id),
                        "relationship": row.get("relationship", "related_account"),
                    }
                )
    return pd.DataFrame(links).drop_duplicates() if links else pd.DataFrame()


def build_account_labels(
    case_labels: pd.DataFrame,
    cases: pd.DataFrame,
    case_entities: pd.DataFrame,
    config: AnalystLabelConfig | None = None,
) -> pd.DataFrame:
    """Propagate case labels to account-level labels."""

    resolved = _config(config)
    if not isinstance(case_labels, pd.DataFrame):
        raise LabelMappingError("case_labels must be a DataFrame")
    if case_labels.empty:
        return _empty(ACCOUNT_LABEL_COLUMNS)
    if not {"case_id", "case_label", "label_timestamp"}.issubset(case_labels.columns):
        raise LabelMappingError("case_labels missing required columns")
    links = _case_account_links(case_labels, cases, case_entities, resolved)
    if links.empty:
        return _empty(ACCOUNT_LABEL_COLUMNS)
    merged = links.merge(case_labels, on="case_id", how="inner")
    rows: list[dict[str, object]] = []
    for account_id, group in merged.groupby("account_id", sort=True):
        ordered = group.copy()
        ordered["_label_timestamp_sort"] = pd.to_datetime(
            ordered["label_timestamp"],
            errors="coerce",
            utc=True,
        )
        ordered = ordered.sort_values(
            ["_label_timestamp_sort", "case_id"],
            ascending=[False, True],
            kind="mergesort",
        )
        source_case_ids = ordered["case_id"].astype(str).tolist()
        source_case_labels = [int(value) for value in ordered["case_label"].tolist()]
        if resolved.propagation.account_label_strategy == "latest_case_label":
            account_label = int(ordered.iloc[0]["case_label"])
        else:
            account_label = int(max(source_case_labels))
        rows.append(
            {
                "account_id": str(account_id),
                "label_version": resolved.label_version,
                "account_label": account_label,
                "label_name": label_name_from_binary_value(account_label),
                "source_case_ids": source_case_ids,
                "source_case_labels": source_case_labels,
                "label_timestamp": ordered.iloc[0]["_label_timestamp_sort"],
                "metadata": {
                    "strategy": resolved.propagation.account_label_strategy,
                    "source_case_count": len(source_case_ids),
                },
            }
        )
    return (
        pd.DataFrame(rows, columns=ACCOUNT_LABEL_COLUMNS)
        .sort_values("account_id")
        .reset_index(drop=True)
    )
