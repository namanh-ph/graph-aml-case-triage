"""Tests for case evidence builders."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CASE_EVIDENCE_PACK_COLUMNS,
    CASE_EXPLANATION_COLUMNS,
    CaseEvidenceBuildError,
    build_account_evidence,
    build_alert_evidence,
    build_case_chronology,
    build_case_evidence_pack_for_case,
    build_case_evidence_packs,
    build_evidence_quality_summary,
    build_graph_evidence,
    build_recommended_review_focus,
    build_risk_driver_evidence,
    build_transaction_evidence,
    build_typology_evidence,
)
from tests.fixtures.case_evidence import evidence_inputs


def test_evidence_section_builders() -> None:
    inputs = evidence_inputs()
    case = inputs["cases"].iloc[0]
    typology = build_typology_evidence(case, inputs["alerts"])
    assert "circular_flow" in typology["typologies"]
    assert "CIRCULAR_FLOW_CHAIN" in typology["reason_codes"]
    alert = build_alert_evidence(case, inputs["alerts"])
    assert alert["alert_count"] == 2
    assert alert["alerts"][0]["alert_id"] == "ALERT_002"
    tx = build_transaction_evidence(case, inputs["alerts"], inputs["transactions"])
    assert tx["transaction_count"] == 2
    assert tx["total_value"] == 2150.0
    account = build_account_evidence(case, inputs["account_risk_scores"], inputs["anomaly_scores"])
    assert account["accounts"][0]["account_id"] == "ACC_001"
    graph = build_graph_evidence(case, inputs["graph_features"])
    assert graph["accounts"][0]["community_id"] == "COMM_001"
    risk = build_risk_driver_evidence(
        case,
        inputs["case_risk_scores"],
        inputs["account_risk_scores"],
        inputs["graph_features"],
        inputs["anomaly_scores"],
        inputs["alerts"],
        inputs["transactions"],
    )
    assert risk["driver_count"] > 0


def test_chronology_focus_quality_and_high_level_build_are_deterministic() -> None:
    inputs = evidence_inputs()
    case = inputs["cases"].iloc[0]
    chronology = build_case_chronology(case, inputs["alerts"], inputs["transactions"])
    assert [event["event_type"] for event in chronology][:2] == ["transaction", "transaction"]
    pack, explanation = build_case_evidence_pack_for_case(case, inputs)
    focus = build_recommended_review_focus(
        pack["typology_evidence"],
        pack["alert_evidence"],
        pack["transaction_evidence"],
        pack["account_evidence"],
        pack["graph_evidence"],
        pack["risk_driver_evidence"],
    )
    assert focus == pack["recommended_review_focus"]
    quality = build_evidence_quality_summary(
        "CASE_001",
        inputs["alerts"],
        inputs["transactions"],
        inputs["account_risk_scores"],
        inputs["graph_features"],
        inputs["case_risk_scores"],
    )
    assert quality["has_alerts"]
    result = build_case_evidence_packs(inputs)
    assert tuple(result.evidence_packs.columns) == CASE_EVIDENCE_PACK_COLUMNS
    assert tuple(result.explanations.columns) == CASE_EXPLANATION_COLUMNS
    assert result.summary["case_count"] == 1
    assert explanation["explanation_text"]


def test_builders_do_not_mutate_inputs_and_malformed_inputs_raise() -> None:
    inputs = evidence_inputs()
    original = {key: value.copy(deep=True) for key, value in inputs.items()}
    build_case_evidence_packs(inputs)
    for key, frame in original.items():
        pd.testing.assert_frame_equal(inputs[key], frame)
    with pytest.raises(CaseEvidenceBuildError):
        build_case_evidence_pack_for_case({"case_id": ""}, inputs)
