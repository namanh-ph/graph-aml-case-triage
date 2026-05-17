# PostgreSQL Schemas

The PostgreSQL layer is organised into five schemas.

Schema namespace SQL is defined in `001_create_schemas.sql` and `002_drop_schemas.sql`. Core table SQL is defined in `003_create_core_tables.sql` and `004_drop_core_tables.sql`.

SQL execution will be handled by database utilities in a later ticket.

## raw

Purpose: Store unmodified source data loaded from reference or external AML datasets.

Expected future tables:

- `transactions_raw`
- `customers_raw`
- `accounts_raw`
- `counterparties_raw`
- `countries_raw`
- `devices_raw`

Lifecycle ownership: initial ingestion and data lineage capture.

Examples: original transaction extracts, source customer records, raw account files, and unmodified reference data.

Later tickets will add ingestion commands and raw data validation checks.

## staging

Purpose: Store cleaned, standardised, and relationally consistent operational tables.

Expected future tables:

- `transactions`
- `customers`
- `accounts`
- `counterparties`
- `countries`
- `devices`

Lifecycle ownership: data standardisation and relational consistency.

Examples: typed timestamps, normalised currencies, canonical account IDs, and validated customer records.

Later tickets will add transformations from `raw`.

## mart

Purpose: Store feature tables and analytics-ready outputs for rules, graph features, and models.

Expected future tables:

- `features_account_daily`
- `graph_features`

Lifecycle ownership: feature engineering and analytics preparation.

Examples: rolling account features, graph centrality outputs, community features, and model-ready feature snapshots.

Later tickets will add batch feature generation utilities.

## aml

Purpose: Store AML alerts, cases, case links, typology outputs, and investigation workflow records.

Expected future tables:

- `alerts`
- `cases`
- `case_alerts`
- `case_entities`

Lifecycle ownership: rule outputs, case generation, and investigation workflow state.

Examples: structuring alerts, fan-in/fan-out alerts, case risk scores, linked evidence IDs, and case status values.

Later tickets will add case generation logic.

## governance

Purpose: Store audit events, model runs, validation reports, lineage, and reproducibility artefacts.

Expected future tables:

- `audit_events`
- `model_runs`
- `validation_reports`

Lifecycle ownership: auditability, validation evidence, model-risk controls, and reproducibility metadata.

Examples: pipeline run records, model parameter snapshots, validation report references, and analyst decision audit entries.

Later tickets will add links from runtime logs to persistent audit events.
