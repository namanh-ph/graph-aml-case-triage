"""Tests for model, audit, and validation report render components."""

import pandas as pd
import pytest

from graph_aml.dashboard.audit_components import (
    render_audit_event_detail,
    render_audit_event_table,
    render_audit_summary,
)
from graph_aml.dashboard.exceptions import DashboardRenderError
from graph_aml.dashboard.model_metrics_components import (
    render_model_metrics_summary,
    render_model_run_table,
    render_precision_at_k_table,
    render_risk_band_bar_chart,
    render_score_distribution_chart,
    render_top_ranked_score_table,
)
from graph_aml.dashboard.validation_report_components import (
    render_validation_file_preview,
    render_validation_file_table,
    render_validation_report_empty_state,
    render_validation_report_index,
)


def test_model_metric_components_are_callable_with_empty_inputs() -> None:
    empty = pd.DataFrame()

    render_score_distribution_chart(empty, "score", "Scores")
    render_risk_band_bar_chart({}, "Bands")
    render_model_run_table(empty)
    render_precision_at_k_table(empty)
    render_top_ranked_score_table(empty, "Top")
    render_model_metrics_summary({"model_run_count": 0})


def test_audit_components_are_callable_with_empty_inputs() -> None:
    render_audit_summary({"event_count": 0})
    render_audit_event_table(pd.DataFrame())
    render_audit_event_detail({})


def test_validation_report_components_are_callable_with_empty_inputs() -> None:
    render_validation_report_index({"file_count": 0, "files": []})
    render_validation_file_table(pd.DataFrame())
    render_validation_file_preview({})
    render_validation_report_empty_state("reports/model_validation")


def test_malformed_component_inputs_raise() -> None:
    with pytest.raises(DashboardRenderError):
        render_score_distribution_chart({"bad": "input"}, "score", "Scores")  # type: ignore[arg-type]
