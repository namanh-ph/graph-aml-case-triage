"""Deterministic case explanation rendering."""

from __future__ import annotations

from typing import Any, cast

from graph_aml.cases.evidence_config import CaseEvidenceConfig
from graph_aml.cases.exceptions import CaseEvidenceBuildError


def _as_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CaseEvidenceBuildError(f"{label} must be a dictionary")
    return cast(dict[str, object], value)


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list | tuple) else []


def _fmt_number(value: object) -> str:
    try:
        return f"{float(cast(Any, value)):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(cast(Any, value))
    except (TypeError, ValueError):
        return default


def render_case_summary_sentence(evidence_pack: dict[str, object]) -> str:
    """Render a compact deterministic case summary sentence."""

    try:
        summary = _as_dict(evidence_pack.get("case_summary", {}), "case_summary")
        case_id = str(evidence_pack.get("case_id") or summary.get("case_id") or "unknown case")
        severity = str(summary.get("severity") or "unknown severity")
        risk_band = str(summary.get("risk_band") or "unscored")
        alert_count = _to_int(summary.get("alert_count"))
        transaction_count = _to_int(summary.get("evidence_transaction_count"))
        total_value = _fmt_number(summary.get("total_transaction_value") or 0)
        return (
            f"Case {case_id} is a {severity} case with {risk_band} risk, "
            f"{alert_count} linked alerts, {transaction_count} evidence transactions, "
            f"and total evidence value {total_value}."
        )
    except CaseEvidenceBuildError:
        raise
    except Exception as exc:
        raise CaseEvidenceBuildError(f"Failed to render case summary: {exc}") from exc


def render_typology_summary(typology_evidence: dict[str, object]) -> str:
    """Render triggered typology summary text."""

    try:
        typologies = [str(value) for value in _as_list(typology_evidence.get("typologies"))]
        reason_codes = [str(value) for value in _as_list(typology_evidence.get("reason_codes"))]
        if not typologies:
            return "No triggered typologies are available for this case."
        base = f"Triggered typologies: {', '.join(typologies)}."
        if reason_codes:
            base += f" Key reason codes: {', '.join(reason_codes)}."
        return base
    except Exception as exc:
        raise CaseEvidenceBuildError(f"Failed to render typology summary: {exc}") from exc


def render_risk_driver_summary(risk_driver_evidence: dict[str, object]) -> str:
    """Render top risk driver summary text."""

    try:
        drivers = _as_list(risk_driver_evidence.get("risk_drivers"))
        if not drivers:
            return "No elevated deterministic risk drivers were identified."
        labels = [
            str(driver.get("label", driver.get("component", "risk driver")))
            for driver in drivers
            if isinstance(driver, dict)
        ][:5]
        return "Top risk drivers: " + ", ".join(labels) + "."
    except Exception as exc:
        raise CaseEvidenceBuildError(f"Failed to render risk driver summary: {exc}") from exc


def render_transaction_summary(transaction_evidence: dict[str, object]) -> str:
    """Render transaction evidence summary text."""

    try:
        count = _to_int(transaction_evidence.get("transaction_count"))
        total = _fmt_number(transaction_evidence.get("total_value") or 0)
        max_value = _fmt_number(transaction_evidence.get("max_value") or 0)
        if count == 0:
            return "No evidence transactions are available for this case."
        return (
            f"Evidence includes {count} transactions with total value {total} "
            f"and maximum value {max_value}."
        )
    except Exception as exc:
        raise CaseEvidenceBuildError(f"Failed to render transaction summary: {exc}") from exc


def render_graph_summary(graph_evidence: dict[str, object]) -> str:
    """Render graph context summary text."""

    try:
        rows = _as_list(graph_evidence.get("accounts"))
        if not rows:
            return "No graph context is available for this case."
        communities = sorted(
            {
                str(row.get("community_id"))
                for row in rows
                if isinstance(row, dict) and row.get("community_id") not in (None, "")
            }
        )
        high_risk_alerts = sum(
            int(row.get("high_risk_alert_count") or 0) for row in rows if isinstance(row, dict)
        )
        community_text = ", ".join(communities) if communities else "unknown communities"
        return (
            f"Graph context covers {len(rows)} related accounts in {community_text} "
            f"with {high_risk_alerts} high-risk graph alert links."
        )
    except Exception as exc:
        raise CaseEvidenceBuildError(f"Failed to render graph summary: {exc}") from exc


def render_case_explanation_text(
    evidence_pack: dict[str, object],
    config: CaseEvidenceConfig | None = None,
) -> str:
    """Render deterministic explanation text from an evidence pack."""

    resolved = CaseEvidenceConfig() if config is None else config
    try:
        parts: list[str] = []
        if resolved.explanation.include_case_summary:
            parts.append(render_case_summary_sentence(evidence_pack))
        if resolved.explanation.include_typology_summary:
            parts.append(
                render_typology_summary(
                    _as_dict(evidence_pack.get("typology_evidence", {}), "typology_evidence")
                )
            )
        if resolved.explanation.include_risk_driver_summary:
            parts.append(
                render_risk_driver_summary(
                    _as_dict(evidence_pack.get("risk_driver_evidence", {}), "risk_driver_evidence")
                )
            )
        if resolved.explanation.include_transaction_summary:
            parts.append(
                render_transaction_summary(
                    _as_dict(evidence_pack.get("transaction_evidence", {}), "transaction_evidence")
                )
            )
        if resolved.explanation.include_graph_summary:
            parts.append(
                render_graph_summary(
                    _as_dict(evidence_pack.get("graph_evidence", {}), "graph_evidence")
                )
            )
        if resolved.explanation.include_recommended_review_focus:
            focus = [
                str(value) for value in _as_list(evidence_pack.get("recommended_review_focus"))
            ]
            if focus:
                parts.append("Recommended review focus: " + "; ".join(focus) + ".")
        return " ".join(part for part in parts if part).strip() or "No case evidence is available."
    except CaseEvidenceBuildError:
        raise
    except Exception as exc:
        raise CaseEvidenceBuildError(f"Failed to render case explanation: {exc}") from exc


def render_case_explanation_bullets(
    evidence_pack: dict[str, object],
    config: CaseEvidenceConfig | None = None,
) -> list[str]:
    """Render deterministic explanation bullets from an evidence pack."""

    resolved = CaseEvidenceConfig() if config is None else config
    bullets = [
        render_case_summary_sentence(evidence_pack),
        render_typology_summary(
            _as_dict(evidence_pack.get("typology_evidence", {}), "typology_evidence")
        ),
        render_risk_driver_summary(
            _as_dict(evidence_pack.get("risk_driver_evidence", {}), "risk_driver_evidence")
        ),
        render_transaction_summary(
            _as_dict(evidence_pack.get("transaction_evidence", {}), "transaction_evidence")
        ),
        render_graph_summary(_as_dict(evidence_pack.get("graph_evidence", {}), "graph_evidence")),
    ]
    bullets.extend(str(value) for value in _as_list(evidence_pack.get("recommended_review_focus")))
    deduped = list(dict.fromkeys(bullet for bullet in bullets if bullet))
    return deduped[: resolved.limits.max_explanation_bullets]
