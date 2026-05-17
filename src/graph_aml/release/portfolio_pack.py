"""Portfolio pack builders for release readiness."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from graph_aml.release.config import ReleaseReadinessConfig
from graph_aml.release.demo_evidence import (
    build_command_transcript_template,
    build_dashboard_walkthrough_markdown,
    build_demo_evidence_index,
    build_demo_validation_checklist_markdown,
)
from graph_aml.release.exceptions import DemoEvidenceError


@dataclass(frozen=True)
class ReleasePortfolioPack:
    release_run_id: str
    portfolio_summary_md: str
    architecture_summary_md: str
    dashboard_walkthrough_md: str
    command_transcript_template_md: str
    demo_validation_checklist_md: str
    validation_index: pd.DataFrame
    evidence_index: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def build_portfolio_summary_markdown(
    inputs: dict[str, object],
    config: ReleaseReadinessConfig | None = None,
) -> str:
    """Build concise reviewer-oriented portfolio summary."""

    if not isinstance(inputs, dict):
        raise DemoEvidenceError("inputs must be a mapping")
    resolved = config or ReleaseReadinessConfig()
    return "\n".join(
        [
            "# Portfolio Summary",
            "",
            (
                "The Graph-Based AML Case Triage and Risk Scoring System is a local-first "
                "financial crime analytics project that turns reference transactional data "
                "into alerts, graph features, risk scores, cases, validation artefacts, "
                "governance records, and reviewer-ready dashboard views."
            ),
            "",
            "## Portfolio Value",
            "",
            (
                "The project demonstrates end-to-end AML analytics engineering, model risk "
                "documentation, auditability, governance inventory, and security control "
                f"packaging for `{resolved.release_version}`."
            ),
            "",
        ]
    )


def build_architecture_summary_markdown(
    inputs: dict[str, object],
    config: ReleaseReadinessConfig | None = None,
) -> str:
    """Build architecture summary markdown."""

    if not isinstance(inputs, dict):
        raise DemoEvidenceError("inputs must be a mapping")
    _ = config or ReleaseReadinessConfig()
    return "\n".join(
        [
            "# Architecture Summary",
            "",
            "- PostgreSQL stores raw, staging, mart, AML, and governance records.",
            "- Neo4j supports graph loading and graph analytics for network context.",
            "- AML rules create deterministic alerts from configured typologies.",
            "- Graph analytics and feature persistence enrich account and case context.",
            "- ML scoring combines anomaly detection, supervised outputs, and risk scoring.",
            (
                "- Case triage links alerts, entities, evidence packs, lifecycle actions, "
                "and audit records."
            ),
            (
                "- The Streamlit dashboard presents operations, model metrics, audit, "
                "and validation pages."
            ),
            (
                "- Governance inventory records lineage, artefacts, model inventory, "
                "and validation inventory."
            ),
            (
                "- Security controls classify sensitive fields, sanitise exports, "
                "and validate audit integrity."
            ),
            "",
        ]
    )


def build_known_limitations_markdown(
    inputs: dict[str, object],
    config: ReleaseReadinessConfig | None = None,
) -> str:
    """Build known limitations markdown."""

    if not isinstance(inputs, dict):
        raise DemoEvidenceError("inputs must be a mapping")
    _ = config or ReleaseReadinessConfig()
    return "\n".join(
        [
            "# Known Limitations",
            "",
            "- Uses reference data rather than production bank records.",
            "- Designed for local-first deployment and portfolio review.",
            "- Analyst labels may be sparse in small local demo runs.",
            "- Supervised metrics are optional when model artefacts are unavailable.",
            "- No external identity provider is implemented.",
            "- No production database encryption layer is implemented.",
            "- No suspicious activity report generation is implemented.",
            "",
        ]
    )


def build_next_steps_markdown(
    inputs: dict[str, object],
    config: ReleaseReadinessConfig | None = None,
) -> str:
    """Build safe future extension notes."""

    if not isinstance(inputs, dict):
        raise DemoEvidenceError("inputs must be a mapping")
    _ = config or ReleaseReadinessConfig()
    return "\n".join(
        [
            "# Next Steps",
            "",
            "- Add production identity integration and row-level access controls.",
            "- Add encrypted database storage and managed secret handling.",
            "- Expand analyst label coverage and independent model validation.",
            "- Add case narrative quality review and SAR drafting workflow boundaries.",
            "- Add deployment runbooks and operational service-level monitoring.",
            "",
        ]
    )


def build_release_portfolio_pack(
    inputs: dict[str, object],
    validation_index: pd.DataFrame,
    config: ReleaseReadinessConfig | None = None,
    release_run_id: str | None = None,
) -> ReleasePortfolioPack:
    """Build all portfolio pack markdown content and indexes."""

    if not isinstance(inputs, dict) or not isinstance(validation_index, pd.DataFrame):
        raise DemoEvidenceError("portfolio pack inputs are malformed")
    resolved = config or ReleaseReadinessConfig()
    run_id = release_run_id or ""
    generated_paths = {
        "portfolio_summary": "release_pack/portfolio_summary.md",
        "architecture_summary": "release_pack/architecture_summary.md",
        "dashboard_walkthrough": "release_pack/dashboard_walkthrough.md",
        "command_transcript_template": "release_pack/command_transcript_template.md",
        "demo_validation_checklist": "release_pack/demo_validation_checklist.md",
        "release_readiness_report": "release_readiness_report.md",
        "release_validation_index": "release_validation_index.csv",
        "release_evidence_index": "release_evidence_index.csv",
    }
    evidence = build_demo_evidence_index(generated_paths, run_id)
    summary = {
        "release_run_id": run_id,
        "validation_index_count": int(len(validation_index)),
        "evidence_item_count": int(len(evidence)),
        "section_count": 5,
    }
    return ReleasePortfolioPack(
        release_run_id=run_id,
        portfolio_summary_md=build_portfolio_summary_markdown(inputs, resolved),
        architecture_summary_md=build_architecture_summary_markdown(inputs, resolved),
        dashboard_walkthrough_md=build_dashboard_walkthrough_markdown(resolved),
        command_transcript_template_md=build_command_transcript_template(resolved),
        demo_validation_checklist_md=build_demo_validation_checklist_markdown(inputs, resolved),
        validation_index=validation_index.copy(deep=True),
        evidence_index=evidence,
        summary=summary,
        metadata={
            "release_name": resolved.release_name,
            "release_version": resolved.release_version,
        },
    )
