"""Tests for release demo evidence and portfolio pack builders."""

import pandas as pd
import pytest

from graph_aml.release import (
    DEMO_EVIDENCE_COLUMNS,
    DemoEvidenceError,
    ReleasePortfolioPack,
    build_architecture_summary_markdown,
    build_command_transcript_template,
    build_dashboard_walkthrough_markdown,
    build_demo_evidence_index,
    build_demo_validation_checklist_markdown,
    build_known_limitations_markdown,
    build_portfolio_summary_markdown,
    build_release_portfolio_pack,
)


def test_demo_evidence_markdown_contains_expected_content() -> None:
    transcript = build_command_transcript_template()
    walkthrough = build_dashboard_walkthrough_markdown()
    checklist = build_demo_validation_checklist_markdown({})

    assert "make services-up" in transcript
    for page in ("Overview", "Alert Queue", "Validation Report"):
        assert page in walkthrough
    for item in ("persisted transactions", "security controls"):
        assert item in checklist


def test_portfolio_pack_builders_cover_scope() -> None:
    inputs: dict[str, object] = {}
    assert "financial crime analytics" in build_portfolio_summary_markdown(inputs)
    architecture = build_architecture_summary_markdown(inputs)
    for term in ("PostgreSQL", "Neo4j", "AML rules", "Security controls"):
        assert term in architecture
    limitations = build_known_limitations_markdown(inputs)
    assert "reference data" in limitations
    assert "local-first" in limitations


def test_evidence_index_and_pack() -> None:
    index = build_demo_evidence_index({"portfolio": "release_pack/portfolio_summary.md"}, "run")
    assert tuple(index.columns) == DEMO_EVIDENCE_COLUMNS
    pack = build_release_portfolio_pack({}, pd.DataFrame(), release_run_id="run")
    assert isinstance(pack, ReleasePortfolioPack)
    assert not pack.evidence_index.empty


def test_malformed_inputs_raise() -> None:
    with pytest.raises(DemoEvidenceError):
        build_demo_validation_checklist_markdown("bad")  # type: ignore[arg-type]
