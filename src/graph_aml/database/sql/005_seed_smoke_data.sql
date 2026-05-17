-- Deterministic smoke seed data for local PostgreSQL checks.
-- This script is idempotent and intentionally tiny; it is not the synthetic AML generator.

INSERT INTO staging.countries (
    country_code,
    country_name,
    region,
    is_high_risk,
    risk_score
) VALUES
    ('SMOKE_US', 'United States', 'North America', FALSE, 15.00),
    ('SMOKE_HR', 'High Risk Jurisdiction', 'Synthetic Region', TRUE, 85.00)
ON CONFLICT (country_code) DO UPDATE SET
    country_name = EXCLUDED.country_name,
    region = EXCLUDED.region,
    is_high_risk = EXCLUDED.is_high_risk,
    risk_score = EXCLUDED.risk_score,
    updated_at = NOW();

INSERT INTO staging.customers (
    customer_id,
    customer_type,
    customer_segment,
    jurisdiction,
    occupation,
    industry_code,
    customer_risk_rating,
    customer_risk_score,
    onboarded_at
) VALUES
    (
        'CUST_SMOKE_001',
        'individual',
        'retail',
        'SMOKE_US',
        'Consultant',
        NULL,
        'medium',
        45.00,
        '2024-01-15T09:00:00Z'
    ),
    (
        'CUST_SMOKE_002',
        'business',
        'sme',
        'SMOKE_HR',
        NULL,
        '5416',
        'high',
        82.00,
        '2024-02-01T10:00:00Z'
    ),
    (
        'CUST_SMOKE_003',
        'individual',
        'retail',
        'SMOKE_US',
        'Trader',
        NULL,
        'low',
        22.00,
        '2024-03-20T11:00:00Z'
    )
ON CONFLICT (customer_id) DO UPDATE SET
    customer_type = EXCLUDED.customer_type,
    customer_segment = EXCLUDED.customer_segment,
    jurisdiction = EXCLUDED.jurisdiction,
    occupation = EXCLUDED.occupation,
    industry_code = EXCLUDED.industry_code,
    customer_risk_rating = EXCLUDED.customer_risk_rating,
    customer_risk_score = EXCLUDED.customer_risk_score,
    onboarded_at = EXCLUDED.onboarded_at,
    updated_at = NOW();

INSERT INTO staging.accounts (
    account_id,
    customer_id,
    account_type,
    account_status,
    currency,
    opened_at,
    home_country
) VALUES
    ('ACC_SMOKE_001', 'CUST_SMOKE_001', 'checking', 'active', 'USD', '2024-01-16T09:00:00Z', 'SMOKE_US'),
    ('ACC_SMOKE_002', 'CUST_SMOKE_002', 'business', 'active', 'USD', '2024-02-02T10:00:00Z', 'SMOKE_HR'),
    ('ACC_SMOKE_003', 'CUST_SMOKE_003', 'checking', 'active', 'USD', '2024-03-21T11:00:00Z', 'SMOKE_US'),
    ('ACC_SMOKE_004', 'CUST_SMOKE_002', 'settlement', 'active', 'USD', '2024-02-03T10:00:00Z', 'SMOKE_HR')
ON CONFLICT (account_id) DO UPDATE SET
    customer_id = EXCLUDED.customer_id,
    account_type = EXCLUDED.account_type,
    account_status = EXCLUDED.account_status,
    currency = EXCLUDED.currency,
    opened_at = EXCLUDED.opened_at,
    home_country = EXCLUDED.home_country,
    updated_at = NOW();

INSERT INTO staging.counterparties (
    counterparty_id,
    counterparty_type,
    counterparty_name,
    country_code,
    institution_name,
    external_account_ref,
    risk_score
) VALUES
    ('CP_SMOKE_001', 'merchant', 'Smoke Electronics', 'SMOKE_US', 'Smoke Bank', 'EXT-SMOKE-001', 20.00),
    ('CP_SMOKE_002', 'beneficiary', 'High Risk Importer', 'SMOKE_HR', 'Offshore Smoke Bank', 'EXT-SMOKE-002', 88.00),
    ('CP_SMOKE_003', 'exchange', 'Smoke FX Desk', 'SMOKE_HR', 'Smoke Exchange', 'EXT-SMOKE-003', 75.00)
ON CONFLICT (counterparty_id) DO UPDATE SET
    counterparty_type = EXCLUDED.counterparty_type,
    counterparty_name = EXCLUDED.counterparty_name,
    country_code = EXCLUDED.country_code,
    institution_name = EXCLUDED.institution_name,
    external_account_ref = EXCLUDED.external_account_ref,
    risk_score = EXCLUDED.risk_score,
    updated_at = NOW();

INSERT INTO staging.devices (
    device_id,
    device_type,
    ip_address,
    ip_cluster,
    phone_hash,
    browser_fingerprint
) VALUES
    ('DEV_SMOKE_001', 'mobile', '192.0.2.10', '192.0.2.0/24', 'PHONE_HASH_SMOKE_001', 'BROWSER_SMOKE_001'),
    ('DEV_SMOKE_002', 'desktop', '198.51.100.25', '198.51.100.0/24', 'PHONE_HASH_SMOKE_002', 'BROWSER_SMOKE_002')
ON CONFLICT (device_id) DO UPDATE SET
    device_type = EXCLUDED.device_type,
    ip_address = EXCLUDED.ip_address,
    ip_cluster = EXCLUDED.ip_cluster,
    phone_hash = EXCLUDED.phone_hash,
    browser_fingerprint = EXCLUDED.browser_fingerprint,
    updated_at = NOW();

INSERT INTO staging.transactions (
    transaction_id,
    sender_account_id,
    receiver_account_id,
    counterparty_id,
    device_id,
    transaction_timestamp,
    amount,
    currency,
    transaction_type,
    channel,
    origin_country,
    destination_country,
    is_cross_border,
    is_labelled_suspicious,
    typology_label,
    source_file
) VALUES
    ('TXN_SMOKE_001', 'ACC_SMOKE_001', 'ACC_SMOKE_002', NULL, 'DEV_SMOKE_001', '2025-01-01T09:00:00Z', 9500.00, 'USD', 'transfer', 'online', 'SMOKE_US', 'SMOKE_HR', TRUE, TRUE, 'Structuring', 'smoke_seed'),
    ('TXN_SMOKE_002', 'ACC_SMOKE_001', 'ACC_SMOKE_002', NULL, 'DEV_SMOKE_001', '2025-01-01T10:00:00Z', 9700.00, 'USD', 'transfer', 'online', 'SMOKE_US', 'SMOKE_HR', TRUE, TRUE, 'Structuring', 'smoke_seed'),
    ('TXN_SMOKE_003', 'ACC_SMOKE_001', NULL, 'CP_SMOKE_001', 'DEV_SMOKE_001', '2025-01-01T11:00:00Z', 9800.00, 'USD', 'payment', 'online', 'SMOKE_US', 'SMOKE_US', FALSE, TRUE, 'Structuring', 'smoke_seed'),
    ('TXN_SMOKE_004', 'ACC_SMOKE_001', NULL, 'CP_SMOKE_002', 'DEV_SMOKE_001', '2025-01-01T12:00:00Z', 9900.00, 'USD', 'payment', 'online', 'SMOKE_US', 'SMOKE_HR', TRUE, TRUE, 'Structuring', 'smoke_seed'),
    ('TXN_SMOKE_005', 'ACC_SMOKE_002', NULL, 'CP_SMOKE_001', 'DEV_SMOKE_002', '2025-01-02T09:30:00Z', 12500.00, 'USD', 'payment', 'branch', 'SMOKE_HR', 'SMOKE_US', TRUE, TRUE, 'Fan-out', 'smoke_seed'),
    ('TXN_SMOKE_006', 'ACC_SMOKE_002', NULL, 'CP_SMOKE_002', 'DEV_SMOKE_002', '2025-01-02T10:30:00Z', 8000.00, 'USD', 'payment', 'online', 'SMOKE_HR', 'SMOKE_HR', FALSE, TRUE, 'Fan-out', 'smoke_seed'),
    ('TXN_SMOKE_007', 'ACC_SMOKE_002', NULL, 'CP_SMOKE_003', 'DEV_SMOKE_002', '2025-01-02T11:30:00Z', 7600.00, 'USD', 'payment', 'online', 'SMOKE_HR', 'SMOKE_HR', FALSE, TRUE, 'Fan-out', 'smoke_seed'),
    ('TXN_SMOKE_008', 'ACC_SMOKE_003', 'ACC_SMOKE_004', NULL, 'DEV_SMOKE_001', '2025-01-03T14:00:00Z', 2500.00, 'USD', 'transfer', 'mobile', 'SMOKE_US', 'SMOKE_HR', TRUE, FALSE, NULL, 'smoke_seed')
ON CONFLICT (transaction_id) DO UPDATE SET
    sender_account_id = EXCLUDED.sender_account_id,
    receiver_account_id = EXCLUDED.receiver_account_id,
    counterparty_id = EXCLUDED.counterparty_id,
    device_id = EXCLUDED.device_id,
    transaction_timestamp = EXCLUDED.transaction_timestamp,
    amount = EXCLUDED.amount,
    currency = EXCLUDED.currency,
    transaction_type = EXCLUDED.transaction_type,
    channel = EXCLUDED.channel,
    origin_country = EXCLUDED.origin_country,
    destination_country = EXCLUDED.destination_country,
    is_cross_border = EXCLUDED.is_cross_border,
    is_labelled_suspicious = EXCLUDED.is_labelled_suspicious,
    typology_label = EXCLUDED.typology_label,
    source_file = EXCLUDED.source_file;

INSERT INTO mart.features_account_daily (
    account_id,
    feature_date,
    feature_version,
    txn_count_1d,
    txn_count_7d,
    total_sent_7d,
    total_received_7d,
    avg_txn_amount_30d,
    max_txn_amount_30d,
    unique_counterparties_7d,
    in_out_ratio_7d,
    retained_balance_proxy,
    below_threshold_count_24h,
    dormant_days_before_activity,
    cross_border_ratio_30d,
    high_risk_country_exposure,
    counterparty_entropy
) VALUES
    ('ACC_SMOKE_001', '2025-01-01', 'smoke_v1', 4, 4, 38900.00, 0.00, 9725.00, 9900.00, 3, NULL, -38900.00, 4, 0, 0.75, 0.60, 1.10),
    ('ACC_SMOKE_002', '2025-01-02', 'smoke_v1', 3, 5, 28100.00, 19200.00, 9500.00, 12500.00, 3, 1.463542, -8900.00, 0, 0, 0.40, 0.90, 1.09)
ON CONFLICT ON CONSTRAINT uq_features_account_daily_version DO UPDATE SET
    txn_count_1d = EXCLUDED.txn_count_1d,
    txn_count_7d = EXCLUDED.txn_count_7d,
    total_sent_7d = EXCLUDED.total_sent_7d,
    total_received_7d = EXCLUDED.total_received_7d,
    avg_txn_amount_30d = EXCLUDED.avg_txn_amount_30d,
    max_txn_amount_30d = EXCLUDED.max_txn_amount_30d,
    unique_counterparties_7d = EXCLUDED.unique_counterparties_7d,
    in_out_ratio_7d = EXCLUDED.in_out_ratio_7d,
    retained_balance_proxy = EXCLUDED.retained_balance_proxy,
    below_threshold_count_24h = EXCLUDED.below_threshold_count_24h,
    dormant_days_before_activity = EXCLUDED.dormant_days_before_activity,
    cross_border_ratio_30d = EXCLUDED.cross_border_ratio_30d,
    high_risk_country_exposure = EXCLUDED.high_risk_country_exposure,
    counterparty_entropy = EXCLUDED.counterparty_entropy;

INSERT INTO mart.graph_features (
    account_id,
    graph_build_version,
    feature_date,
    degree_centrality,
    in_degree,
    out_degree,
    pagerank_score,
    betweenness_centrality,
    clustering_coefficient,
    community_id,
    community_size,
    cycle_count,
    shortest_path_to_flagged,
    shared_device_count,
    fan_in_count,
    fan_out_count
) VALUES
    ('ACC_SMOKE_001', 'smoke_graph_v1', '2025-01-01', 0.4200000000, 0, 4, 0.1200000000, 0.3100000000, 0.2500000000, 'COMM_SMOKE_001', 4, 0, 1, 1, 0, 3),
    ('ACC_SMOKE_002', 'smoke_graph_v1', '2025-01-02', 0.5200000000, 2, 3, 0.2200000000, 0.4300000000, 0.1800000000, 'COMM_SMOKE_001', 4, 0, 0, 1, 2, 3)
ON CONFLICT ON CONSTRAINT uq_graph_features_version DO UPDATE SET
    degree_centrality = EXCLUDED.degree_centrality,
    in_degree = EXCLUDED.in_degree,
    out_degree = EXCLUDED.out_degree,
    pagerank_score = EXCLUDED.pagerank_score,
    betweenness_centrality = EXCLUDED.betweenness_centrality,
    clustering_coefficient = EXCLUDED.clustering_coefficient,
    community_id = EXCLUDED.community_id,
    community_size = EXCLUDED.community_size,
    cycle_count = EXCLUDED.cycle_count,
    shortest_path_to_flagged = EXCLUDED.shortest_path_to_flagged,
    shared_device_count = EXCLUDED.shared_device_count,
    fan_in_count = EXCLUDED.fan_in_count,
    fan_out_count = EXCLUDED.fan_out_count;

INSERT INTO governance.model_runs (
    model_run_id,
    experiment_name,
    model_name,
    model_version,
    model_type,
    feature_version,
    training_start,
    training_end,
    parameters,
    metrics,
    artefact_uri
) VALUES (
    'MODEL_RUN_SMOKE_001',
    'graph_aml_case_triage',
    'smoke_isolation_forest',
    '0.1.0-smoke',
    'isolation_forest',
    'smoke_v1',
    '2025-01-04T09:00:00Z',
    '2025-01-04T09:05:00Z',
    '{"n_estimators": 200, "contamination": 0.05, "random_state": 42}'::jsonb,
    '{"precision_at_10": 0.8, "smoke_dataset": true}'::jsonb,
    'mlruns/smoke/MODEL_RUN_SMOKE_001'
)
ON CONFLICT (model_run_id) DO UPDATE SET
    experiment_name = EXCLUDED.experiment_name,
    model_name = EXCLUDED.model_name,
    model_version = EXCLUDED.model_version,
    model_type = EXCLUDED.model_type,
    feature_version = EXCLUDED.feature_version,
    training_start = EXCLUDED.training_start,
    training_end = EXCLUDED.training_end,
    parameters = EXCLUDED.parameters,
    metrics = EXCLUDED.metrics,
    artefact_uri = EXCLUDED.artefact_uri;

INSERT INTO aml.alerts (
    alert_id,
    account_id,
    customer_id,
    rule_name,
    typology,
    severity,
    risk_score_rule,
    reason_code,
    evidence_ids,
    detection_window_start,
    detection_window_end,
    model_run_id,
    alert_status
) VALUES
    (
        'ALERT_SMOKE_001',
        'ACC_SMOKE_001',
        'CUST_SMOKE_001',
        'Structuring',
        'Smurfing',
        'high',
        82.00,
        '4 transfers below threshold within 24 hours',
        ARRAY['TXN_SMOKE_001', 'TXN_SMOKE_002', 'TXN_SMOKE_003', 'TXN_SMOKE_004'],
        '2025-01-01T00:00:00Z',
        '2025-01-02T00:00:00Z',
        'MODEL_RUN_SMOKE_001',
        'New'
    ),
    (
        'ALERT_SMOKE_002',
        'ACC_SMOKE_002',
        'CUST_SMOKE_002',
        'Fan-out',
        'Dispersion',
        'high',
        78.00,
        '3 unique recipients from one account within 7 days',
        ARRAY['TXN_SMOKE_005', 'TXN_SMOKE_006', 'TXN_SMOKE_007'],
        '2025-01-02T00:00:00Z',
        '2025-01-09T00:00:00Z',
        'MODEL_RUN_SMOKE_001',
        'New'
    )
ON CONFLICT (alert_id) DO UPDATE SET
    account_id = EXCLUDED.account_id,
    customer_id = EXCLUDED.customer_id,
    rule_name = EXCLUDED.rule_name,
    typology = EXCLUDED.typology,
    severity = EXCLUDED.severity,
    risk_score_rule = EXCLUDED.risk_score_rule,
    reason_code = EXCLUDED.reason_code,
    evidence_ids = EXCLUDED.evidence_ids,
    detection_window_start = EXCLUDED.detection_window_start,
    detection_window_end = EXCLUDED.detection_window_end,
    model_run_id = EXCLUDED.model_run_id,
    alert_status = EXCLUDED.alert_status,
    updated_at = NOW();

INSERT INTO aml.cases (
    case_id,
    primary_account_id,
    primary_customer_id,
    typologies,
    total_transaction_value,
    rule_typology_score,
    graph_risk_score,
    anomaly_score,
    customer_risk_score,
    jurisdiction_risk_score,
    case_risk_score,
    severity,
    status,
    explanation
) VALUES (
    'CASE_SMOKE_001',
    'ACC_SMOKE_001',
    'CUST_SMOKE_001',
    ARRAY['Smurfing', 'Dispersion'],
    67000.00,
    82.00,
    74.00,
    69.00,
    62.00,
    85.00,
    79.75,
    'high',
    'New',
    'Smoke case containing structuring and fan-out alerts across linked accounts.'
)
ON CONFLICT (case_id) DO UPDATE SET
    primary_account_id = EXCLUDED.primary_account_id,
    primary_customer_id = EXCLUDED.primary_customer_id,
    typologies = EXCLUDED.typologies,
    total_transaction_value = EXCLUDED.total_transaction_value,
    rule_typology_score = EXCLUDED.rule_typology_score,
    graph_risk_score = EXCLUDED.graph_risk_score,
    anomaly_score = EXCLUDED.anomaly_score,
    customer_risk_score = EXCLUDED.customer_risk_score,
    jurisdiction_risk_score = EXCLUDED.jurisdiction_risk_score,
    case_risk_score = EXCLUDED.case_risk_score,
    severity = EXCLUDED.severity,
    status = EXCLUDED.status,
    explanation = EXCLUDED.explanation,
    updated_at = NOW();

INSERT INTO aml.case_alerts (
    case_id,
    alert_id
) VALUES
    ('CASE_SMOKE_001', 'ALERT_SMOKE_001'),
    ('CASE_SMOKE_001', 'ALERT_SMOKE_002')
ON CONFLICT (case_id, alert_id) DO NOTHING;

INSERT INTO aml.case_entities (
    case_id,
    entity_type,
    entity_id,
    relationship_type
) VALUES
    ('CASE_SMOKE_001', 'account', 'ACC_SMOKE_001', 'primary_account'),
    ('CASE_SMOKE_001', 'account', 'ACC_SMOKE_002', 'related_account'),
    ('CASE_SMOKE_001', 'customer', 'CUST_SMOKE_002', 'related_customer')
ON CONFLICT ON CONSTRAINT uq_case_entities_entity DO UPDATE SET
    relationship_type = EXCLUDED.relationship_type;

INSERT INTO governance.audit_events (
    event_timestamp,
    event_type,
    component,
    run_id,
    pipeline_stage,
    entity_type,
    entity_id,
    action,
    status,
    details,
    created_by
)
SELECT
    '2025-01-04T10:00:00Z',
    'seed',
    'database',
    'RUN_SMOKE_SEED_001',
    'db_seed_smoke',
    'seed',
    'SEED_SMOKE_001',
    'insert_smoke_seed_data',
    'completed',
    '{"records": 38, "source": "005_seed_smoke_data.sql"}'::jsonb,
    'system'
WHERE NOT EXISTS (
    SELECT 1
    FROM governance.audit_events
    WHERE entity_id = 'SEED_SMOKE_001'
);

INSERT INTO governance.audit_events (
    event_timestamp,
    event_type,
    component,
    run_id,
    pipeline_stage,
    entity_type,
    entity_id,
    action,
    status,
    details,
    created_by
)
SELECT
    '2025-01-04T10:01:00Z',
    'case',
    'case_generation',
    'RUN_SMOKE_SEED_001',
    'case_smoke_seed',
    'case',
    'CASE_SMOKE_001',
    'create_smoke_case',
    'completed',
    '{"alert_count": 2, "case_risk_score": 79.75}'::jsonb,
    'system'
WHERE NOT EXISTS (
    SELECT 1
    FROM governance.audit_events
    WHERE entity_id = 'CASE_SMOKE_001'
);

INSERT INTO governance.validation_reports (
    validation_report_id,
    report_name,
    report_version,
    model_run_id,
    report_path,
    report_type,
    summary
) VALUES (
    'REPORT_SMOKE_001',
    'Smoke Validation Report',
    '0.1.0-smoke',
    'MODEL_RUN_SMOKE_001',
    'reports/model_validation/smoke_validation_report.md',
    'smoke',
    '{"purpose": "database smoke test", "records_seeded": 38, "limitations": "not representative"}'::jsonb
)
ON CONFLICT (validation_report_id) DO UPDATE SET
    report_name = EXCLUDED.report_name,
    report_version = EXCLUDED.report_version,
    model_run_id = EXCLUDED.model_run_id,
    report_path = EXCLUDED.report_path,
    report_type = EXCLUDED.report_type,
    summary = EXCLUDED.summary;
