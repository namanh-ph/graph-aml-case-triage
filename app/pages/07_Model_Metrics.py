"""Model Metrics page for score and run metadata review."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import (  # noqa: E402
    DashboardDataError,
    build_model_metrics_summary,
    build_precision_at_k_placeholder,
    build_top_ranked_scores,
    create_dashboard_engine,
    dataframe_to_csv_bytes,
    dispose_dashboard_engine,
    load_dashboard_config,
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
    read_dashboard_model_runs,
    read_dashboard_monitoring_runs,
    read_dashboard_reason_contributions,
    read_dashboard_score_decomposition,
    read_dashboard_supervised_model_runs,
    read_dashboard_supervised_model_scores,
    read_dashboard_threshold_recommendations,
    read_dashboard_volume_monitoring_metrics,
    render_model_metrics_summary,
    render_model_run_table,
    render_precision_at_k_table,
    render_risk_band_bar_chart,
    render_score_distribution_chart,
    render_top_ranked_score_table,
    safe_download_filename,
)


def _download(label: str, frame, name: str) -> None:
    if not frame.empty:
        st.download_button(
            label,
            dataframe_to_csv_bytes(frame),
            file_name=safe_download_filename(name),
            mime="text/csv",
        )


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Model Metrics",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Model Metrics")
    with st.sidebar:
        anomaly_version = st.text_input("Anomaly model version")
        account_score_version = st.text_input("Account risk score version")
        case_score_version = st.text_input("Case risk score version")
        risk_band = st.selectbox("Risk band", ["", "low", "medium", "high", "critical"])
        limit = st.number_input(
            "Row limit",
            min_value=1,
            max_value=config.max_page_size,
            value=min(config.model_metrics.default_score_limit, config.max_page_size),
        )

    engine = None
    try:
        engine = create_dashboard_engine()
        model_runs = read_dashboard_model_runs(
            engine,
            model_version=anomaly_version or None,
            limit=config.model_metrics.default_model_metric_limit,
        )
        anomaly = read_dashboard_account_anomaly_scores(
            engine,
            model_version=anomaly_version or None,
            risk_band=risk_band or None,
            limit=int(limit),
        )
        account = read_dashboard_account_risk_scores(
            engine,
            score_version=account_score_version or None,
            risk_band=risk_band or None,
            limit=int(limit),
        )
        case = read_dashboard_case_risk_scores(
            engine,
            score_version=case_score_version or None,
            risk_band=risk_band or None,
            limit=int(limit),
        )
        supervised_scores = read_dashboard_supervised_model_scores(engine, limit=int(limit))
        supervised_runs = read_dashboard_supervised_model_runs(
            engine,
            limit=config.model_metrics.default_model_metric_limit,
        )
        comparison_runs = read_dashboard_model_comparison_runs(
            engine,
            limit=config.model_metrics.default_model_metric_limit,
        )
        comparison_run_id = (
            None if comparison_runs.empty else str(comparison_runs["comparison_run_id"].iloc[0])
        )
        comparison_metrics = read_dashboard_model_comparison_metrics(
            engine,
            comparison_run_id=comparison_run_id,
            limit=int(limit),
        )
        threshold_recommendations = read_dashboard_threshold_recommendations(
            engine,
            comparison_run_id=comparison_run_id,
            limit=int(limit),
        )
        champion_rows = read_dashboard_champion_challenger_results(
            engine,
            comparison_run_id=comparison_run_id,
            limit=int(limit),
        )
        monitoring_runs = read_dashboard_monitoring_runs(
            engine,
            limit=config.model_metrics.default_model_metric_limit,
        )
        monitoring_run_id = (
            None if monitoring_runs.empty else str(monitoring_runs["monitoring_run_id"].iloc[0])
        )
        drift_metrics = read_dashboard_drift_metrics(
            engine,
            monitoring_run_id=monitoring_run_id,
            limit=int(limit),
        )
        volume_metrics = read_dashboard_volume_monitoring_metrics(
            engine,
            monitoring_run_id=monitoring_run_id,
            limit=int(limit),
        )
        backtesting_metrics = read_dashboard_backtesting_metrics(
            engine,
            monitoring_run_id=monitoring_run_id,
            limit=int(limit),
        )
        explainability_runs = read_dashboard_explainability_runs(
            engine,
            limit=config.model_metrics.default_model_metric_limit,
        )
        explanation_run_id = (
            None
            if explainability_runs.empty
            else str(explainability_runs["explanation_run_id"].iloc[0])
        )
        global_features = read_dashboard_global_feature_importance(
            engine,
            explanation_run_id=explanation_run_id,
            limit=int(limit),
        )
        score_decomposition = read_dashboard_score_decomposition(
            engine,
            explanation_run_id=explanation_run_id,
            limit=int(limit),
        )
        reason_contributions = read_dashboard_reason_contributions(
            engine,
            explanation_run_id=explanation_run_id,
            limit=int(limit),
        )
        model_cards = read_dashboard_model_cards(
            engine,
            explanation_run_id=explanation_run_id,
            limit=config.model_metrics.default_model_metric_limit,
        )
        bundle = {
            "model_runs": model_runs,
            "account_anomaly_scores": anomaly,
            "account_risk_scores": account,
            "case_risk_scores": case,
            "supervised_model_scores": supervised_scores,
            "supervised_model_runs": supervised_runs,
            "model_comparison_runs": comparison_runs,
            "model_comparison_metrics": comparison_metrics,
            "threshold_recommendations": threshold_recommendations,
            "champion_challenger_results": champion_rows,
            "monitoring_runs": monitoring_runs,
            "drift_metrics": drift_metrics,
            "volume_monitoring_metrics": volume_metrics,
            "backtesting_metrics": backtesting_metrics,
            "explainability_runs": explainability_runs,
            "global_feature_importance": global_features,
            "score_decomposition": score_decomposition,
            "reason_contributions": reason_contributions,
            "model_cards": model_cards,
        }
        summary = build_model_metrics_summary(bundle, config)
        render_model_metrics_summary(summary)
        render_model_run_table(model_runs)
        render_score_distribution_chart(anomaly, "anomaly_score", "Anomaly Score Distribution")
        render_risk_band_bar_chart(summary["anomaly_score_summary"], "Anomaly Risk Bands")
        render_score_distribution_chart(account, "account_risk_score", "Account Risk Distribution")
        render_risk_band_bar_chart(summary["account_risk_summary"], "Account Risk Bands")
        render_score_distribution_chart(case, "case_risk_score", "Case Risk Distribution")
        render_risk_band_bar_chart(summary["case_risk_summary"], "Case Risk Bands")
        render_top_ranked_score_table(
            build_top_ranked_scores(anomaly, "anomaly_rank", "anomaly_score"),
            "Top Anomaly Scores",
        )
        render_top_ranked_score_table(
            build_top_ranked_scores(account, "risk_rank", "account_risk_score"),
            "Top Account Risk Scores",
        )
        render_top_ranked_score_table(
            build_top_ranked_scores(case, "risk_rank", "case_risk_score"),
            "Top Case Risk Scores",
        )
        render_model_run_table(supervised_runs)
        render_score_distribution_chart(
            supervised_scores,
            "supervised_score",
            "Supervised AML Score Distribution",
        )
        render_top_ranked_score_table(
            build_top_ranked_scores(supervised_scores, "risk_rank", "supervised_score"),
            "Top Supervised AML Scores",
        )
        st.subheader("Model Comparison")
        if comparison_runs.empty:
            st.info("No persisted model comparison runs are available yet.")
        else:
            st.dataframe(comparison_runs, use_container_width=True)
            st.caption("Champion-challenger results")
            st.dataframe(champion_rows, use_container_width=True)
            st.caption("Threshold recommendations")
            st.dataframe(threshold_recommendations, use_container_width=True)
            with st.expander("Candidate metrics"):
                st.dataframe(comparison_metrics, use_container_width=True)
        st.subheader("Monitoring")
        if monitoring_runs.empty:
            st.info("No persisted monitoring runs are available yet.")
        else:
            latest = monitoring_runs.iloc[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Latest run", str(latest.get("monitoring_run_id", ""))[:18])
            col2.metric("High drift", int(latest.get("high_drift_count", 0) or 0))
            col3.metric("Critical volume", int(latest.get("critical_count", 0) or 0))
            st.dataframe(monitoring_runs, use_container_width=True)
            with st.expander("Drift metrics"):
                st.dataframe(drift_metrics, use_container_width=True)
            with st.expander("Volume metrics"):
                st.dataframe(volume_metrics, use_container_width=True)
            with st.expander("Backtesting metrics"):
                st.dataframe(backtesting_metrics, use_container_width=True)
        st.subheader("Explainability")
        if explainability_runs.empty:
            st.info("No persisted explainability runs are available yet.")
        else:
            latest_explanation = explainability_runs.iloc[0]
            col1, col2, col3 = st.columns(3)
            col1.metric(
                "Latest run",
                str(latest_explanation.get("explanation_run_id", ""))[:18],
            )
            col2.metric("Global features", int(len(global_features)))
            col3.metric("Model cards", int(len(model_cards)))
            st.dataframe(explainability_runs, use_container_width=True)
            with st.expander("Top global features"):
                st.dataframe(global_features, use_container_width=True)
            with st.expander("Score decomposition"):
                st.dataframe(score_decomposition, use_container_width=True)
            with st.expander("Reason contributions"):
                st.dataframe(reason_contributions, use_container_width=True)
        render_precision_at_k_table(
            build_precision_at_k_placeholder(
                case,
                config.model_metrics.default_top_k_values,
                rank_column="risk_rank",
            )
        )
        if config.enable_download_buttons:
            _download("Download Model Runs", model_runs, "model_runs")
            _download("Download Anomaly Scores", anomaly, "account_anomaly_scores")
            _download("Download Account Risk Scores", account, "account_risk_scores")
            _download("Download Case Risk Scores", case, "case_risk_scores")
            _download("Download Supervised Scores", supervised_scores, "supervised_scores")
            _download("Download Comparison Metrics", comparison_metrics, "model_comparison_metrics")
            _download("Download Drift Metrics", drift_metrics, "drift_metrics")
            _download("Download Backtesting Metrics", backtesting_metrics, "backtesting_metrics")
            _download(
                "Download Global Feature Importance",
                global_features,
                "global_feature_importance",
            )
            _download(
                "Download Score Decomposition",
                score_decomposition,
                "score_decomposition",
            )
            _download(
                "Download Reason Contributions",
                reason_contributions,
                "reason_contributions",
            )
            _download(
                "Download Threshold Recommendations",
                threshold_recommendations,
                "threshold_recommendations",
            )
    except DashboardDataError as exc:
        st.info(f"Model metric data is not available yet: {exc}")
    finally:
        dispose_dashboard_engine(engine)


main()
