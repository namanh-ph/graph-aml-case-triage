"""Summary helpers for generated AML cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from graph_aml.cases.evidence_builders import CaseEvidenceBuildResult
    from graph_aml.cases.generation import CaseGenerationResult
    from graph_aml.cases.risk_scoring import CaseRiskScoreResult


def _counts(series: pd.Series) -> dict[str, int]:
    if series.empty:
        return {}
    return {
        str(key): int(value)
        for key, value in series.astype(str).value_counts().sort_index().items()
    }


def summarise_case_groups(groups: pd.DataFrame) -> dict[str, object]:
    """Build a JSON-serialisable summary for case groups."""

    if groups.empty:
        return {
            "case_group_count": 0,
            "unique_primary_account_count": 0,
            "grouping_strategy_counts": {},
        }
    return {
        "case_group_count": int(len(groups)),
        "unique_primary_account_count": int(groups["primary_account_id"].nunique(dropna=True))
        if "primary_account_id" in groups.columns
        else 0,
        "grouping_strategy_counts": _counts(groups["grouping_strategy"])
        if "grouping_strategy" in groups.columns
        else {},
    }


def summarise_generated_cases(cases: pd.DataFrame) -> dict[str, object]:
    """Build a JSON-serialisable summary for generated cases."""

    if cases.empty:
        return {
            "case_count": 0,
            "unique_primary_account_count": 0,
            "status_counts": {},
            "severity_counts": {},
            "grouping_strategy_counts": {},
            "mean_alert_count": 0.0,
            "max_alert_count": 0,
            "max_priority_score": 0.0,
            "mean_priority_score": 0.0,
        }
    priority = pd.to_numeric(
        cases.get("priority_score", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0)
    alert_count = pd.to_numeric(
        cases.get("alert_count", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0)
    return {
        "case_count": int(len(cases)),
        "unique_primary_account_count": int(cases["primary_account_id"].nunique(dropna=True))
        if "primary_account_id" in cases.columns
        else 0,
        "status_counts": _counts(cases["status"]) if "status" in cases.columns else {},
        "severity_counts": _counts(cases["severity"]) if "severity" in cases.columns else {},
        "grouping_strategy_counts": _counts(cases["grouping_strategy"])
        if "grouping_strategy" in cases.columns
        else {},
        "mean_alert_count": float(alert_count.mean()) if len(alert_count) else 0.0,
        "max_alert_count": int(alert_count.max()) if len(alert_count) else 0,
        "max_priority_score": float(priority.max()) if len(priority) else 0.0,
        "mean_priority_score": float(priority.mean()) if len(priority) else 0.0,
    }


def case_generation_result_to_dict(result: CaseGenerationResult) -> dict[str, object]:
    """Convert a case generation result into a compact serialisable payload."""

    return {
        "summary": dict(result.summary),
        "metadata": dict(result.metadata),
        "case_count": int(len(result.cases)),
        "case_alert_link_count": int(len(result.case_alerts)),
        "case_entity_link_count": int(len(result.case_entities)),
        "case_group_count": int(len(result.groups)),
    }


def summarise_case_risk_components(components: pd.DataFrame) -> dict[str, object]:
    """Build a serialisable summary of case risk components."""

    if components.empty:
        return {
            "row_count": 0,
            "component_means": {},
            "mean_component_coverage": 0.0,
        }
    component_cols = [
        column for column in components.columns if column.endswith("_score") and column != "case_id"
    ]
    return {
        "row_count": int(len(components)),
        "component_means": {
            column: float(pd.to_numeric(components[column], errors="coerce").fillna(0).mean())
            for column in component_cols
        },
        "mean_component_coverage": float(
            pd.to_numeric(components["component_coverage"], errors="coerce").fillna(0).mean()
        )
        if "component_coverage" in components.columns
        else 0.0,
    }


def summarise_case_risk_scores(scores: pd.DataFrame) -> dict[str, object]:
    """Build a serialisable summary of case risk scores."""

    if scores.empty:
        return {
            "row_count": 0,
            "unique_case_count": 0,
            "risk_band_counts": {},
            "min_score": 0.0,
            "max_score": 0.0,
            "mean_score": 0.0,
            "mean_total_transaction_value": 0.0,
        }
    case_scores = pd.to_numeric(scores["case_risk_score"], errors="coerce").fillna(0)
    values = pd.to_numeric(scores.get("total_transaction_value", 0), errors="coerce").fillna(0)
    return {
        "row_count": int(len(scores)),
        "unique_case_count": int(scores["case_id"].nunique(dropna=True)),
        "risk_band_counts": _counts(scores["risk_band"]),
        "min_score": float(case_scores.min()),
        "max_score": float(case_scores.max()),
        "mean_score": float(case_scores.mean()),
        "mean_total_transaction_value": float(values.mean()) if len(values) else 0.0,
    }


def case_risk_score_result_to_dict(result: CaseRiskScoreResult) -> dict[str, object]:
    """Convert a case risk score result into a compact serialisable payload."""

    return {
        "summary": dict(result.summary),
        "metadata": dict(result.metadata),
        "score_count": int(len(result.scores)),
        "component_count": int(len(result.components)),
    }


def summarise_case_evidence_packs(evidence_packs: pd.DataFrame) -> dict[str, object]:
    """Build a serialisable summary for case evidence packs."""

    if evidence_packs.empty:
        return {
            "evidence_pack_count": 0,
            "unique_case_count": 0,
            "cases_missing_alerts": 0,
            "cases_missing_transactions": 0,
            "cases_missing_risk_scores": 0,
        }
    quality = evidence_packs["evidence_quality"]
    return {
        "evidence_pack_count": int(len(evidence_packs)),
        "unique_case_count": int(evidence_packs["case_id"].nunique(dropna=True)),
        "cases_missing_alerts": int(
            quality.apply(lambda item: not item.get("has_alerts", False)).sum()
        ),
        "cases_missing_transactions": int(
            quality.apply(lambda item: not item.get("has_transactions", False)).sum()
        ),
        "cases_missing_risk_scores": int(
            quality.apply(lambda item: not item.get("has_risk_scores", False)).sum()
        ),
    }


def summarise_case_explanations(explanations: pd.DataFrame) -> dict[str, object]:
    """Build a serialisable summary for case explanations."""

    if explanations.empty:
        return {"explanation_count": 0, "unique_case_count": 0, "version_counts": {}}
    return {
        "explanation_count": int(len(explanations)),
        "unique_case_count": int(explanations["case_id"].nunique(dropna=True)),
        "version_counts": _counts(explanations["explanation_version"]),
    }


def case_evidence_build_result_to_dict(result: CaseEvidenceBuildResult) -> dict[str, object]:
    """Convert a case evidence build result into a compact serialisable payload."""

    return {
        "summary": dict(result.summary),
        "metadata": dict(result.metadata),
        "evidence_pack_count": int(len(result.evidence_packs)),
        "explanation_count": int(len(result.explanations)),
    }
