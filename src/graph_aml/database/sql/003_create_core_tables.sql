-- Create core PostgreSQL tables for the Graph-Based AML Case Triage project.
-- This script is idempotent and assumes schemas already exist.

CREATE TABLE IF NOT EXISTS raw.customers_raw (
    raw_record_id BIGSERIAL PRIMARY KEY,
    source_system TEXT,
    source_file TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL,
    record_hash TEXT
);
COMMENT ON TABLE raw.customers_raw IS 'Source customer records stored as JSONB payloads before standardisation.';
COMMENT ON COLUMN raw.customers_raw.raw_payload IS 'Unmodified source customer record.';
CREATE INDEX IF NOT EXISTS idx_customers_raw_source_file ON raw.customers_raw (source_file);
CREATE INDEX IF NOT EXISTS idx_customers_raw_ingested_at ON raw.customers_raw (ingested_at);

CREATE TABLE IF NOT EXISTS raw.accounts_raw (
    raw_record_id BIGSERIAL PRIMARY KEY,
    source_system TEXT,
    source_file TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL,
    record_hash TEXT
);
COMMENT ON TABLE raw.accounts_raw IS 'Source account records stored as JSONB payloads before standardisation.';
COMMENT ON COLUMN raw.accounts_raw.raw_payload IS 'Unmodified source account record.';
CREATE INDEX IF NOT EXISTS idx_accounts_raw_source_file ON raw.accounts_raw (source_file);
CREATE INDEX IF NOT EXISTS idx_accounts_raw_ingested_at ON raw.accounts_raw (ingested_at);

CREATE TABLE IF NOT EXISTS raw.transactions_raw (
    raw_record_id BIGSERIAL PRIMARY KEY,
    source_system TEXT,
    source_file TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL,
    record_hash TEXT,
    transaction_id TEXT,
    sender_account_id TEXT,
    receiver_account_id TEXT,
    transaction_timestamp TIMESTAMPTZ,
    amount NUMERIC(18, 2),
    currency TEXT
);
COMMENT ON TABLE raw.transactions_raw IS 'Source transaction records with traceability columns and raw JSONB.';
COMMENT ON COLUMN raw.transactions_raw.raw_payload IS 'Unmodified source transaction record.';
COMMENT ON COLUMN raw.transactions_raw.transaction_id IS 'Optional source transaction identifier for lineage.';
CREATE INDEX IF NOT EXISTS idx_transactions_raw_source_file ON raw.transactions_raw (source_file);
CREATE INDEX IF NOT EXISTS idx_transactions_raw_ingested_at ON raw.transactions_raw (ingested_at);
CREATE INDEX IF NOT EXISTS idx_transactions_raw_transaction_id ON raw.transactions_raw (transaction_id);
CREATE INDEX IF NOT EXISTS idx_transactions_raw_timestamp ON raw.transactions_raw (transaction_timestamp);

CREATE TABLE IF NOT EXISTS raw.counterparties_raw (
    raw_record_id BIGSERIAL PRIMARY KEY,
    source_system TEXT,
    source_file TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL,
    record_hash TEXT
);
COMMENT ON TABLE raw.counterparties_raw IS 'Source counterparty records stored as JSONB payloads.';
COMMENT ON COLUMN raw.counterparties_raw.raw_payload IS 'Unmodified source counterparty record.';
CREATE INDEX IF NOT EXISTS idx_counterparties_raw_source_file ON raw.counterparties_raw (source_file);
CREATE INDEX IF NOT EXISTS idx_counterparties_raw_ingested_at ON raw.counterparties_raw (ingested_at);

CREATE TABLE IF NOT EXISTS raw.countries_raw (
    raw_record_id BIGSERIAL PRIMARY KEY,
    source_system TEXT,
    source_file TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL,
    record_hash TEXT
);
COMMENT ON TABLE raw.countries_raw IS 'Source country and jurisdiction reference records stored as JSONB.';
COMMENT ON COLUMN raw.countries_raw.raw_payload IS 'Unmodified source country or jurisdiction record.';
CREATE INDEX IF NOT EXISTS idx_countries_raw_source_file ON raw.countries_raw (source_file);
CREATE INDEX IF NOT EXISTS idx_countries_raw_ingested_at ON raw.countries_raw (ingested_at);

CREATE TABLE IF NOT EXISTS raw.devices_raw (
    raw_record_id BIGSERIAL PRIMARY KEY,
    source_system TEXT,
    source_file TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL,
    record_hash TEXT
);
COMMENT ON TABLE raw.devices_raw IS 'Source device and identifier records stored as JSONB payloads.';
COMMENT ON COLUMN raw.devices_raw.raw_payload IS 'Unmodified source device or identifier record.';
CREATE INDEX IF NOT EXISTS idx_devices_raw_source_file ON raw.devices_raw (source_file);
CREATE INDEX IF NOT EXISTS idx_devices_raw_ingested_at ON raw.devices_raw (ingested_at);

CREATE TABLE IF NOT EXISTS staging.countries (
    country_code TEXT PRIMARY KEY,
    country_name TEXT NOT NULL,
    region TEXT,
    is_high_risk BOOLEAN NOT NULL DEFAULT FALSE,
    risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_countries_risk_score_range CHECK (risk_score >= 0 AND risk_score <= 100)
);
COMMENT ON TABLE staging.countries IS 'Standardised country and jurisdiction risk reference data.';
COMMENT ON COLUMN staging.countries.is_high_risk IS 'Flag indicating high-risk jurisdiction treatment.';
CREATE INDEX IF NOT EXISTS idx_countries_is_high_risk ON staging.countries (is_high_risk);

CREATE TABLE IF NOT EXISTS staging.customers (
    customer_id TEXT PRIMARY KEY,
    customer_type TEXT NOT NULL,
    customer_segment TEXT,
    jurisdiction TEXT REFERENCES staging.countries(country_code),
    occupation TEXT,
    industry_code TEXT,
    customer_risk_rating TEXT,
    customer_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    onboarded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_customers_risk_score_range CHECK (
        customer_risk_score >= 0 AND customer_risk_score <= 100
    )
);
COMMENT ON TABLE staging.customers IS 'Standardised customer profiles and customer risk attributes.';
COMMENT ON COLUMN staging.customers.customer_risk_score IS 'Customer-level risk score normalised to 0-100.';
CREATE INDEX IF NOT EXISTS idx_customers_jurisdiction ON staging.customers (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_customers_risk_rating ON staging.customers (customer_risk_rating);

CREATE TABLE IF NOT EXISTS staging.accounts (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES staging.customers(customer_id),
    account_type TEXT NOT NULL,
    account_status TEXT NOT NULL,
    currency TEXT NOT NULL,
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    home_country TEXT REFERENCES staging.countries(country_code),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE staging.accounts IS 'Standardised account records linked to customers and jurisdictions.';
COMMENT ON COLUMN staging.accounts.customer_id IS 'Customer that owns the account.';
CREATE INDEX IF NOT EXISTS idx_accounts_customer_id ON staging.accounts (customer_id);
CREATE INDEX IF NOT EXISTS idx_accounts_home_country ON staging.accounts (home_country);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON staging.accounts (account_status);

CREATE TABLE IF NOT EXISTS staging.counterparties (
    counterparty_id TEXT PRIMARY KEY,
    counterparty_type TEXT NOT NULL,
    counterparty_name TEXT,
    country_code TEXT REFERENCES staging.countries(country_code),
    institution_name TEXT,
    external_account_ref TEXT,
    risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_counterparties_risk_score_range CHECK (risk_score >= 0 AND risk_score <= 100)
);
COMMENT ON TABLE staging.counterparties IS 'Standardised external counterparties, merchants, and institutions.';
COMMENT ON COLUMN staging.counterparties.external_account_ref IS 'External account reference when supplied by source data.';
CREATE INDEX IF NOT EXISTS idx_counterparties_country_code ON staging.counterparties (country_code);
CREATE INDEX IF NOT EXISTS idx_counterparties_type ON staging.counterparties (counterparty_type);

CREATE TABLE IF NOT EXISTS staging.devices (
    device_id TEXT PRIMARY KEY,
    device_type TEXT,
    ip_address TEXT,
    ip_cluster TEXT,
    phone_hash TEXT,
    browser_fingerprint TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE staging.devices IS 'Standardised device, IP, phone, and browser identifier records.';
COMMENT ON COLUMN staging.devices.ip_cluster IS 'Normalised IP cluster for shared identifier analysis.';
CREATE INDEX IF NOT EXISTS idx_devices_ip_cluster ON staging.devices (ip_cluster);
CREATE INDEX IF NOT EXISTS idx_devices_phone_hash ON staging.devices (phone_hash);

CREATE TABLE IF NOT EXISTS staging.transactions (
    transaction_id TEXT PRIMARY KEY,
    sender_account_id TEXT NOT NULL REFERENCES staging.accounts(account_id),
    receiver_account_id TEXT REFERENCES staging.accounts(account_id),
    counterparty_id TEXT REFERENCES staging.counterparties(counterparty_id),
    device_id TEXT REFERENCES staging.devices(device_id),
    transaction_timestamp TIMESTAMPTZ NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    currency TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    channel TEXT,
    origin_country TEXT REFERENCES staging.countries(country_code),
    destination_country TEXT REFERENCES staging.countries(country_code),
    is_cross_border BOOLEAN NOT NULL DEFAULT FALSE,
    is_labelled_suspicious BOOLEAN,
    typology_label TEXT,
    source_file TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_transactions_amount_positive CHECK (amount > 0)
);
COMMENT ON TABLE staging.transactions IS 'Standardised transaction records linked to accounts and evidence entities.';
COMMENT ON COLUMN staging.transactions.is_labelled_suspicious IS 'Optional synthetic or benchmark suspicious activity label.';
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON staging.transactions (transaction_timestamp);
CREATE INDEX IF NOT EXISTS idx_transactions_sender_account ON staging.transactions (sender_account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_receiver_account ON staging.transactions (receiver_account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_counterparty ON staging.transactions (counterparty_id);
CREATE INDEX IF NOT EXISTS idx_transactions_device ON staging.transactions (device_id);
CREATE INDEX IF NOT EXISTS idx_transactions_suspicious_label ON staging.transactions (is_labelled_suspicious);
CREATE INDEX IF NOT EXISTS idx_transactions_origin_country ON staging.transactions (origin_country);
CREATE INDEX IF NOT EXISTS idx_transactions_destination_country ON staging.transactions (destination_country);

CREATE TABLE IF NOT EXISTS mart.features_account_daily (
    feature_id BIGSERIAL PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES staging.accounts(account_id),
    feature_date DATE NOT NULL,
    feature_version TEXT NOT NULL,
    txn_count_1d INTEGER NOT NULL DEFAULT 0,
    txn_count_7d INTEGER NOT NULL DEFAULT 0,
    total_sent_7d NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_received_7d NUMERIC(18, 2) NOT NULL DEFAULT 0,
    avg_txn_amount_30d NUMERIC(18, 2) NOT NULL DEFAULT 0,
    max_txn_amount_30d NUMERIC(18, 2) NOT NULL DEFAULT 0,
    unique_counterparties_7d INTEGER NOT NULL DEFAULT 0,
    in_out_ratio_7d NUMERIC(18, 6),
    retained_balance_proxy NUMERIC(18, 2),
    below_threshold_count_24h INTEGER NOT NULL DEFAULT 0,
    dormant_days_before_activity INTEGER,
    cross_border_ratio_30d NUMERIC(10, 6),
    high_risk_country_exposure NUMERIC(10, 6),
    counterparty_entropy NUMERIC(10, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_features_account_daily_version UNIQUE (
        account_id,
        feature_date,
        feature_version
    )
);
COMMENT ON TABLE mart.features_account_daily IS 'Daily account-level behavioural features for rules and models.';
COMMENT ON COLUMN mart.features_account_daily.feature_version IS 'Feature generation version for reproducibility.';
CREATE INDEX IF NOT EXISTS idx_features_account_daily_account ON mart.features_account_daily (account_id);
CREATE INDEX IF NOT EXISTS idx_features_account_daily_date ON mart.features_account_daily (feature_date);

CREATE TABLE IF NOT EXISTS mart.graph_features (
    graph_feature_id BIGSERIAL UNIQUE,
    account_id TEXT NOT NULL REFERENCES staging.accounts(account_id),
    feature_date DATE NOT NULL,
    feature_version TEXT NOT NULL,
    graph_build_id TEXT NOT NULL,
    graph_database TEXT,
    computed_at TIMESTAMPTZ NOT NULL,
    degree DOUBLE PRECISION NOT NULL DEFAULT 0,
    in_degree DOUBLE PRECISION NOT NULL DEFAULT 0,
    out_degree DOUBLE PRECISION NOT NULL DEFAULT 0,
    degree_centrality DOUBLE PRECISION NOT NULL DEFAULT 0,
    in_degree_centrality DOUBLE PRECISION NOT NULL DEFAULT 0,
    out_degree_centrality DOUBLE PRECISION NOT NULL DEFAULT 0,
    pagerank_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    betweenness_centrality DOUBLE PRECISION NOT NULL DEFAULT 0,
    clustering_coefficient DOUBLE PRECISION NOT NULL DEFAULT 0,
    community_id INTEGER,
    community_size INTEGER NOT NULL DEFAULT 0,
    cycle_count INTEGER NOT NULL DEFAULT 0,
    fan_in_count INTEGER NOT NULL DEFAULT 0,
    fan_out_count INTEGER NOT NULL DEFAULT 0,
    alert_count INTEGER NOT NULL DEFAULT 0,
    high_risk_alert_count INTEGER NOT NULL DEFAULT 0,
    shortest_path_to_flagged INTEGER,
    neighbour_account_count INTEGER NOT NULL DEFAULT 0,
    counterparty_count INTEGER NOT NULL DEFAULT 0,
    transaction_count INTEGER NOT NULL DEFAULT 0,
    total_sent_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_received_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    graph_component_size INTEGER NOT NULL DEFAULT 0,
    graph_build_version TEXT,
    shared_device_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, feature_date, feature_version, graph_build_id)
);
COMMENT ON TABLE mart.graph_features IS 'Account-level graph analytics features from Neo4j transaction networks.';
COMMENT ON COLUMN mart.graph_features.feature_version IS 'Graph feature generation version for reproducibility.';
COMMENT ON COLUMN mart.graph_features.graph_build_id IS 'Deterministic graph build identifier for idempotent feature persistence.';
CREATE INDEX IF NOT EXISTS idx_graph_features_account_id
    ON mart.graph_features(account_id);
CREATE INDEX IF NOT EXISTS idx_graph_features_feature_date
    ON mart.graph_features(feature_date);
CREATE INDEX IF NOT EXISTS idx_graph_features_feature_version
    ON mart.graph_features(feature_version);
CREATE INDEX IF NOT EXISTS idx_graph_features_graph_build_id
    ON mart.graph_features(graph_build_id);
CREATE INDEX IF NOT EXISTS idx_graph_features_pagerank_score
    ON mart.graph_features(pagerank_score DESC);
CREATE INDEX IF NOT EXISTS idx_graph_features_high_risk_alert_count
    ON mart.graph_features(high_risk_alert_count DESC);
CREATE INDEX IF NOT EXISTS idx_graph_features_community
    ON mart.graph_features(community_id);

CREATE TABLE IF NOT EXISTS mart.account_anomaly_scores (
    account_id TEXT NOT NULL REFERENCES staging.accounts(account_id),
    score_date DATE NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_run_id TEXT NOT NULL,
    feature_date DATE,
    account_feature_version TEXT,
    graph_feature_version TEXT,
    graph_build_id TEXT,
    anomaly_score DOUBLE PRECISION NOT NULL,
    anomaly_score_raw DOUBLE PRECISION NOT NULL,
    anomaly_rank INTEGER NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    risk_band TEXT NOT NULL,
    feature_names JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    preprocessing_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    scored_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, score_date, model_name, model_version, model_run_id),
    CONSTRAINT chk_account_anomaly_scores_risk_band CHECK (
        risk_band IN ('low', 'medium', 'high')
    ),
    CONSTRAINT chk_account_anomaly_scores_score CHECK (
        anomaly_score >= 0 AND anomaly_score <= 100
    )
);
COMMENT ON TABLE mart.account_anomaly_scores IS 'Account-level Isolation Forest anomaly scores for downstream AML risk scoring.';
COMMENT ON COLUMN mart.account_anomaly_scores.model_run_id IS 'Deterministic model run identifier for idempotent anomaly score persistence.';
CREATE INDEX IF NOT EXISTS idx_account_anomaly_scores_account_id
    ON mart.account_anomaly_scores(account_id);
CREATE INDEX IF NOT EXISTS idx_account_anomaly_scores_score_date
    ON mart.account_anomaly_scores(score_date);
CREATE INDEX IF NOT EXISTS idx_account_anomaly_scores_model_version
    ON mart.account_anomaly_scores(model_version);
CREATE INDEX IF NOT EXISTS idx_account_anomaly_scores_model_run_id
    ON mart.account_anomaly_scores(model_run_id);
CREATE INDEX IF NOT EXISTS idx_account_anomaly_scores_anomaly_score
    ON mart.account_anomaly_scores(anomaly_score DESC);
CREATE INDEX IF NOT EXISTS idx_account_anomaly_scores_risk_band
    ON mart.account_anomaly_scores(risk_band);

CREATE TABLE IF NOT EXISTS mart.account_risk_scores (
    account_id TEXT NOT NULL REFERENCES staging.accounts(account_id),
    score_date DATE NOT NULL,
    score_name TEXT NOT NULL,
    score_version TEXT NOT NULL,
    account_risk_score DOUBLE PRECISION NOT NULL,
    risk_band TEXT NOT NULL,
    risk_rank INTEGER NOT NULL,
    rule_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    graph_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    anomaly_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    customer_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    jurisdiction_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    component_coverage DOUBLE PRECISION NOT NULL DEFAULT 0,
    alert_count INTEGER NOT NULL DEFAULT 0,
    high_severity_alert_count INTEGER NOT NULL DEFAULT 0,
    critical_severity_alert_count INTEGER NOT NULL DEFAULT 0,
    max_rule_alert_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    mean_rule_alert_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    max_anomaly_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    graph_percentile_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    scored_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, score_date, score_name, score_version),
    CONSTRAINT chk_account_risk_scores_risk_band CHECK (
        risk_band IN ('low', 'medium', 'high', 'critical')
    ),
    CONSTRAINT chk_account_risk_scores_score CHECK (
        account_risk_score >= 0 AND account_risk_score <= 100
    )
);
COMMENT ON TABLE mart.account_risk_scores IS 'Composite account-level AML risk scores for downstream case generation.';
COMMENT ON COLUMN mart.account_risk_scores.account_risk_score IS 'Weighted composite score normalised to 0-100.';
CREATE INDEX IF NOT EXISTS idx_account_risk_scores_account_id
    ON mart.account_risk_scores(account_id);
CREATE INDEX IF NOT EXISTS idx_account_risk_scores_score_date
    ON mart.account_risk_scores(score_date);
CREATE INDEX IF NOT EXISTS idx_account_risk_scores_score_version
    ON mart.account_risk_scores(score_version);
CREATE INDEX IF NOT EXISTS idx_account_risk_scores_risk_score
    ON mart.account_risk_scores(account_risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_account_risk_scores_risk_band
    ON mart.account_risk_scores(risk_band);

CREATE TABLE IF NOT EXISTS aml.alerts (
    alert_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES staging.accounts(account_id),
    customer_id TEXT REFERENCES staging.customers(customer_id),
    rule_name TEXT NOT NULL,
    typology TEXT NOT NULL,
    severity TEXT NOT NULL,
    risk_score_rule NUMERIC(5, 2) NOT NULL,
    reason_code TEXT NOT NULL,
    evidence_ids TEXT[] NOT NULL DEFAULT '{}',
    detection_window_start TIMESTAMPTZ,
    detection_window_end TIMESTAMPTZ,
    model_run_id TEXT,
    alert_status TEXT NOT NULL DEFAULT 'New',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_alerts_risk_score_rule_range CHECK (
        risk_score_rule >= 0 AND risk_score_rule <= 100
    ),
    CONSTRAINT chk_alerts_severity CHECK (severity IN ('low', 'medium', 'high', 'critical'))
);
COMMENT ON TABLE aml.alerts IS 'Rule-generated and model-generated AML alerts with evidence references.';
COMMENT ON COLUMN aml.alerts.evidence_ids IS 'Transaction or entity identifiers supporting the alert.';
CREATE INDEX IF NOT EXISTS idx_alerts_account ON aml.alerts (account_id);
CREATE INDEX IF NOT EXISTS idx_alerts_customer ON aml.alerts (customer_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON aml.alerts (severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON aml.alerts (alert_status);
CREATE INDEX IF NOT EXISTS idx_alerts_rule_name ON aml.alerts (rule_name);

CREATE TABLE IF NOT EXISTS aml.cases (
    case_id TEXT PRIMARY KEY,
    case_version TEXT NOT NULL DEFAULT 'case_generation_v1',
    primary_account_id TEXT REFERENCES staging.accounts(account_id),
    primary_customer_id TEXT REFERENCES staging.customers(customer_id),
    related_accounts JSONB NOT NULL DEFAULT '[]'::jsonb,
    related_customers JSONB NOT NULL DEFAULT '[]'::jsonb,
    alert_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    typologies JSONB NOT NULL DEFAULT '[]'::jsonb,
    rule_names JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_transaction_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    alert_count INTEGER NOT NULL DEFAULT 0,
    unique_typology_count INTEGER NOT NULL DEFAULT 0,
    evidence_transaction_count INTEGER NOT NULL DEFAULT 0,
    max_rule_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    mean_rule_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    max_account_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    priority_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    grouping_strategy TEXT NOT NULL DEFAULT 'account',
    case_group_key TEXT NOT NULL DEFAULT '',
    summary TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    rule_typology_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    graph_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    anomaly_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    customer_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    jurisdiction_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    case_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'New',
    explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_cases_case_risk_score_range CHECK (
        case_risk_score >= 0 AND case_risk_score <= 100
    ),
    CONSTRAINT chk_cases_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_cases_status CHECK (
        status IN (
            'New',
            'In review',
            'Escalated',
            'Information requested',
            'Closed false positive',
            'Closed suspicious',
            'Archived'
        )
    )
);
COMMENT ON TABLE aml.cases IS 'Grouped AML investigation cases with composite risk scores and statuses.';
COMMENT ON COLUMN aml.cases.case_risk_score IS 'Final composite case risk score normalised to 0-100.';
COMMENT ON COLUMN aml.cases.priority_score IS 'Deterministic case review priority based on alert and account risk context.';
CREATE INDEX IF NOT EXISTS idx_cases_primary_account ON aml.cases (primary_account_id);
CREATE INDEX IF NOT EXISTS idx_cases_primary_customer ON aml.cases (primary_customer_id);
CREATE INDEX IF NOT EXISTS idx_cases_primary_account_id ON aml.cases(primary_account_id);
CREATE INDEX IF NOT EXISTS idx_cases_primary_customer_id ON aml.cases(primary_customer_id);
CREATE INDEX IF NOT EXISTS idx_cases_priority_score ON aml.cases(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_cases_severity ON aml.cases (severity);
CREATE INDEX IF NOT EXISTS idx_cases_status ON aml.cases (status);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON aml.cases (created_at);

CREATE TABLE IF NOT EXISTS aml.case_alerts (
    case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    alert_id TEXT NOT NULL REFERENCES aml.alerts(alert_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, alert_id)
);
COMMENT ON TABLE aml.case_alerts IS 'Bridge table linking alerts to generated investigation cases.';
CREATE INDEX IF NOT EXISTS idx_case_alerts_alert ON aml.case_alerts (alert_id);
CREATE INDEX IF NOT EXISTS idx_case_alerts_alert_id ON aml.case_alerts(alert_id);

CREATE TABLE IF NOT EXISTS aml.case_entities (
    case_entity_id BIGSERIAL UNIQUE,
    case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    relationship TEXT NOT NULL DEFAULT 'related',
    relationship_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, entity_type, entity_id, relationship),
    CONSTRAINT uq_case_entities_entity UNIQUE (case_id, entity_type, entity_id)
);
COMMENT ON TABLE aml.case_entities IS 'Entities linked to investigation cases with relationship metadata.';
COMMENT ON COLUMN aml.case_entities.relationship_type IS 'Reason the entity is associated with the case.';
CREATE INDEX IF NOT EXISTS idx_case_entities_case ON aml.case_entities (case_id);
CREATE INDEX IF NOT EXISTS idx_case_entities_entity ON aml.case_entities (entity_type, entity_id);

CREATE TABLE IF NOT EXISTS aml.case_risk_scores (
    case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    score_date DATE NOT NULL,
    score_name TEXT NOT NULL,
    score_version TEXT NOT NULL,
    case_risk_score DOUBLE PRECISION NOT NULL,
    risk_band TEXT NOT NULL,
    risk_rank INTEGER NOT NULL,
    alert_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    account_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    graph_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    anomaly_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    typology_diversity_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    evidence_value_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    component_coverage DOUBLE PRECISION NOT NULL DEFAULT 0,
    alert_count INTEGER NOT NULL DEFAULT 0,
    typology_count INTEGER NOT NULL DEFAULT 0,
    related_account_count INTEGER NOT NULL DEFAULT 0,
    evidence_transaction_count INTEGER NOT NULL DEFAULT 0,
    total_transaction_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    max_alert_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    max_account_risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    max_anomaly_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    scored_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id, score_date, score_name, score_version),
    CONSTRAINT chk_case_risk_scores_risk_band CHECK (
        risk_band IN ('low', 'medium', 'high', 'critical')
    ),
    CONSTRAINT chk_case_risk_scores_score CHECK (
        case_risk_score >= 0 AND case_risk_score <= 100
    )
);
COMMENT ON TABLE aml.case_risk_scores IS 'Formal case-level composite AML risk scores for triage.';
CREATE INDEX IF NOT EXISTS idx_case_risk_scores_case_id
    ON aml.case_risk_scores(case_id);
CREATE INDEX IF NOT EXISTS idx_case_risk_scores_score_date
    ON aml.case_risk_scores(score_date);
CREATE INDEX IF NOT EXISTS idx_case_risk_scores_score_version
    ON aml.case_risk_scores(score_version);
CREATE INDEX IF NOT EXISTS idx_case_risk_scores_risk_score
    ON aml.case_risk_scores(case_risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_case_risk_scores_risk_band
    ON aml.case_risk_scores(risk_band);

CREATE TABLE IF NOT EXISTS aml.case_evidence_packs (
    case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    evidence_version TEXT NOT NULL,
    case_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    typology_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    alert_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    transaction_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    account_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    graph_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_driver_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    chronology JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_review_focus JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_quality JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id, evidence_version)
);
COMMENT ON TABLE aml.case_evidence_packs IS 'Structured case evidence packs for deterministic AML case review.';
CREATE INDEX IF NOT EXISTS idx_case_evidence_packs_case_id
    ON aml.case_evidence_packs(case_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_packs_evidence_version
    ON aml.case_evidence_packs(evidence_version);

CREATE TABLE IF NOT EXISTS aml.case_explanations (
    case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    explanation_version TEXT NOT NULL,
    explanation_text TEXT NOT NULL,
    explanation_bullets JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_driver_summary TEXT,
    typology_summary TEXT,
    transaction_summary TEXT,
    graph_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id, explanation_version)
);
COMMENT ON TABLE aml.case_explanations IS 'Deterministic template-based explanations for AML cases.';
CREATE INDEX IF NOT EXISTS idx_case_explanations_case_id
    ON aml.case_explanations(case_id);
CREATE INDEX IF NOT EXISTS idx_case_explanations_explanation_version
    ON aml.case_explanations(explanation_version);

CREATE TABLE IF NOT EXISTS aml.case_lifecycle_events (
    action_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    analyst_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    assigned_to TEXT,
    queue TEXT,
    decision_reason TEXT,
    comment TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    action_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE aml.case_lifecycle_events IS 'Append-only analyst lifecycle events for AML cases.';

CREATE TABLE IF NOT EXISTS aml.case_assignments (
    case_id TEXT PRIMARY KEY REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    assigned_to TEXT,
    queue TEXT,
    assigned_by TEXT,
    assigned_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE aml.case_assignments IS 'Current AML case assignment snapshot.';

CREATE INDEX IF NOT EXISTS idx_case_lifecycle_events_case_id
    ON aml.case_lifecycle_events(case_id);
CREATE INDEX IF NOT EXISTS idx_case_lifecycle_events_action_type
    ON aml.case_lifecycle_events(action_type);
CREATE INDEX IF NOT EXISTS idx_case_lifecycle_events_analyst_id
    ON aml.case_lifecycle_events(analyst_id);
CREATE INDEX IF NOT EXISTS idx_case_lifecycle_events_timestamp
    ON aml.case_lifecycle_events(action_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_case_assignments_assigned_to
    ON aml.case_assignments(assigned_to);

ALTER TABLE aml.cases
    ADD COLUMN IF NOT EXISTS case_risk_band TEXT;

ALTER TABLE aml.cases
    ADD COLUMN IF NOT EXISTS case_risk_rank INTEGER;

ALTER TABLE aml.cases
    ADD COLUMN IF NOT EXISTS assigned_to TEXT;

ALTER TABLE aml.cases
    ADD COLUMN IF NOT EXISTS queue TEXT;

ALTER TABLE aml.cases
    ADD COLUMN IF NOT EXISTS last_decision_reason TEXT;

ALTER TABLE aml.cases
    ADD COLUMN IF NOT EXISTS last_decision_at TIMESTAMPTZ;

ALTER TABLE aml.cases
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_cases_assigned_to
    ON aml.cases(assigned_to);
CREATE INDEX IF NOT EXISTS idx_cases_last_decision_at
    ON aml.cases(last_decision_at DESC);

CREATE TABLE IF NOT EXISTS aml.case_labels (
    case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    label_version TEXT NOT NULL,
    case_label INTEGER NOT NULL,
    label_name TEXT NOT NULL,
    source_status TEXT NOT NULL,
    source_action_type TEXT,
    analyst_id TEXT,
    decision_reason TEXT,
    comment TEXT,
    label_timestamp TIMESTAMPTZ NOT NULL,
    case_created_at TIMESTAMPTZ,
    case_updated_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id, label_version)
);
COMMENT ON TABLE aml.case_labels IS 'Analyst feedback case labels derived from explicit lifecycle closure decisions.';

CREATE TABLE IF NOT EXISTS aml.account_labels (
    account_id TEXT NOT NULL REFERENCES staging.accounts(account_id),
    label_version TEXT NOT NULL,
    account_label INTEGER NOT NULL,
    label_name TEXT NOT NULL,
    source_case_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_case_labels JSONB NOT NULL DEFAULT '[]'::jsonb,
    label_timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, label_version)
);
COMMENT ON TABLE aml.account_labels IS 'Account-level labels propagated from reviewed case outcomes.';

CREATE TABLE IF NOT EXISTS mart.case_supervised_dataset (
    case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE,
    dataset_version TEXT NOT NULL,
    case_label INTEGER NOT NULL,
    label_name TEXT NOT NULL,
    label_timestamp TIMESTAMPTZ NOT NULL,
    case_risk_score DOUBLE PRECISION,
    risk_band TEXT,
    alert_count INTEGER,
    typology_count INTEGER,
    related_account_count INTEGER,
    evidence_transaction_count INTEGER,
    total_transaction_value DOUBLE PRECISION,
    component_coverage DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id, dataset_version)
);
COMMENT ON TABLE mart.case_supervised_dataset IS 'Case-level supervised learning readiness dataset.';

CREATE TABLE IF NOT EXISTS mart.account_supervised_dataset (
    account_id TEXT NOT NULL REFERENCES staging.accounts(account_id),
    dataset_version TEXT NOT NULL,
    account_label INTEGER NOT NULL,
    label_name TEXT NOT NULL,
    label_timestamp TIMESTAMPTZ NOT NULL,
    account_risk_score DOUBLE PRECISION,
    risk_band TEXT,
    anomaly_score DOUBLE PRECISION,
    graph_risk_score DOUBLE PRECISION,
    rule_risk_score DOUBLE PRECISION,
    customer_risk_score DOUBLE PRECISION,
    jurisdiction_risk_score DOUBLE PRECISION,
    degree_centrality DOUBLE PRECISION,
    pagerank_score DOUBLE PRECISION,
    betweenness_centrality DOUBLE PRECISION,
    cycle_count DOUBLE PRECISION,
    community_size DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, dataset_version)
);
COMMENT ON TABLE mart.account_supervised_dataset IS 'Account-level supervised learning readiness dataset.';

CREATE INDEX IF NOT EXISTS idx_case_labels_label_version
    ON aml.case_labels(label_version);
CREATE INDEX IF NOT EXISTS idx_case_labels_case_label
    ON aml.case_labels(case_label);
CREATE INDEX IF NOT EXISTS idx_account_labels_label_version
    ON aml.account_labels(label_version);
CREATE INDEX IF NOT EXISTS idx_account_labels_account_label
    ON aml.account_labels(account_label);
CREATE INDEX IF NOT EXISTS idx_case_supervised_dataset_label
    ON mart.case_supervised_dataset(case_label);
CREATE INDEX IF NOT EXISTS idx_account_supervised_dataset_label
    ON mart.account_supervised_dataset(account_label);

CREATE TABLE IF NOT EXISTS mart.supervised_model_scores (
    entity_id TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_family TEXT NOT NULL,
    score_date DATE NOT NULL,
    supervised_score DOUBLE PRECISION NOT NULL,
    predicted_label INTEGER NOT NULL,
    risk_rank INTEGER NOT NULL,
    label INTEGER,
    label_name TEXT,
    label_timestamp TIMESTAMPTZ,
    dataset_version TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_id, entity_level, model_name, model_version, score_date)
);
COMMENT ON TABLE mart.supervised_model_scores IS 'Supervised AML model probability scores.';

CREATE TABLE IF NOT EXISTS governance.supervised_model_runs (
    run_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_family TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    feature_names JSONB NOT NULL DEFAULT '[]'::jsonb,
    train_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    threshold_metrics JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_k_metrics JSONB NOT NULL DEFAULT '[]'::jsonb,
    artefact_paths JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    trained_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.supervised_model_runs IS 'Supervised AML model run metadata.';

CREATE INDEX IF NOT EXISTS idx_supervised_model_scores_entity_level
    ON mart.supervised_model_scores(entity_level);
CREATE INDEX IF NOT EXISTS idx_supervised_model_scores_model_version
    ON mart.supervised_model_scores(model_version);
CREATE INDEX IF NOT EXISTS idx_supervised_model_scores_score
    ON mart.supervised_model_scores(supervised_score DESC);
CREATE INDEX IF NOT EXISTS idx_supervised_model_scores_dataset_version
    ON mart.supervised_model_scores(dataset_version);
CREATE INDEX IF NOT EXISTS idx_supervised_model_runs_model_version
    ON governance.supervised_model_runs(model_version);
CREATE INDEX IF NOT EXISTS idx_supervised_model_runs_trained_at
    ON governance.supervised_model_runs(trained_at DESC);

CREATE TABLE IF NOT EXISTS governance.model_comparison_runs (
    comparison_run_id TEXT PRIMARY KEY,
    comparison_name TEXT NOT NULL,
    comparison_version TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    label_version TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    champion_candidate TEXT,
    candidate_count INTEGER NOT NULL DEFAULT 0,
    labelled_entity_count INTEGER NOT NULL DEFAULT 0,
    positive_count INTEGER NOT NULL DEFAULT 0,
    negative_count INTEGER NOT NULL DEFAULT 0,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.model_comparison_runs IS 'Model comparison validation run metadata.';

CREATE TABLE IF NOT EXISTS governance.model_comparison_metrics (
    comparison_run_id TEXT NOT NULL,
    candidate_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    top_k INTEGER,
    threshold DOUBLE PRECISION,
    entity_count INTEGER,
    positive_count INTEGER,
    negative_count INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.model_comparison_metrics IS 'Candidate score comparison metrics.';

CREATE TABLE IF NOT EXISTS governance.threshold_recommendations (
    comparison_run_id TEXT NOT NULL,
    candidate_name TEXT NOT NULL,
    recommended_threshold DOUBLE PRECISION,
    precision DOUBLE PRECISION,
    recall DOUBLE PRECISION,
    f1 DOUBLE PRECISION,
    review_volume INTEGER,
    review_rate DOUBLE PRECISION,
    meets_min_precision BOOLEAN,
    meets_min_recall BOOLEAN,
    selection_reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (comparison_run_id, candidate_name)
);
COMMENT ON TABLE governance.threshold_recommendations IS 'Recommended candidate operating thresholds.';

CREATE TABLE IF NOT EXISTS governance.champion_challenger_results (
    comparison_run_id TEXT NOT NULL,
    candidate_name TEXT NOT NULL,
    is_champion BOOLEAN NOT NULL DEFAULT false,
    selection_metric TEXT,
    selection_metric_value DOUBLE PRECISION,
    selection_top_k INTEGER,
    precision_at_k DOUBLE PRECISION,
    recall_at_k DOUBLE PRECISION,
    pr_auc DOUBLE PRECISION,
    roc_auc DOUBLE PRECISION,
    recommended_threshold DOUBLE PRECISION,
    review_volume INTEGER,
    selection_rank INTEGER,
    selection_reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (comparison_run_id, candidate_name)
);
COMMENT ON TABLE governance.champion_challenger_results IS 'Champion-challenger model comparison outcomes.';

CREATE INDEX IF NOT EXISTS idx_model_comparison_runs_version
    ON governance.model_comparison_runs(comparison_version);
CREATE INDEX IF NOT EXISTS idx_model_comparison_runs_created_at
    ON governance.model_comparison_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_model_comparison_metrics_run
    ON governance.model_comparison_metrics(comparison_run_id);
CREATE INDEX IF NOT EXISTS idx_model_comparison_metrics_candidate
    ON governance.model_comparison_metrics(candidate_name);
CREATE INDEX IF NOT EXISTS idx_threshold_recommendations_candidate
    ON governance.threshold_recommendations(candidate_name);
CREATE INDEX IF NOT EXISTS idx_champion_challenger_results_champion
    ON governance.champion_challenger_results(is_champion);

CREATE TABLE IF NOT EXISTS governance.monitoring_runs (
    monitoring_run_id TEXT PRIMARY KEY,
    monitoring_name TEXT NOT NULL,
    monitoring_version TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    baseline_window_start DATE,
    baseline_window_end DATE,
    comparison_window_start DATE,
    comparison_window_end DATE,
    high_drift_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    critical_count INTEGER NOT NULL DEFAULT 0,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.monitoring_runs IS 'Monitoring, drift, and backtesting run metadata.';

CREATE TABLE IF NOT EXISTS governance.drift_metrics (
    monitoring_run_id TEXT NOT NULL,
    metric_scope TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    drift_metric TEXT NOT NULL,
    drift_value DOUBLE PRECISION,
    drift_band TEXT NOT NULL,
    baseline_count INTEGER,
    comparison_count INTEGER,
    baseline_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    comparison_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.drift_metrics IS 'Feature and score drift metrics by monitoring run.';

CREATE TABLE IF NOT EXISTS governance.score_monitoring_metrics (
    monitoring_run_id TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    score_name TEXT NOT NULL,
    window_name TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    min_score DOUBLE PRECISION,
    max_score DOUBLE PRECISION,
    mean_score DOUBLE PRECISION,
    median_score DOUBLE PRECISION,
    std_score DOUBLE PRECISION,
    p90_score DOUBLE PRECISION,
    p95_score DOUBLE PRECISION,
    high_risk_share DOUBLE PRECISION,
    top_k_mean_score DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.score_monitoring_metrics IS 'Score stability metrics by monitoring window.';

CREATE TABLE IF NOT EXISTS governance.volume_monitoring_metrics (
    monitoring_run_id TEXT NOT NULL,
    volume_type TEXT NOT NULL,
    window_name TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    baseline_count INTEGER,
    comparison_count INTEGER,
    relative_change DOUBLE PRECISION,
    severity_band TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.volume_monitoring_metrics IS 'Alert, case, and typology volume stability metrics.';

CREATE TABLE IF NOT EXISTS governance.segment_monitoring_metrics (
    monitoring_run_id TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    segment_column TEXT NOT NULL,
    segment_value TEXT NOT NULL,
    window_name TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    positive_count INTEGER,
    positive_rate DOUBLE PRECISION,
    mean_score DOUBLE PRECISION,
    median_score DOUBLE PRECISION,
    high_risk_share DOUBLE PRECISION,
    precision_at_k DOUBLE PRECISION,
    recall_at_k DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.segment_monitoring_metrics IS 'Segment-level monitoring metrics.';

CREATE TABLE IF NOT EXISTS governance.backtesting_metrics (
    monitoring_run_id TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    window_name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    row_count INTEGER,
    positive_count INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.backtesting_metrics IS 'Backtesting metrics across historical windows.';

CREATE INDEX IF NOT EXISTS idx_monitoring_runs_version
    ON governance.monitoring_runs(monitoring_version);
CREATE INDEX IF NOT EXISTS idx_monitoring_runs_created_at
    ON governance.monitoring_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_drift_metrics_run
    ON governance.drift_metrics(monitoring_run_id);
CREATE INDEX IF NOT EXISTS idx_drift_metrics_band
    ON governance.drift_metrics(drift_band);
CREATE INDEX IF NOT EXISTS idx_score_monitoring_metrics_run
    ON governance.score_monitoring_metrics(monitoring_run_id);
CREATE INDEX IF NOT EXISTS idx_volume_monitoring_metrics_run
    ON governance.volume_monitoring_metrics(monitoring_run_id);
CREATE INDEX IF NOT EXISTS idx_segment_monitoring_metrics_run
    ON governance.segment_monitoring_metrics(monitoring_run_id);
CREATE INDEX IF NOT EXISTS idx_backtesting_metrics_run
    ON governance.backtesting_metrics(monitoring_run_id);

CREATE TABLE IF NOT EXISTS governance.explainability_runs (
    explanation_run_id TEXT PRIMARY KEY,
    explanation_name TEXT NOT NULL,
    explanation_version TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    model_version TEXT,
    dataset_version TEXT,
    comparison_version TEXT,
    monitoring_version TEXT,
    global_feature_count INTEGER NOT NULL DEFAULT 0,
    local_contribution_count INTEGER NOT NULL DEFAULT 0,
    score_decomposition_count INTEGER NOT NULL DEFAULT 0,
    reason_contribution_count INTEGER NOT NULL DEFAULT 0,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.explainability_runs IS 'Explainability and model-card run metadata.';

CREATE TABLE IF NOT EXISTS governance.global_feature_importance (
    explanation_run_id TEXT NOT NULL,
    model_name TEXT,
    model_version TEXT,
    entity_level TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    importance_value DOUBLE PRECISION,
    importance_rank INTEGER,
    importance_method TEXT NOT NULL,
    direction TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.global_feature_importance IS 'Global supervised feature attribution rows.';

CREATE TABLE IF NOT EXISTS governance.local_feature_contributions (
    explanation_run_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    model_name TEXT,
    model_version TEXT,
    feature_name TEXT NOT NULL,
    feature_value DOUBLE PRECISION,
    contribution_value DOUBLE PRECISION,
    contribution_rank INTEGER,
    importance_method TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.local_feature_contributions IS 'Local supervised feature contribution rows.';

CREATE TABLE IF NOT EXISTS governance.score_decomposition (
    explanation_run_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    score_name TEXT NOT NULL,
    component_name TEXT NOT NULL,
    component_value DOUBLE PRECISION,
    component_weight DOUBLE PRECISION,
    weighted_contribution DOUBLE PRECISION,
    contribution_rank INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.score_decomposition IS 'Composite score component decomposition rows.';

CREATE TABLE IF NOT EXISTS governance.reason_contributions (
    explanation_run_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_level TEXT NOT NULL,
    reason_type TEXT NOT NULL,
    reason_name TEXT NOT NULL,
    reason_value TEXT,
    reason_rank INTEGER,
    source_table TEXT,
    source_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.reason_contributions IS 'Reason-code contribution rows across rules, graph, anomaly, supervised, evidence, and labels.';

CREATE TABLE IF NOT EXISTS governance.model_cards (
    explanation_run_id TEXT NOT NULL,
    model_card_version TEXT NOT NULL,
    model_card_markdown TEXT NOT NULL,
    model_card_sections JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (explanation_run_id, model_card_version)
);
COMMENT ON TABLE governance.model_cards IS 'Consolidated AML model card Markdown and section metadata.';

CREATE INDEX IF NOT EXISTS idx_explainability_runs_version
    ON governance.explainability_runs(explanation_version);
CREATE INDEX IF NOT EXISTS idx_explainability_runs_created_at
    ON governance.explainability_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_global_feature_importance_run
    ON governance.global_feature_importance(explanation_run_id);
CREATE INDEX IF NOT EXISTS idx_local_feature_contributions_run
    ON governance.local_feature_contributions(explanation_run_id);
CREATE INDEX IF NOT EXISTS idx_score_decomposition_run
    ON governance.score_decomposition(explanation_run_id);
CREATE INDEX IF NOT EXISTS idx_reason_contributions_run
    ON governance.reason_contributions(explanation_run_id);
CREATE INDEX IF NOT EXISTS idx_model_cards_run
    ON governance.model_cards(explanation_run_id);

CREATE TABLE IF NOT EXISTS governance.inventory_runs (
    inventory_run_id TEXT PRIMARY KEY,
    inventory_name TEXT NOT NULL,
    inventory_version TEXT NOT NULL,
    lineage_node_count INTEGER NOT NULL DEFAULT 0,
    lineage_edge_count INTEGER NOT NULL DEFAULT 0,
    artefact_count INTEGER NOT NULL DEFAULT 0,
    process_count INTEGER NOT NULL DEFAULT 0,
    model_inventory_count INTEGER NOT NULL DEFAULT 0,
    validation_inventory_count INTEGER NOT NULL DEFAULT 0,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.inventory_runs IS 'Governance inventory run metadata and summary counts.';

CREATE TABLE IF NOT EXISTS governance.lineage_nodes (
    inventory_run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    name TEXT NOT NULL,
    schema_name TEXT,
    version TEXT,
    row_count BIGINT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (inventory_run_id, node_id)
);
COMMENT ON TABLE governance.lineage_nodes IS 'Data, process, artefact, and run nodes in the governance lineage graph.';

CREATE TABLE IF NOT EXISTS governance.lineage_edges (
    inventory_run_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    process_name TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (inventory_run_id, source_id, target_id, relationship_type)
);
COMMENT ON TABLE governance.lineage_edges IS 'Directed lineage and dependency edges between inventory nodes.';

CREATE TABLE IF NOT EXISTS governance.artefact_registry (
    inventory_run_id TEXT NOT NULL,
    artefact_id TEXT NOT NULL,
    artefact_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    extension TEXT NOT NULL,
    size_bytes BIGINT,
    hash_value TEXT,
    modified_at TIMESTAMPTZ,
    source_dir TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (inventory_run_id, artefact_id)
);
COMMENT ON TABLE governance.artefact_registry IS 'Versioned registry of local governance, documentation, and validation artefacts.';

CREATE TABLE IF NOT EXISTS governance.process_inventory (
    inventory_run_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    input_count INTEGER NOT NULL DEFAULT 0,
    output_count INTEGER NOT NULL DEFAULT 0,
    inputs JSONB NOT NULL DEFAULT '[]'::jsonb,
    outputs JSONB NOT NULL DEFAULT '[]'::jsonb,
    latest_audit_timestamp TIMESTAMPTZ,
    latest_status TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (inventory_run_id, process_name)
);
COMMENT ON TABLE governance.process_inventory IS 'Configured process inventory with inputs, outputs, and latest audit status.';

CREATE TABLE IF NOT EXISTS governance.model_inventory (
    inventory_run_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    model_family TEXT,
    dataset_version TEXT,
    entity_level TEXT,
    run_count INTEGER NOT NULL DEFAULT 0,
    latest_run_timestamp TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.model_inventory IS 'Inventory of persisted model runs by model, version, family, and dataset.';

CREATE TABLE IF NOT EXISTS governance.validation_inventory (
    inventory_run_id TEXT NOT NULL,
    validation_type TEXT NOT NULL,
    validation_version TEXT,
    run_count INTEGER NOT NULL DEFAULT 0,
    latest_run_id TEXT,
    latest_run_timestamp TIMESTAMPTZ,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.validation_inventory IS 'Inventory of persisted validation, monitoring, and explainability runs.';

CREATE INDEX IF NOT EXISTS idx_inventory_runs_version
    ON governance.inventory_runs(inventory_version);
CREATE INDEX IF NOT EXISTS idx_inventory_runs_created_at
    ON governance.inventory_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_type
    ON governance.lineage_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_process
    ON governance.lineage_edges(process_name);
CREATE INDEX IF NOT EXISTS idx_artefact_registry_type
    ON governance.artefact_registry(artefact_type);
CREATE INDEX IF NOT EXISTS idx_process_inventory_process
    ON governance.process_inventory(process_name);
CREATE INDEX IF NOT EXISTS idx_model_inventory_model_version
    ON governance.model_inventory(model_version);
CREATE INDEX IF NOT EXISTS idx_validation_inventory_type
    ON governance.validation_inventory(validation_type);

CREATE TABLE IF NOT EXISTS governance.security_control_runs (
    security_run_id TEXT PRIMARY KEY,
    security_name TEXT NOT NULL,
    security_version TEXT NOT NULL,
    sensitive_field_count INTEGER NOT NULL DEFAULT 0,
    restricted_field_count INTEGER NOT NULL DEFAULT 0,
    confidential_field_count INTEGER NOT NULL DEFAULT 0,
    unallowed_secret_finding_count INTEGER NOT NULL DEFAULT 0,
    audit_integrity_issue_count INTEGER NOT NULL DEFAULT 0,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.security_control_runs IS 'Security controls, privacy safeguards, and access governance run metadata.';

CREATE TABLE IF NOT EXISTS governance.sensitive_field_inventory (
    security_run_id TEXT NOT NULL,
    schema_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    classification TEXT NOT NULL,
    matched_pattern TEXT,
    recommended_masking_strategy TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (security_run_id, schema_name, table_name, column_name)
);
COMMENT ON TABLE governance.sensitive_field_inventory IS 'Classified sensitive field inventory and recommended masking strategies.';

CREATE TABLE IF NOT EXISTS governance.permission_matrix (
    security_run_id TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    allowed BOOLEAN NOT NULL,
    reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (security_run_id, role, action)
);
COMMENT ON TABLE governance.permission_matrix IS 'Role-action permission policy snapshots for dashboard and export governance.';

CREATE TABLE IF NOT EXISTS governance.secrets_scan_findings (
    security_run_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    pattern_name TEXT NOT NULL,
    line_number INTEGER,
    match_preview TEXT,
    allowed BOOLEAN NOT NULL DEFAULT false,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.secrets_scan_findings IS 'Redacted local secret-like string scan findings.';

CREATE TABLE IF NOT EXISTS governance.audit_integrity_checks (
    security_run_id TEXT NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    issue_count INTEGER NOT NULL DEFAULT 0,
    severity TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.audit_integrity_checks IS 'Audit log integrity check outputs.';

CREATE INDEX IF NOT EXISTS idx_security_control_runs_version
    ON governance.security_control_runs(security_version);
CREATE INDEX IF NOT EXISTS idx_security_control_runs_created_at
    ON governance.security_control_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sensitive_field_inventory_classification
    ON governance.sensitive_field_inventory(classification);
CREATE INDEX IF NOT EXISTS idx_permission_matrix_role
    ON governance.permission_matrix(role);
CREATE INDEX IF NOT EXISTS idx_secrets_scan_findings_allowed
    ON governance.secrets_scan_findings(allowed);
CREATE INDEX IF NOT EXISTS idx_audit_integrity_checks_status
    ON governance.audit_integrity_checks(status);

CREATE TABLE IF NOT EXISTS governance.release_readiness_runs (
    release_run_id TEXT PRIMARY KEY,
    release_name TEXT NOT NULL,
    release_version TEXT NOT NULL,
    repository_check_count INTEGER NOT NULL DEFAULT 0,
    documentation_check_count INTEGER NOT NULL DEFAULT 0,
    artefact_check_count INTEGER NOT NULL DEFAULT 0,
    failed_check_count INTEGER NOT NULL DEFAULT 0,
    warning_check_count INTEGER NOT NULL DEFAULT 0,
    validation_artefact_count INTEGER NOT NULL DEFAULT 0,
    evidence_item_count INTEGER NOT NULL DEFAULT 0,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.release_readiness_runs IS 'Release readiness run metadata for portfolio evidence packaging.';

CREATE TABLE IF NOT EXISTS governance.release_repository_checks (
    release_run_id TEXT NOT NULL,
    check_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_name TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.release_repository_checks IS 'Repository hygiene checks for release readiness.';

CREATE TABLE IF NOT EXISTS governance.release_documentation_checks (
    release_run_id TEXT NOT NULL,
    document_path TEXT NOT NULL,
    check_name TEXT NOT NULL,
    required_section TEXT,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.release_documentation_checks IS 'Documentation completeness checks for release readiness.';

CREATE TABLE IF NOT EXISTS governance.release_artefact_checks (
    release_run_id TEXT NOT NULL,
    artefact_name TEXT NOT NULL,
    relative_path TEXT,
    artefact_type TEXT,
    required BOOLEAN NOT NULL DEFAULT false,
    status TEXT NOT NULL,
    size_bytes BIGINT,
    modified_at TIMESTAMPTZ,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.release_artefact_checks IS 'Validation artefact availability checks for release readiness.';

CREATE TABLE IF NOT EXISTS governance.release_evidence_index (
    release_run_id TEXT NOT NULL,
    evidence_name TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    relative_path TEXT,
    status TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.release_evidence_index IS 'Demo evidence pack index for portfolio review.';

CREATE TABLE IF NOT EXISTS governance.release_portfolio_pack (
    release_run_id TEXT PRIMARY KEY,
    portfolio_summary_md TEXT NOT NULL,
    architecture_summary_md TEXT NOT NULL,
    dashboard_walkthrough_md TEXT NOT NULL,
    command_transcript_template_md TEXT NOT NULL,
    demo_validation_checklist_md TEXT NOT NULL,
    validation_index JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_index JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE governance.release_portfolio_pack IS 'Portfolio narrative, architecture, dashboard walkthrough, and command transcript evidence.';

CREATE INDEX IF NOT EXISTS idx_release_readiness_runs_version
    ON governance.release_readiness_runs(release_version);
CREATE INDEX IF NOT EXISTS idx_release_readiness_runs_created_at
    ON governance.release_readiness_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_release_repository_checks_status
    ON governance.release_repository_checks(status);
CREATE INDEX IF NOT EXISTS idx_release_documentation_checks_status
    ON governance.release_documentation_checks(status);
CREATE INDEX IF NOT EXISTS idx_release_artefact_checks_status
    ON governance.release_artefact_checks(status);
CREATE INDEX IF NOT EXISTS idx_release_evidence_index_type
    ON governance.release_evidence_index(evidence_type);

CREATE TABLE IF NOT EXISTS governance.audit_events (
    audit_event_id BIGSERIAL PRIMARY KEY,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    component TEXT NOT NULL,
    run_id TEXT,
    pipeline_stage TEXT,
    entity_type TEXT,
    entity_id TEXT,
    action TEXT NOT NULL,
    status TEXT,
    details JSONB NOT NULL DEFAULT '{}',
    created_by TEXT NOT NULL DEFAULT 'system'
);
COMMENT ON TABLE governance.audit_events IS 'Runtime, pipeline, model, and analyst action audit events.';
COMMENT ON COLUMN governance.audit_events.details IS 'Structured audit event details.';
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON governance.audit_events (event_timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON governance.audit_events (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON governance.audit_events (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_run_id ON governance.audit_events (run_id);

CREATE TABLE IF NOT EXISTS governance.model_runs (
    model_run_id TEXT PRIMARY KEY,
    experiment_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    model_type TEXT NOT NULL,
    feature_version TEXT,
    training_start TIMESTAMPTZ,
    training_end TIMESTAMPTZ,
    parameters JSONB NOT NULL DEFAULT '{}',
    metrics JSONB NOT NULL DEFAULT '{}',
    artefact_uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE governance.model_runs IS 'Model run metadata, parameters, metrics, and artefact references.';
COMMENT ON COLUMN governance.model_runs.metrics IS 'Tracked model metrics for validation and comparison.';
CREATE INDEX IF NOT EXISTS idx_model_runs_experiment ON governance.model_runs (experiment_name);
CREATE INDEX IF NOT EXISTS idx_model_runs_model_name ON governance.model_runs (model_name);
CREATE INDEX IF NOT EXISTS idx_model_runs_created_at ON governance.model_runs (created_at);

CREATE TABLE IF NOT EXISTS governance.validation_reports (
    validation_report_id TEXT PRIMARY KEY,
    report_name TEXT NOT NULL,
    report_version TEXT NOT NULL,
    model_run_id TEXT REFERENCES governance.model_runs(model_run_id),
    report_path TEXT NOT NULL,
    report_type TEXT NOT NULL,
    summary JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE governance.validation_reports IS 'Validation report metadata and links to model runs.';
COMMENT ON COLUMN governance.validation_reports.summary IS 'Structured summary of validation findings.';
CREATE INDEX IF NOT EXISTS idx_validation_reports_model_run ON governance.validation_reports (model_run_id);
CREATE INDEX IF NOT EXISTS idx_validation_reports_type ON governance.validation_reports (report_type);
CREATE INDEX IF NOT EXISTS idx_validation_reports_created_at ON governance.validation_reports (created_at);
