-- WARNING: This cleanup deletes only deterministic smoke seed records.
-- It does not remove schemas, table definitions, or non-smoke local data.

DELETE FROM governance.validation_reports
WHERE validation_report_id LIKE 'REPORT_SMOKE_%';

DELETE FROM aml.case_alerts
WHERE case_id LIKE 'CASE_SMOKE_%'
   OR alert_id LIKE 'ALERT_SMOKE_%';

DELETE FROM aml.case_entities
WHERE case_id LIKE 'CASE_SMOKE_%'
   OR entity_id LIKE '%SMOKE_%';

DELETE FROM aml.cases
WHERE case_id LIKE 'CASE_SMOKE_%';

DELETE FROM aml.alerts
WHERE alert_id LIKE 'ALERT_SMOKE_%';

DELETE FROM mart.account_risk_scores
WHERE account_id LIKE 'ACC_SMOKE_%';

DELETE FROM mart.account_anomaly_scores
WHERE account_id LIKE 'ACC_SMOKE_%'
   OR model_run_id LIKE '%SMOKE_%';

DELETE FROM mart.graph_features
WHERE account_id LIKE 'ACC_SMOKE_%'
   OR graph_build_version LIKE 'smoke_%';

DELETE FROM mart.features_account_daily
WHERE account_id LIKE 'ACC_SMOKE_%'
   OR feature_version LIKE 'smoke_%';

DELETE FROM staging.transactions
WHERE transaction_id LIKE 'TXN_SMOKE_%'
   OR source_file = 'smoke_seed';

DELETE FROM staging.devices
WHERE device_id LIKE 'DEV_SMOKE_%';

DELETE FROM staging.counterparties
WHERE counterparty_id LIKE 'CP_SMOKE_%';

DELETE FROM staging.accounts
WHERE account_id LIKE 'ACC_SMOKE_%';

DELETE FROM staging.customers
WHERE customer_id LIKE 'CUST_SMOKE_%';

DELETE FROM staging.countries
WHERE country_code IN ('SMOKE_US', 'SMOKE_HR')
  AND country_name IN ('United States', 'High Risk Jurisdiction');

DELETE FROM governance.model_runs
WHERE model_run_id LIKE 'MODEL_RUN_SMOKE_%';

DELETE FROM governance.audit_events
WHERE entity_id LIKE '%SMOKE_%'
   OR run_id LIKE 'RUN_SMOKE_%';
