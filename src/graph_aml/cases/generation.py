"""Case record generation from deterministic alert groups."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine

from graph_aml.cases.config import CaseGenerationConfig
from graph_aml.cases.exceptions import CaseGenerationError
from graph_aml.cases.grouping import (
    CASE_ALERT_LINK_COLUMNS,
    CASE_ENTITY_LINK_COLUMNS,
    CASE_RECORD_COLUMNS,
    build_case_groups,
    build_case_id,
    normalise_case_list,
)
from graph_aml.cases.summary import summarise_generated_cases


@dataclass(frozen=True)
class CaseGenerationResult:
    cases: pd.DataFrame
    case_alerts: pd.DataFrame
    case_entities: pd.DataFrame
    groups: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def _empty_generation_result(
    config: CaseGenerationConfig, groups: pd.DataFrame | None = None
) -> CaseGenerationResult:
    empty_cases = pd.DataFrame(columns=CASE_RECORD_COLUMNS)
    return CaseGenerationResult(
        cases=empty_cases,
        case_alerts=pd.DataFrame(columns=CASE_ALERT_LINK_COLUMNS),
        case_entities=pd.DataFrame(columns=CASE_ENTITY_LINK_COLUMNS),
        groups=groups if groups is not None else pd.DataFrame(),
        summary=summarise_generated_cases(empty_cases),
        metadata={"case_version": config.case_version},
    )


def _clip_score(value: object) -> float:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").fillna(0).iloc[0]
    return float(max(0.0, min(100.0, number)))


def _severity_from_priority(priority_score: float) -> str:
    if priority_score >= 90:
        return "critical"
    if priority_score >= 75:
        return "high"
    if priority_score >= 50:
        return "medium"
    return "low"


def _max_alert_severity(alerts: pd.DataFrame, fallback_priority: float) -> str:
    severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    if alerts.empty or "severity" not in alerts.columns:
        return _severity_from_priority(fallback_priority)
    values = alerts["severity"].astype(str).str.lower()
    scored = [(severity_rank.get(value, 0), value) for value in values]
    scored = [item for item in scored if item[0] > 0]
    if not scored:
        return _severity_from_priority(fallback_priority)
    return cast(str, max(scored)[1])


def _safe_sum_transactions(transactions: pd.DataFrame, transaction_ids: tuple[str, ...]) -> float:
    if transactions.empty or not transaction_ids or "transaction_id" not in transactions.columns:
        return 0.0
    amount_col = "amount" if "amount" in transactions.columns else "transaction_amount"
    if amount_col not in transactions.columns:
        return 0.0
    frame = transactions[transactions["transaction_id"].astype(str).isin(transaction_ids)]
    return float(pd.to_numeric(frame[amount_col], errors="coerce").fillna(0).sum())


def _max_account_risk(account_risk_scores: pd.DataFrame, account_ids: tuple[str, ...]) -> float:
    if (
        account_risk_scores.empty
        or not account_ids
        or "account_id" not in account_risk_scores.columns
    ):
        return 0.0
    if "account_risk_score" not in account_risk_scores.columns:
        return 0.0
    frame = account_risk_scores[account_risk_scores["account_id"].astype(str).isin(account_ids)]
    if frame.empty:
        return 0.0
    return _clip_score(pd.to_numeric(frame["account_risk_score"], errors="coerce").fillna(0).max())


def _priority_score(
    alert_count: int,
    max_account_risk_score: float,
    max_rule_risk_score: float,
    config: CaseGenerationConfig,
) -> float:
    candidates: list[float] = []
    if config.priority.use_account_risk_score:
        candidates.append(max_account_risk_score)
    if config.priority.use_max_alert_score:
        candidates.append(max_rule_risk_score)
    score = max(candidates) if candidates else 0.0
    if config.priority.use_alert_count_uplift:
        uplift = min(
            config.priority.max_alert_count_uplift,
            max(0, alert_count - 1) * config.priority.alert_count_uplift_per_alert,
        )
        score += uplift
    return _clip_score(score)


def build_case_summary_text(case_row: dict[str, object] | pd.Series) -> str:
    """Build compact deterministic case summary text."""

    row = case_row.to_dict() if isinstance(case_row, pd.Series) else dict(case_row)
    alert_count = int(row.get("alert_count", 0) or 0)
    typology_count = int(row.get("unique_typology_count", 0) or 0)
    account_id = row.get("primary_account_id") or "unknown account"
    severity = str(row.get("severity") or "low")
    priority = float(row.get("priority_score", 0) or 0)
    strategy = str(row.get("grouping_strategy") or "group")
    return (
        f"{alert_count} alerts for {account_id} grouped by {strategy}; "
        f"{typology_count} typologies; {severity} severity; priority {priority:.2f}."
    )


def _case_entity_rows(
    case_id: str,
    primary_account_id: str | None,
    primary_customer_id: str | None,
    account_ids: tuple[str, ...],
    customer_ids: tuple[str, ...],
    transaction_ids: tuple[str, ...],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for account_id in account_ids:
        rows.append(
            {
                "case_id": case_id,
                "entity_type": "account",
                "entity_id": account_id,
                "relationship": "primary_account"
                if account_id == primary_account_id
                else "related_account",
            }
        )
    for customer_id in customer_ids:
        rows.append(
            {
                "case_id": case_id,
                "entity_type": "customer",
                "entity_id": customer_id,
                "relationship": "primary_customer"
                if customer_id == primary_customer_id
                else "related_customer",
            }
        )
    for transaction_id in transaction_ids:
        rows.append(
            {
                "case_id": case_id,
                "entity_type": "transaction",
                "entity_id": transaction_id,
                "relationship": "evidence_transaction",
            }
        )
    return rows


def generate_cases_from_groups(
    groups: pd.DataFrame,
    alerts: pd.DataFrame,
    account_risk_scores: pd.DataFrame,
    transactions: pd.DataFrame,
    config: CaseGenerationConfig | None = None,
) -> CaseGenerationResult:
    """Generate case records and links from case groups."""

    resolved = CaseGenerationConfig() if config is None else config
    if groups.empty:
        return _empty_generation_result(resolved, groups)
    if "alert_id" not in alerts.columns:
        raise CaseGenerationError("alerts must include alert_id")
    try:
        alert_frame = alerts.copy(deep=True)
        alert_frame["alert_id"] = alert_frame["alert_id"].astype(str)
        now = datetime.now(UTC)
        cases: list[dict[str, object]] = []
        case_alert_rows: list[dict[str, object]] = []
        case_entity_rows: list[dict[str, object]] = []
        for group in groups.to_dict("records"):
            alert_ids = normalise_case_list(group.get("alert_ids"))
            account_ids = normalise_case_list(group.get("account_ids"))
            customer_ids = normalise_case_list(group.get("customer_ids"))
            transaction_ids = normalise_case_list(group.get("transaction_ids"))
            group_alerts = alert_frame[alert_frame["alert_id"].isin(alert_ids)]
            if group_alerts.empty:
                continue
            rule_scores = pd.to_numeric(
                group_alerts.get("risk_score_rule", 0), errors="coerce"
            ).fillna(0)
            max_rule_score = _clip_score(rule_scores.max())
            mean_rule_score = _clip_score(rule_scores.mean())
            max_account_risk = _max_account_risk(account_risk_scores, account_ids)
            priority = _priority_score(len(alert_ids), max_account_risk, max_rule_score, resolved)
            severity = _max_alert_severity(group_alerts, priority)
            case_id = build_case_id(str(group["case_group_id"]), resolved.case_version)
            typologies = normalise_case_list(group.get("typologies"))
            rule_names = normalise_case_list(group.get("rule_names"))
            primary_account_id = str(group.get("primary_account_id") or "") or None
            primary_customer_id = str(group.get("primary_customer_id") or "") or None
            row = {
                "case_id": case_id,
                "case_version": resolved.case_version,
                "primary_account_id": primary_account_id,
                "primary_customer_id": primary_customer_id,
                "related_accounts": list(account_ids),
                "related_customers": list(customer_ids),
                "alert_ids": list(alert_ids),
                "typologies": list(typologies),
                "rule_names": list(rule_names),
                "total_transaction_value": _safe_sum_transactions(transactions, transaction_ids),
                "alert_count": int(len(alert_ids)),
                "unique_typology_count": int(len(typologies)),
                "evidence_transaction_count": int(len(transaction_ids)),
                "max_rule_risk_score": max_rule_score,
                "mean_rule_risk_score": mean_rule_score,
                "max_account_risk_score": max_account_risk,
                "priority_score": priority,
                "severity": severity,
                "status": resolved.default_status,
                "grouping_strategy": group.get("grouping_strategy"),
                "case_group_key": group.get("case_group_key"),
                "summary": "",
                "created_at": now,
                "updated_at": now,
            }
            row["summary"] = build_case_summary_text(row)
            cases.append(row)
            case_alert_rows.extend(
                {"case_id": case_id, "alert_id": alert_id} for alert_id in alert_ids
            )
            case_entity_rows.extend(
                _case_entity_rows(
                    case_id,
                    primary_account_id,
                    primary_customer_id,
                    account_ids,
                    customer_ids,
                    transaction_ids,
                )
            )
        case_frame = pd.DataFrame(cases, columns=CASE_RECORD_COLUMNS)
        if not case_frame.empty:
            case_frame = case_frame.sort_values(
                ["priority_score", "case_id"],
                ascending=[False, True],
                kind="mergesort",
            ).reset_index(drop=True)
        alert_links = pd.DataFrame(
            case_alert_rows, columns=CASE_ALERT_LINK_COLUMNS
        ).drop_duplicates()
        entity_links = pd.DataFrame(
            case_entity_rows, columns=CASE_ENTITY_LINK_COLUMNS
        ).drop_duplicates()
        alert_links = alert_links.sort_values(
            list(CASE_ALERT_LINK_COLUMNS), kind="mergesort"
        ).reset_index(drop=True)
        entity_links = entity_links.sort_values(
            list(CASE_ENTITY_LINK_COLUMNS), kind="mergesort"
        ).reset_index(drop=True)
        summary = summarise_generated_cases(case_frame)
        return CaseGenerationResult(
            cases=case_frame,
            case_alerts=alert_links,
            case_entities=entity_links,
            groups=groups.copy(deep=True),
            summary=summary,
            metadata={"case_version": resolved.case_version, "group_count": int(len(groups))},
        )
    except CaseGenerationError:
        raise
    except Exception as exc:
        raise CaseGenerationError(f"failed to generate cases: {exc}") from exc


def generate_cases_from_inputs(
    inputs: dict[str, pd.DataFrame],
    config: CaseGenerationConfig | None = None,
) -> CaseGenerationResult:
    """Generate cases from input frame dictionary."""

    resolved = CaseGenerationConfig() if config is None else config
    try:
        groups = build_case_groups(
            inputs.get("alerts", pd.DataFrame()),
            inputs.get("accounts", pd.DataFrame()),
            inputs.get("graph_features", pd.DataFrame()),
            inputs.get("transactions", pd.DataFrame()),
            resolved,
        )
        return generate_cases_from_groups(
            groups,
            inputs.get("alerts", pd.DataFrame()),
            inputs.get("account_risk_scores", pd.DataFrame()),
            inputs.get("transactions", pd.DataFrame()),
            resolved,
        )
    except Exception as exc:
        if isinstance(exc, CaseGenerationError):
            raise
        raise CaseGenerationError(f"failed to generate cases from inputs: {exc}") from exc


def generate_and_persist_cases(
    engine: Engine,
    generation_config: CaseGenerationConfig | None = None,
    persistence_config: Any | None = None,
    limit: int | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> tuple[CaseGenerationResult, Any]:
    """Read inputs, generate cases, and persist them."""

    resolved = CaseGenerationConfig() if generation_config is None else generation_config
    try:
        from graph_aml.cases.inputs import read_case_inputs
        from graph_aml.cases.persistence import CasePersistenceConfig, persist_cases

        inputs = read_case_inputs(engine, resolved, limit=limit)
        result = generate_cases_from_inputs(inputs, resolved)
        persist_config = persistence_config or CasePersistenceConfig(
            case_version=resolved.case_version
        )
        persistence_result = persist_cases(
            engine,
            result,
            persist_config,
            extra_metadata=extra_metadata,
        )
        return result, persistence_result
    except Exception as exc:
        if isinstance(exc, CaseGenerationError):
            raise
        raise CaseGenerationError(f"failed to generate and persist cases: {exc}") from exc
