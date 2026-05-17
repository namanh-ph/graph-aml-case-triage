"""Tests for dashboard model metric readers and helpers."""

import pandas as pd
import pytest
from sqlalchemy.sql.elements import TextClause

from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.model_metrics import (
    build_precision_at_k_placeholder,
    build_score_distribution_summary,
    build_top_ranked_scores,
)
from graph_aml.dashboard.model_metrics_data import (
    read_dashboard_account_anomaly_scores,
    read_dashboard_account_risk_scores,
    read_dashboard_backtesting_metrics,
    read_dashboard_case_risk_scores,
    read_dashboard_champion_challenger_results,
    read_dashboard_drift_metrics,
    read_dashboard_explainability_runs,
    read_dashboard_global_feature_importance,
    read_dashboard_model_cards,
    read_dashboard_model_comparison_metrics,
    read_dashboard_model_comparison_runs,
    read_dashboard_model_metric_bundle,
    read_dashboard_model_runs,
    read_dashboard_monitoring_runs,
    read_dashboard_reason_contributions,
    read_dashboard_score_decomposition,
    read_dashboard_supervised_model_runs,
    read_dashboard_supervised_model_scores,
    read_dashboard_threshold_recommendations,
    read_dashboard_volume_monitoring_metrics,
)


def test_model_metric_readers_query_expected_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read(
        sql: TextClause,
        engine: object,
        params: dict[str, object] | None = None,
    ) -> pd.DataFrame:
        calls.append((str(sql), params))
        text = str(sql)
        if "governance.model_runs" in text:
            return pd.DataFrame({"model_run_id": ["MR1"]})
        if "mart.account_anomaly_scores" in text:
            return pd.DataFrame({"account_id": ["A1"], "anomaly_score": [90.0]})
        if "mart.account_risk_scores" in text:
            return pd.DataFrame({"account_id": ["A1"], "account_risk_score": [91.0]})
        if "aml.case_risk_scores" in text:
            return pd.DataFrame({"case_id": ["C1"], "case_risk_score": [92.0]})
        if "mart.supervised_model_scores" in text:
            return pd.DataFrame({"entity_id": ["C1"], "supervised_score": [0.8]})
        if "governance.supervised_model_runs" in text:
            return pd.DataFrame({"run_id": ["SR1"]})
        if "governance.model_comparison_runs" in text:
            return pd.DataFrame({"comparison_run_id": ["CR1"]})
        if "governance.model_comparison_metrics" in text:
            return pd.DataFrame({"candidate_name": ["case_risk_score"]})
        if "governance.threshold_recommendations" in text:
            return pd.DataFrame({"candidate_name": ["case_risk_score"]})
        if "governance.champion_challenger_results" in text:
            return pd.DataFrame({"candidate_name": ["case_risk_score"], "is_champion": [True]})
        if "governance.monitoring_runs" in text:
            return pd.DataFrame({"monitoring_run_id": ["MRUN1"]})
        if "governance.drift_metrics" in text:
            return pd.DataFrame({"feature_name": ["score"], "drift_band": ["high"]})
        if "governance.volume_monitoring_metrics" in text:
            return pd.DataFrame({"volume_type": ["alerts"], "severity_band": ["critical"]})
        if "governance.backtesting_metrics" in text:
            return pd.DataFrame({"metric_name": ["case_count"]})
        if "governance.explainability_runs" in text:
            return pd.DataFrame({"explanation_run_id": ["E1"]})
        if "governance.global_feature_importance" in text:
            return pd.DataFrame({"feature_name": ["case_risk_score"]})
        if "governance.score_decomposition" in text:
            return pd.DataFrame({"component_name": ["rule_typology_score"]})
        if "governance.reason_contributions" in text:
            return pd.DataFrame({"reason_name": ["Structuring"]})
        if "governance.model_cards" in text:
            return pd.DataFrame({"model_card_markdown": ["# Card"]})
        return pd.DataFrame()

    monkeypatch.setattr("graph_aml.dashboard.model_metrics_data.pd.read_sql_query", fake_read)
    engine = object()

    read_dashboard_model_runs(engine, model_name="iforest", limit=5)  # type: ignore[arg-type]
    read_dashboard_account_anomaly_scores(engine, risk_band="high", limit=5)  # type: ignore[arg-type]
    read_dashboard_account_risk_scores(engine, score_version="v1", limit=5)  # type: ignore[arg-type]
    read_dashboard_case_risk_scores(engine, score_version="v1", limit=5)  # type: ignore[arg-type]
    read_dashboard_supervised_model_scores(engine, model_version="v1", limit=5)  # type: ignore[arg-type]
    read_dashboard_supervised_model_runs(engine, model_version="v1", limit=5)  # type: ignore[arg-type]
    read_dashboard_model_comparison_runs(engine, comparison_version="v1", limit=5)  # type: ignore[arg-type]
    read_dashboard_model_comparison_metrics(engine, comparison_run_id="CR1", limit=5)  # type: ignore[arg-type]
    read_dashboard_threshold_recommendations(engine, comparison_run_id="CR1", limit=5)  # type: ignore[arg-type]
    read_dashboard_champion_challenger_results(engine, comparison_run_id="CR1", limit=5)  # type: ignore[arg-type]
    read_dashboard_monitoring_runs(engine, monitoring_version="v1", limit=5)  # type: ignore[arg-type]
    read_dashboard_drift_metrics(engine, monitoring_run_id="MRUN1", limit=5)  # type: ignore[arg-type]
    read_dashboard_volume_monitoring_metrics(engine, monitoring_run_id="MRUN1", limit=5)  # type: ignore[arg-type]
    read_dashboard_backtesting_metrics(engine, monitoring_run_id="MRUN1", limit=5)  # type: ignore[arg-type]
    read_dashboard_explainability_runs(engine, explanation_version="v1", limit=5)  # type: ignore[arg-type]
    read_dashboard_global_feature_importance(engine, explanation_run_id="E1", limit=5)  # type: ignore[arg-type]
    read_dashboard_score_decomposition(engine, explanation_run_id="E1", limit=5)  # type: ignore[arg-type]
    read_dashboard_reason_contributions(engine, explanation_run_id="E1", limit=5)  # type: ignore[arg-type]
    read_dashboard_model_cards(engine, explanation_run_id="E1", limit=5)  # type: ignore[arg-type]
    bundle = read_dashboard_model_metric_bundle(engine, limit=5)  # type: ignore[arg-type]

    all_sql = "\n".join(sql for sql, _ in calls)
    assert "governance.model_runs" in all_sql
    assert "mart.account_anomaly_scores" in all_sql
    assert "mart.account_risk_scores" in all_sql
    assert "aml.case_risk_scores" in all_sql
    assert "mart.supervised_model_scores" in all_sql
    assert "governance.supervised_model_runs" in all_sql
    assert "governance.model_comparison_runs" in all_sql
    assert "governance.model_comparison_metrics" in all_sql
    assert "governance.threshold_recommendations" in all_sql
    assert "governance.champion_challenger_results" in all_sql
    assert "governance.monitoring_runs" in all_sql
    assert "governance.drift_metrics" in all_sql
    assert "governance.volume_monitoring_metrics" in all_sql
    assert "governance.backtesting_metrics" in all_sql
    assert "governance.explainability_runs" in all_sql
    assert "governance.global_feature_importance" in all_sql
    assert "governance.score_decomposition" in all_sql
    assert "governance.reason_contributions" in all_sql
    assert "governance.model_cards" in all_sql
    assert any(params and params.get("limit") == 5 for _, params in calls)
    assert set(bundle) == {
        "model_runs",
        "account_anomaly_scores",
        "account_risk_scores",
        "case_risk_scores",
        "supervised_model_scores",
        "supervised_model_runs",
        "model_comparison_runs",
        "model_comparison_metrics",
        "threshold_recommendations",
        "champion_challenger_results",
        "monitoring_runs",
        "drift_metrics",
        "volume_monitoring_metrics",
        "backtesting_metrics",
        "explainability_runs",
        "global_feature_importance",
        "score_decomposition",
        "reason_contributions",
        "model_cards",
    }


def test_model_metric_helpers_summarise_and_do_not_mutate() -> None:
    scores = pd.DataFrame(
        {"risk_rank": [2, 1], "score": [80.0, 90.0], "risk_band": ["high", "critical"]}
    )
    original = scores.copy(deep=True)

    summary = build_score_distribution_summary(scores, "score")
    top = build_top_ranked_scores(scores, "risk_rank", "score", top_k=1)
    precision = build_precision_at_k_placeholder(scores, (10,), rank_column="risk_rank")

    assert summary["row_count"] == 2
    assert summary["max"] == 90.0
    assert top.iloc[0]["risk_rank"] == 1
    assert precision.iloc[0]["status"] == "label_unavailable"
    pd.testing.assert_frame_equal(scores, original)


def test_model_metric_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.dashboard.model_metrics_data.pd.read_sql_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(DashboardDataError):
        read_dashboard_model_runs(object())  # type: ignore[arg-type]
