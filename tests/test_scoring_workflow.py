"""Tests for end-to-end scoring workflow."""

import pandas as pd

from graph_aml.scoring import (
    AccountRiskScorePersistenceResult,
    AccountRiskScoreResult,
    compute_and_persist_account_risk_scores,
)


class FakeEngine:
    pass


def test_compute_and_persist_workflow(monkeypatch) -> None:
    calls: list[object] = []

    inputs = {
        "accounts": pd.DataFrame({"account_id": ["A1"], "customer_risk_rating": ["high"]}),
        "alerts": pd.DataFrame(),
        "graph_features": pd.DataFrame(),
        "anomaly_scores": pd.DataFrame(),
    }

    def fake_read(engine, config, limit=None):
        calls.append(limit)
        return inputs

    monkeypatch.setattr("graph_aml.scoring.inputs.read_scoring_feature_inputs", fake_read)
    monkeypatch.setattr(
        "graph_aml.scoring.persistence.persist_account_risk_scores",
        lambda *a, **k: AccountRiskScorePersistenceResult(rows_persisted=1, persisted=True),
    )
    scoring_result, persistence_result = compute_and_persist_account_risk_scores(
        FakeEngine(),  # type: ignore[arg-type]
        limit=7,
    )
    assert isinstance(scoring_result, AccountRiskScoreResult)
    assert persistence_result.persisted
    assert calls == [7]
