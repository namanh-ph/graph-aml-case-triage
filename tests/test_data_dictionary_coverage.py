"""Tests for data dictionary table and required column coverage."""

from graph_aml.documentation import build_data_dictionary


def _tables() -> dict[str, set[str]]:
    dictionary = build_data_dictionary()
    return {
        table.qualified_name: {column.column_name for column in table.columns}
        for table in dictionary.tables
    }


def test_raw_tables_are_covered() -> None:
    tables = _tables()

    assert {
        "raw.customers_raw",
        "raw.accounts_raw",
        "raw.transactions_raw",
        "raw.counterparties_raw",
        "raw.countries_raw",
        "raw.devices_raw",
    }.issubset(tables)


def test_staging_tables_are_covered() -> None:
    tables = _tables()

    assert {
        "staging.countries",
        "staging.customers",
        "staging.accounts",
        "staging.counterparties",
        "staging.devices",
        "staging.transactions",
    }.issubset(tables)


def test_mart_tables_are_covered() -> None:
    assert {
        "mart.features_account_daily",
        "mart.graph_features",
        "mart.account_anomaly_scores",
        "mart.account_risk_scores",
    }.issubset(_tables())


def test_aml_tables_are_covered() -> None:
    assert {
        "aml.alerts",
        "aml.cases",
        "aml.case_alerts",
        "aml.case_entities",
    }.issubset(_tables())


def test_governance_tables_are_covered() -> None:
    assert {
        "governance.audit_events",
        "governance.model_runs",
        "governance.validation_reports",
    }.issubset(_tables())


def test_staging_transactions_includes_expected_transaction_columns() -> None:
    assert {
        "transaction_id",
        "sender_account_id",
        "receiver_account_id",
        "counterparty_id",
        "device_id",
        "transaction_timestamp",
        "amount",
        "currency",
        "transaction_type",
        "channel",
        "origin_country",
        "destination_country",
        "is_cross_border",
        "is_labelled_suspicious",
        "typology_label",
        "source_file",
        "created_at",
    }.issubset(_tables()["staging.transactions"])


def test_mart_features_account_daily_includes_account_feature_columns() -> None:
    assert {
        "feature_id",
        "account_id",
        "feature_date",
        "feature_version",
        "txn_count_1d",
        "txn_count_7d",
        "total_sent_7d",
        "total_received_7d",
        "avg_txn_amount_30d",
        "max_txn_amount_30d",
        "unique_counterparties_7d",
        "in_out_ratio_7d",
        "retained_balance_proxy",
        "below_threshold_count_24h",
        "dormant_days_before_activity",
        "cross_border_ratio_30d",
        "high_risk_country_exposure",
        "counterparty_entropy",
        "created_at",
    }.issubset(_tables()["mart.features_account_daily"])


def test_mart_graph_features_includes_graph_feature_columns() -> None:
    assert {
        "graph_feature_id",
        "account_id",
        "graph_build_version",
        "feature_date",
        "degree_centrality",
        "in_degree",
        "out_degree",
        "pagerank_score",
        "betweenness_centrality",
        "clustering_coefficient",
        "community_id",
        "community_size",
        "cycle_count",
        "shortest_path_to_flagged",
        "shared_device_count",
        "fan_in_count",
        "fan_out_count",
        "created_at",
    }.issubset(_tables()["mart.graph_features"])


def test_mart_account_anomaly_scores_includes_model_score_columns() -> None:
    assert {
        "account_id",
        "score_date",
        "model_name",
        "model_version",
        "model_run_id",
        "feature_date",
        "account_feature_version",
        "graph_feature_version",
        "graph_build_id",
        "anomaly_score",
        "anomaly_score_raw",
        "anomaly_rank",
        "is_anomaly",
        "risk_band",
        "feature_names",
        "model_parameters",
        "preprocessing_metadata",
        "metrics",
        "metadata",
        "scored_at",
        "created_at",
        "updated_at",
    }.issubset(_tables()["mart.account_anomaly_scores"])


def test_mart_account_risk_scores_includes_composite_score_columns() -> None:
    assert {
        "account_id",
        "score_date",
        "score_name",
        "score_version",
        "account_risk_score",
        "risk_band",
        "risk_rank",
        "rule_risk_score",
        "graph_risk_score",
        "anomaly_risk_score",
        "customer_risk_score",
        "jurisdiction_risk_score",
        "component_coverage",
        "weights",
        "metadata",
        "scored_at",
        "created_at",
        "updated_at",
    }.issubset(_tables()["mart.account_risk_scores"])


def test_aml_alerts_includes_reason_code_and_evidence_ids() -> None:
    assert {"reason_code", "evidence_ids"}.issubset(_tables()["aml.alerts"])


def test_aml_cases_includes_case_risk_score_and_status() -> None:
    assert {"case_risk_score", "status"}.issubset(_tables()["aml.cases"])


def test_governance_audit_events_includes_audit_event_fields() -> None:
    assert {"event_type", "component", "action", "details"}.issubset(
        _tables()["governance.audit_events"]
    )


def test_governance_model_runs_includes_parameters_and_metrics() -> None:
    assert {"parameters", "metrics"}.issubset(_tables()["governance.model_runs"])


def test_governance_validation_reports_includes_report_metadata() -> None:
    assert {"report_name", "report_version", "report_path", "report_type"}.issubset(
        _tables()["governance.validation_reports"]
    )
