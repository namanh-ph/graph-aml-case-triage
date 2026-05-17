"""Shared in-memory fixtures for case risk tests."""

import pandas as pd

from graph_aml.cases import (
    CASE_RISK_COMPONENT_COLUMNS,
    CASE_RISK_SCORE_COLUMNS,
    CaseRiskScoreResult,
)


def case_risk_components() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["C1", 90, 80, 70, 60, 50, 40, 90, 80, 80, 70, 70, 60, 60, 50, 2, 2, 1, 2, 150, 1.0],
            ["C2", 20, 30, 10, 40, 25, 10, 20, 20, 30, 30, 10, 10, 40, 40, 1, 1, 1, 1, 20, 1.0],
        ],
        columns=CASE_RISK_COMPONENT_COLUMNS,
    )


def case_risk_score_result() -> CaseRiskScoreResult:
    scores = pd.DataFrame(
        [
            [
                "C1",
                "2026-01-01",
                "composite_case_risk",
                "composite_case_risk_v1",
                80.0,
                "high",
                1,
                90.0,
                80.0,
                70.0,
                60.0,
                50.0,
                40.0,
                1.0,
                2,
                2,
                1,
                2,
                150.0,
                90.0,
                80.0,
                60.0,
            ]
        ],
        columns=CASE_RISK_SCORE_COLUMNS,
    )
    return CaseRiskScoreResult(scores=scores, components=pd.DataFrame(), metadata={"weights": {}})
