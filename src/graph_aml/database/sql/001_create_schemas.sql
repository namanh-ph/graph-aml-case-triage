-- Create PostgreSQL schemas for the Graph-Based AML Case Triage project.
-- This script is idempotent and only creates schema namespaces.

CREATE SCHEMA IF NOT EXISTS raw;
COMMENT ON SCHEMA raw IS 'Unmodified source data loaded from synthetic or external AML datasets.';

CREATE SCHEMA IF NOT EXISTS staging;
COMMENT ON SCHEMA staging IS 'Cleaned, standardised, and relationally consistent operational tables.';

CREATE SCHEMA IF NOT EXISTS mart;
COMMENT ON SCHEMA mart IS 'Feature tables and analytics-ready outputs for rules, graph features, and models.';

CREATE SCHEMA IF NOT EXISTS aml;
COMMENT ON SCHEMA aml IS 'AML alerts, cases, case links, typology outputs, and investigation workflow records.';

CREATE SCHEMA IF NOT EXISTS governance;
COMMENT ON SCHEMA governance IS 'Audit events, model runs, validation reports, lineage, and reproducibility artefacts.';
