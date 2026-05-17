-- DESTRUCTIVE RESET SCRIPT.
-- WARNING: This script deletes all core AML tables and all data inside them.
-- It does not drop PostgreSQL schemas.

DROP TABLE IF EXISTS aml.case_entities CASCADE;
DROP TABLE IF EXISTS aml.case_alerts CASCADE;
DROP TABLE IF EXISTS aml.case_assignments CASCADE;
DROP TABLE IF EXISTS aml.case_lifecycle_events CASCADE;
DROP TABLE IF EXISTS aml.case_explanations CASCADE;
DROP TABLE IF EXISTS aml.case_evidence_packs CASCADE;
DROP TABLE IF EXISTS aml.case_risk_scores CASCADE;
DROP TABLE IF EXISTS aml.cases CASCADE;
DROP TABLE IF EXISTS aml.alerts CASCADE;
DROP TABLE IF EXISTS governance.validation_reports CASCADE;
DROP TABLE IF EXISTS governance.model_runs CASCADE;
DROP TABLE IF EXISTS governance.audit_events CASCADE;
DROP TABLE IF EXISTS mart.account_risk_scores CASCADE;
DROP TABLE IF EXISTS mart.account_anomaly_scores CASCADE;
DROP TABLE IF EXISTS mart.graph_features CASCADE;
DROP TABLE IF EXISTS mart.features_account_daily CASCADE;
DROP TABLE IF EXISTS staging.transactions CASCADE;
DROP TABLE IF EXISTS staging.devices CASCADE;
DROP TABLE IF EXISTS staging.counterparties CASCADE;
DROP TABLE IF EXISTS staging.accounts CASCADE;
DROP TABLE IF EXISTS staging.customers CASCADE;
DROP TABLE IF EXISTS staging.countries CASCADE;
DROP TABLE IF EXISTS raw.devices_raw CASCADE;
DROP TABLE IF EXISTS raw.countries_raw CASCADE;
DROP TABLE IF EXISTS raw.counterparties_raw CASCADE;
DROP TABLE IF EXISTS raw.transactions_raw CASCADE;
DROP TABLE IF EXISTS raw.accounts_raw CASCADE;
DROP TABLE IF EXISTS raw.customers_raw CASCADE;
