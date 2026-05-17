"""Tests for deterministic case explanations."""

import pytest

from graph_aml.cases import (
    CaseEvidenceBuildError,
    render_case_explanation_bullets,
    render_case_explanation_text,
    render_case_summary_sentence,
    render_graph_summary,
    render_risk_driver_summary,
    render_transaction_summary,
    render_typology_summary,
)
from tests.fixtures.case_evidence import evidence_result


def evidence_pack() -> dict[str, object]:
    return evidence_result().evidence_packs.iloc[0].to_dict()


def test_explanation_sections_include_expected_context() -> None:
    pack = evidence_pack()
    assert "CASE_001" in render_case_summary_sentence(pack)
    assert "critical" in render_case_summary_sentence(pack)
    assert "circular_flow" in render_typology_summary(pack["typology_evidence"])
    assert "risk drivers" in render_risk_driver_summary(pack["risk_driver_evidence"]).lower()
    assert "2 transactions" in render_transaction_summary(pack["transaction_evidence"])
    assert "COMM_001" in render_graph_summary(pack["graph_evidence"])


def test_explanation_text_and_bullets_are_deterministic() -> None:
    pack = evidence_pack()
    assert render_case_explanation_text(pack) == render_case_explanation_text(pack)
    assert render_case_explanation_bullets(pack) == render_case_explanation_bullets(pack)
    assert render_case_explanation_bullets(pack)


def test_sparse_evidence_and_malformed_payloads() -> None:
    sparse = {
        "case_id": "CASE_EMPTY",
        "case_summary": {"case_id": "CASE_EMPTY"},
        "typology_evidence": {},
        "risk_driver_evidence": {},
        "transaction_evidence": {},
        "graph_evidence": {},
        "recommended_review_focus": [],
    }
    assert render_case_explanation_text(sparse)
    with pytest.raises(CaseEvidenceBuildError):
        render_case_summary_sentence({"case_summary": []})
