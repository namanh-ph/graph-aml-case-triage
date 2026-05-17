# Data Dictionary

## Project Overview

- Project: graph-aml-case-triage
- Dictionary version: 1.0
- Generated at: 2026-05-03T23:46:28.575678+00:00
- Source metadata: database schema metadata, SQL table metadata, validation rules, and curated business descriptions.

## Schema Overview

| Schema | Lifecycle stage | Description |
| --- | --- | --- |
| raw | Raw source capture | Unmodified source data loaded from reference or external AML datasets. |
| staging | Cleaned and standardised relational data | Cleaned, standardised, and relationally consistent operational tables. |
| mart | Analytics-ready feature data | Feature tables and analytics-ready outputs for rules, graph features, and models. |
| aml | AML alert, case, and investigation workflow data | AML alerts, cases, case links, typology outputs, and investigation workflow records. |
| governance | Audit, model run, validation, and lineage artefacts | Audit events, model runs, validation reports, lineage, and reproducibility artefacts. |

## Table Index

| Table | Description |
| --- | --- |
| raw.customers_raw | Source customer records stored as JSONB payloads before standardisation. |
| raw.accounts_raw | Source account records stored as JSONB payloads before standardisation. |
| raw.transactions_raw | Source transaction records with traceability columns and raw JSONB. |
| raw.counterparties_raw | Source counterparty records stored as JSONB payloads. |
| raw.countries_raw | Source country and jurisdiction reference records stored as JSONB. |
| raw.devices_raw | Source device and identifier records stored as JSONB payloads. |
| staging.countries | Standardised country and jurisdiction risk reference data. |
| staging.customers | Standardised customer profiles and customer risk attributes. |
| staging.accounts | Standardised account records linked to customers and jurisdictions. |
| staging.counterparties | Standardised external counterparties, merchants, and institutions. |
| staging.devices | Standardised device, IP, phone, and browser identifier records. |
| staging.transactions | Standardised transaction records linked to accounts and evidence entities. |
| mart.features_account_daily | Daily account-level behavioural features for rules and models. |
| mart.graph_features | Account-level graph analytics features from transaction networks. |
| aml.alerts | Rule-generated and model-generated AML alerts with evidence references. |
| aml.cases | Grouped AML investigation cases with composite risk scores and statuses. |
| aml.case_alerts | Bridge table linking alerts to generated investigation cases. |
| aml.case_entities | Entities linked to investigation cases with relationship metadata. |
| governance.audit_events | Runtime, pipeline, model, and analyst action audit events. |
| governance.model_runs | Model run metadata, parameters, metrics, and artefact references. |
| governance.validation_reports | Validation report metadata and links to model runs. |

## raw schema

Unmodified source data loaded from reference or external AML datasets.

### raw.customers_raw

Source customer records stored as JSONB payloads before standardisation.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| raw_record_id | BIGSERIAL | False | PK | Raw record id column for this project table. | Captures raw record id for raw.customers_raw. |  | 1 |  |
| source_system | TEXT | True |  | Source system column for this project table. | Captures source system for raw.customers_raw. |  | reference |  |
| source_file | TEXT | True |  | Source file column for this project table. | Captures source file for raw.customers_raw. |  | transactions.csv |  |
| ingested_at | TIMESTAMPTZ | False |  | Ingested at column for this project table. | Captures ingested at for raw.customers_raw. |  | 2025-01-01T12:00:00Z |  |
| raw_payload | JSONB | False |  | Original source record captured as JSONB. | Stores the original source record as JSONB for lineage and replay. | Must contain the original source record as a JSON object. | {"transaction_id": "TXN_001"} |  |
| record_hash | TEXT | True |  | Deterministic hash of the raw payload. | Supports lineage, reproducibility, integrity checks, and later deduplication. |  | sha256:... |  |

### raw.accounts_raw

Source account records stored as JSONB payloads before standardisation.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| raw_record_id | BIGSERIAL | False | PK | Raw record id column for this project table. | Captures raw record id for raw.accounts_raw. |  | 1 |  |
| source_system | TEXT | True |  | Source system column for this project table. | Captures source system for raw.accounts_raw. |  | reference |  |
| source_file | TEXT | True |  | Source file column for this project table. | Captures source file for raw.accounts_raw. |  | transactions.csv |  |
| ingested_at | TIMESTAMPTZ | False |  | Ingested at column for this project table. | Captures ingested at for raw.accounts_raw. |  | 2025-01-01T12:00:00Z |  |
| raw_payload | JSONB | False |  | Original source record captured as JSONB. | Stores the original source record as JSONB for lineage and replay. | Must contain the original source record as a JSON object. | {"transaction_id": "TXN_001"} |  |
| record_hash | TEXT | True |  | Deterministic hash of the raw payload. | Supports lineage, reproducibility, integrity checks, and later deduplication. |  | sha256:... |  |

### raw.transactions_raw

Source transaction records with traceability columns and raw JSONB.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| raw_record_id | BIGSERIAL | False | PK | Raw record id column for this project table. | Captures raw record id for raw.transactions_raw. |  | 1 |  |
| source_system | TEXT | True |  | Source system column for this project table. | Captures source system for raw.transactions_raw. |  | reference |  |
| source_file | TEXT | True |  | Source file column for this project table. | Captures source file for raw.transactions_raw. |  | transactions.csv |  |
| ingested_at | TIMESTAMPTZ | False |  | Ingested at column for this project table. | Captures ingested at for raw.transactions_raw. |  | 2025-01-01T12:00:00Z |  |
| raw_payload | JSONB | False |  | Original source record captured as JSONB. | Stores the original source record as JSONB for lineage and replay. | Must contain the original source record as a JSON object. | {"transaction_id": "TXN_001"} |  |
| record_hash | TEXT | True |  | Deterministic hash of the raw payload. | Supports lineage, reproducibility, integrity checks, and later deduplication. |  | sha256:... |  |
| transaction_id | TEXT | True |  | Transaction id column for this project table. | Source transaction identifier used to trace payment activity. |  | TXN_001 | raw_payload |
| sender_account_id | TEXT | True |  | Sender account id column for this project table. | Standardised account that initiated the transaction. |  | ACC_001 | raw_payload |
| receiver_account_id | TEXT | True |  | Receiver account id column for this project table. | Standardised internal account that received the transaction when present. |  | ACC_002 | raw_payload |
| transaction_timestamp | TIMESTAMPTZ | True |  | Transaction timestamp column for this project table. | Parsed event time used for temporal rules and feature windows. |  | 2025-01-01T12:00:00Z | raw_payload |
| amount | NUMERIC(18, 2) | True |  | Amount column for this project table. | Positive monetary transaction amount used by rules, features, and scoring. |  | 125.50 | raw_payload |
| currency | TEXT | True |  | Currency column for this project table. | Normalised currency code for transaction and account consistency. |  | USD | raw_payload |

### raw.counterparties_raw

Source counterparty records stored as JSONB payloads.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| raw_record_id | BIGSERIAL | False | PK | Raw record id column for this project table. | Captures raw record id for raw.counterparties_raw. |  | 1 |  |
| source_system | TEXT | True |  | Source system column for this project table. | Captures source system for raw.counterparties_raw. |  | reference |  |
| source_file | TEXT | True |  | Source file column for this project table. | Captures source file for raw.counterparties_raw. |  | transactions.csv |  |
| ingested_at | TIMESTAMPTZ | False |  | Ingested at column for this project table. | Captures ingested at for raw.counterparties_raw. |  | 2025-01-01T12:00:00Z |  |
| raw_payload | JSONB | False |  | Original source record captured as JSONB. | Stores the original source record as JSONB for lineage and replay. | Must contain the original source record as a JSON object. | {"transaction_id": "TXN_001"} |  |
| record_hash | TEXT | True |  | Deterministic hash of the raw payload. | Supports lineage, reproducibility, integrity checks, and later deduplication. |  | sha256:... |  |

### raw.countries_raw

Source country and jurisdiction reference records stored as JSONB.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| raw_record_id | BIGSERIAL | False | PK | Raw record id column for this project table. | Captures raw record id for raw.countries_raw. |  | 1 |  |
| source_system | TEXT | True |  | Source system column for this project table. | Captures source system for raw.countries_raw. |  | reference |  |
| source_file | TEXT | True |  | Source file column for this project table. | Captures source file for raw.countries_raw. |  | transactions.csv |  |
| ingested_at | TIMESTAMPTZ | False |  | Ingested at column for this project table. | Captures ingested at for raw.countries_raw. |  | 2025-01-01T12:00:00Z |  |
| raw_payload | JSONB | False |  | Original source record captured as JSONB. | Stores the original source record as JSONB for lineage and replay. | Must contain the original source record as a JSON object. | {"transaction_id": "TXN_001"} |  |
| record_hash | TEXT | True |  | Deterministic hash of the raw payload. | Supports lineage, reproducibility, integrity checks, and later deduplication. |  | sha256:... |  |

### raw.devices_raw

Source device and identifier records stored as JSONB payloads.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| raw_record_id | BIGSERIAL | False | PK | Raw record id column for this project table. | Captures raw record id for raw.devices_raw. |  | 1 |  |
| source_system | TEXT | True |  | Source system column for this project table. | Captures source system for raw.devices_raw. |  | reference |  |
| source_file | TEXT | True |  | Source file column for this project table. | Captures source file for raw.devices_raw. |  | transactions.csv |  |
| ingested_at | TIMESTAMPTZ | False |  | Ingested at column for this project table. | Captures ingested at for raw.devices_raw. |  | 2025-01-01T12:00:00Z |  |
| raw_payload | JSONB | False |  | Original source record captured as JSONB. | Stores the original source record as JSONB for lineage and replay. | Must contain the original source record as a JSON object. | {"transaction_id": "TXN_001"} |  |
| record_hash | TEXT | True |  | Deterministic hash of the raw payload. | Supports lineage, reproducibility, integrity checks, and later deduplication. |  | sha256:... |  |

## staging schema

Cleaned, standardised, and relationally consistent operational tables.

### staging.countries

Standardised country and jurisdiction risk reference data.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| country_code | TEXT | False | PK | Country code column for this project table. | Normalised country code used for jurisdiction and cross-border analysis. |  | AU | raw.countries_raw.raw_payload |
| country_name | TEXT | False |  | Country name column for this project table. | Captures country name for staging.countries. |  | Australia | raw.countries_raw.raw_payload |
| region | TEXT | True |  | Region column for this project table. | Captures region for staging.countries. |  | APAC | raw.countries_raw.raw_payload |
| is_high_risk | BOOLEAN | False |  | Is high risk column for this project table. | Captures is high risk for staging.countries. | Defaults to false. | false | raw.countries_raw.raw_payload |
| risk_score | NUMERIC(5, 2) | False |  | Risk score column for this project table. | Captures risk score for staging.countries. | Must be between 0 and 100. | 25.00 | raw.countries_raw.raw_payload |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for staging.countries. |  | 2025-01-01T12:00:00Z |  |
| updated_at | TIMESTAMPTZ | False |  | Updated at column for this project table. | Captures updated at for staging.countries. |  | 2025-01-01T12:00:00Z |  |

### staging.customers

Standardised customer profiles and customer risk attributes.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| customer_id | TEXT | False | PK | Customer id column for this project table. | Captures customer id for staging.customers. |  | CUST_001 | raw.customers_raw.raw_payload |
| customer_type | TEXT | False |  | Customer type column for this project table. | Captures customer type for staging.customers. | Lowercase standardised type. | individual | raw.customers_raw.raw_payload |
| customer_segment | TEXT | True |  | Customer segment column for this project table. | Captures customer segment for staging.customers. |  | retail | raw.customers_raw.raw_payload |
| jurisdiction | TEXT | True | FK -> staging.countries(country_code) | Jurisdiction column for this project table. | Captures jurisdiction for staging.customers. |  | AU | raw.customers_raw.raw_payload |
| occupation | TEXT | True |  | Occupation column for this project table. | Captures occupation for staging.customers. |  | engineer | raw.customers_raw.raw_payload |
| industry_code | TEXT | True |  | Industry code column for this project table. | Captures industry code for staging.customers. |  | 5411 | raw.customers_raw.raw_payload |
| customer_risk_rating | TEXT | True |  | Customer risk rating column for this project table. | Captures customer risk rating for staging.customers. | Defaults to low when missing. | medium | raw.customers_raw.raw_payload |
| customer_risk_score | NUMERIC(5, 2) | False |  | Customer risk score column for this project table. | Captures customer risk score for staging.customers. | Must be between 0 and 100. | 42.00 | raw.customers_raw.raw_payload |
| onboarded_at | TIMESTAMPTZ | True |  | Onboarded at column for this project table. | Captures onboarded at for staging.customers. | Parsed as timestamp when supplied. | 2024-12-01T00:00:00Z | raw.customers_raw.raw_payload |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for staging.customers. |  | 2025-01-01T12:00:00Z |  |
| updated_at | TIMESTAMPTZ | False |  | Updated at column for this project table. | Captures updated at for staging.customers. |  | 2025-01-01T12:00:00Z |  |

### staging.accounts

Standardised account records linked to customers and jurisdictions.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| account_id | TEXT | False | PK | Account id column for this project table. | Captures account id for staging.accounts. |  | ACC_001 | raw.accounts_raw.raw_payload |
| customer_id | TEXT | False | FK -> staging.customers(customer_id) | Customer id column for this project table. | Captures customer id for staging.accounts. |  | CUST_001 | raw.accounts_raw.raw_payload |
| account_type | TEXT | False |  | Account type column for this project table. | Captures account type for staging.accounts. |  | current | raw.accounts_raw.raw_payload |
| account_status | TEXT | False |  | Account status column for this project table. | Captures account status for staging.accounts. | Defaults to active when missing. | active | raw.accounts_raw.raw_payload |
| currency | TEXT | False |  | Currency column for this project table. | Normalised currency code for transaction and account consistency. | Uppercase ISO-like currency code. | USD | raw.accounts_raw.raw_payload |
| opened_at | TIMESTAMPTZ | True |  | Opened at column for this project table. | Captures opened at for staging.accounts. | Parsed as timestamp when supplied. | 2024-01-01T00:00:00Z | raw.accounts_raw.raw_payload |
| closed_at | TIMESTAMPTZ | True |  | Closed at column for this project table. | Captures closed at for staging.accounts. |  | 2025-01-01T00:00:00Z | raw.accounts_raw.raw_payload |
| home_country | TEXT | True | FK -> staging.countries(country_code) | Home country column for this project table. | Captures home country for staging.accounts. |  | AU | raw.accounts_raw.raw_payload |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for staging.accounts. |  | 2025-01-01T12:00:00Z |  |
| updated_at | TIMESTAMPTZ | False |  | Updated at column for this project table. | Captures updated at for staging.accounts. |  | 2025-01-01T12:00:00Z |  |

### staging.counterparties

Standardised external counterparties, merchants, and institutions.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| counterparty_id | TEXT | False | PK | Counterparty id column for this project table. | Captures counterparty id for staging.counterparties. |  | CP_001 | raw.counterparties_raw.raw_payload |
| counterparty_type | TEXT | False |  | Counterparty type column for this project table. | Captures counterparty type for staging.counterparties. |  | merchant | raw.counterparties_raw.raw_payload |
| counterparty_name | TEXT | True |  | Counterparty name column for this project table. | Captures counterparty name for staging.counterparties. |  | Example Merchant | raw.counterparties_raw.raw_payload |
| country_code | TEXT | True | FK -> staging.countries(country_code) | Country code column for this project table. | Normalised country code used for jurisdiction and cross-border analysis. |  | NZ | raw.counterparties_raw.raw_payload |
| institution_name | TEXT | True |  | Institution name column for this project table. | Captures institution name for staging.counterparties. |  | Example Bank | raw.counterparties_raw.raw_payload |
| external_account_ref | TEXT | True |  | External account ref column for this project table. | Captures external account ref for staging.counterparties. |  | EXT-001 | raw.counterparties_raw.raw_payload |
| risk_score | NUMERIC(5, 2) | False |  | Risk score column for this project table. | Captures risk score for staging.counterparties. | Must be between 0 and 100. | 35.00 | raw.counterparties_raw.raw_payload |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for staging.counterparties. |  | 2025-01-01T12:00:00Z |  |
| updated_at | TIMESTAMPTZ | False |  | Updated at column for this project table. | Captures updated at for staging.counterparties. |  | 2025-01-01T12:00:00Z |  |

### staging.devices

Standardised device, IP, phone, and browser identifier records.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| device_id | TEXT | False | PK | Device id column for this project table. | Captures device id for staging.devices. |  | DEV_001 | raw.devices_raw.raw_payload |
| device_type | TEXT | True |  | Device type column for this project table. | Captures device type for staging.devices. |  | mobile | raw.devices_raw.raw_payload |
| ip_address | TEXT | True |  | Ip address column for this project table. | Captures ip address for staging.devices. |  | 203.0.113.10 | raw.devices_raw.raw_payload |
| ip_cluster | TEXT | True |  | Ip cluster column for this project table. | Captures ip cluster for staging.devices. |  | 203.0.113.0/24 | raw.devices_raw.raw_payload |
| phone_hash | TEXT | True |  | Phone hash column for this project table. | Captures phone hash for staging.devices. |  | hash-phone | raw.devices_raw.raw_payload |
| browser_fingerprint | TEXT | True |  | Browser fingerprint column for this project table. | Captures browser fingerprint for staging.devices. |  | browser-hash | raw.devices_raw.raw_payload |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for staging.devices. |  | 2025-01-01T12:00:00Z |  |
| updated_at | TIMESTAMPTZ | False |  | Updated at column for this project table. | Captures updated at for staging.devices. |  | 2025-01-01T12:00:00Z |  |

### staging.transactions

Standardised transaction records linked to accounts and evidence entities.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| transaction_id | TEXT | False | PK | Transaction id column for this project table. | Source transaction identifier used to trace payment activity. |  | TXN_001 | raw.transactions_raw.raw_payload |
| sender_account_id | TEXT | False | FK -> staging.accounts(account_id) | Sender account id column for this project table. | Standardised account that initiated the transaction. |  | ACC_001 | raw.transactions_raw.raw_payload |
| receiver_account_id | TEXT | True | FK -> staging.accounts(account_id) | Receiver account id column for this project table. | Standardised internal account that received the transaction when present. |  | ACC_002 | raw.transactions_raw.raw_payload |
| counterparty_id | TEXT | True | FK -> staging.counterparties(counterparty_id) | Counterparty id column for this project table. | Captures counterparty id for staging.transactions. |  | CP_001 | raw.transactions_raw.raw_payload |
| device_id | TEXT | True | FK -> staging.devices(device_id) | Device id column for this project table. | Captures device id for staging.transactions. |  | DEV_001 | raw.transactions_raw.raw_payload |
| transaction_timestamp | TIMESTAMPTZ | False |  | Transaction timestamp column for this project table. | Parsed event time used for temporal rules and feature windows. | Parsed timestamp; must be populated. | 2025-01-01T12:00:00Z | raw.transactions_raw.raw_payload |
| amount | NUMERIC(18, 2) | False |  | Amount column for this project table. | Positive monetary transaction amount used by rules, features, and scoring. | Must be greater than 0. | 125.50 | raw.transactions_raw.raw_payload |
| currency | TEXT | False |  | Currency column for this project table. | Normalised currency code for transaction and account consistency. | Uppercase currency code; defaults to USD. | USD | raw.transactions_raw.raw_payload |
| transaction_type | TEXT | False |  | Transaction type column for this project table. | Captures transaction type for staging.transactions. |  | transfer | raw.transactions_raw.raw_payload |
| channel | TEXT | True |  | Channel column for this project table. | Captures channel for staging.transactions. |  | online | raw.transactions_raw.raw_payload |
| origin_country | TEXT | True | FK -> staging.countries(country_code) | Origin country column for this project table. | Captures origin country for staging.transactions. |  | AU | raw.transactions_raw.raw_payload |
| destination_country | TEXT | True | FK -> staging.countries(country_code) | Destination country column for this project table. | Captures destination country for staging.transactions. |  | NZ | raw.transactions_raw.raw_payload |
| is_cross_border | BOOLEAN | False |  | Is cross border column for this project table. | Flag recalculated from origin and destination countries for cross-border typologies. | Recalculated as origin_country != destination_country. | true | derived from staging.transactions origin and destination |
| is_labelled_suspicious | BOOLEAN | True |  | Is labelled suspicious column for this project table. | Labelled scenario label used for validation, rules, and later model evaluation. | Labelled scenario label when supplied. | false | raw.transactions_raw.raw_payload |
| typology_label | TEXT | True |  | Typology label column for this project table. | Suspicious activity typology label from labelled scenario injection. |  | structuring | raw.transactions_raw.raw_payload |
| source_file | TEXT | True |  | Source file column for this project table. | Captures source file for staging.transactions. |  | transactions.csv | raw.transactions_raw.source_file or raw_payload |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for staging.transactions. |  | 2025-01-01T12:00:00Z |  |

## mart schema

Feature tables and analytics-ready outputs for rules, graph features, and models.

### mart.features_account_daily

Daily account-level behavioural features for rules and models.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| feature_id | BIGSERIAL | False | PK | Feature id column for this project table. | Captures feature id for mart.features_account_daily. |  | 1 |  |
| account_id | TEXT | False | FK -> staging.accounts(account_id) | Account id column for this project table. | Captures account id for mart.features_account_daily. |  | ACC_001 |  |
| feature_date | DATE | False |  | Feature date column for this project table. | Captures feature date for mart.features_account_daily. |  | 2025-01-01 |  |
| feature_version | TEXT | False |  | Feature version column for this project table. | Captures feature version for mart.features_account_daily. | Unique with account_id and feature_date. | features_v1 |  |
| txn_count_1d | INTEGER | False |  | Txn count 1d column for this project table. | Captures txn count 1d for mart.features_account_daily. |  | 3 |  |
| txn_count_7d | INTEGER | False |  | Txn count 7d column for this project table. | Captures txn count 7d for mart.features_account_daily. |  | 12 |  |
| total_sent_7d | NUMERIC(18, 2) | False |  | Total sent 7d column for this project table. | Captures total sent 7d for mart.features_account_daily. |  | 1500.00 |  |
| total_received_7d | NUMERIC(18, 2) | False |  | Total received 7d column for this project table. | Captures total received 7d for mart.features_account_daily. |  | 900.00 |  |
| avg_txn_amount_30d | NUMERIC(18, 2) | False |  | Avg txn amount 30d column for this project table. | Captures avg txn amount 30d for mart.features_account_daily. |  | 125.00 |  |
| max_txn_amount_30d | NUMERIC(18, 2) | False |  | Max txn amount 30d column for this project table. | Captures max txn amount 30d for mart.features_account_daily. |  | 999.00 |  |
| unique_counterparties_7d | INTEGER | False |  | Unique counterparties 7d column for this project table. | Captures unique counterparties 7d for mart.features_account_daily. |  | 5 |  |
| in_out_ratio_7d | NUMERIC(18, 6) | True |  | In out ratio 7d column for this project table. | Captures in out ratio 7d for mart.features_account_daily. |  | 1.250000 |  |
| retained_balance_proxy | NUMERIC(18, 2) | True |  | Retained balance proxy column for this project table. | Captures retained balance proxy for mart.features_account_daily. |  | 600.00 |  |
| below_threshold_count_24h | INTEGER | False |  | Below threshold count 24h column for this project table. | Captures below threshold count 24h for mart.features_account_daily. |  | 4 |  |
| dormant_days_before_activity | INTEGER | True |  | Dormant days before activity column for this project table. | Captures dormant days before activity for mart.features_account_daily. |  | 120 |  |
| cross_border_ratio_30d | NUMERIC(10, 6) | True |  | Cross border ratio 30d column for this project table. | Captures cross border ratio 30d for mart.features_account_daily. |  | 0.150000 |  |
| high_risk_country_exposure | NUMERIC(10, 6) | True |  | High risk country exposure column for this project table. | Captures high risk country exposure for mart.features_account_daily. |  | 0.050000 |  |
| counterparty_entropy | NUMERIC(10, 6) | True |  | Counterparty entropy column for this project table. | Captures counterparty entropy for mart.features_account_daily. |  | 1.500000 |  |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for mart.features_account_daily. |  | 2025-01-01T12:00:00Z |  |

### mart.graph_features

Account-level graph analytics features from transaction networks.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| graph_feature_id | BIGSERIAL | False | PK | Graph feature id column for this project table. | Captures graph feature id for mart.graph_features. |  | 1 |  |
| account_id | TEXT | False | FK -> staging.accounts(account_id) | Account id column for this project table. | Captures account id for mart.graph_features. |  | ACC_001 |  |
| graph_build_version | TEXT | False |  | Graph build version column for this project table. | Captures graph build version for mart.graph_features. | Unique with account_id and feature_date. | graph_v1 |  |
| feature_date | DATE | False |  | Feature date column for this project table. | Captures feature date for mart.graph_features. |  | 2025-01-01 |  |
| degree_centrality | NUMERIC(18, 10) | True |  | Degree centrality column for this project table. | Captures degree centrality for mart.graph_features. |  | 0.1200000000 |  |
| in_degree | INTEGER | True |  | In degree column for this project table. | Captures in degree for mart.graph_features. |  | 5 |  |
| out_degree | INTEGER | True |  | Out degree column for this project table. | Captures out degree for mart.graph_features. |  | 4 |  |
| pagerank_score | NUMERIC(18, 10) | True |  | Pagerank score column for this project table. | Captures pagerank score for mart.graph_features. |  | 0.0012000000 |  |
| betweenness_centrality | NUMERIC(18, 10) | True |  | Betweenness centrality column for this project table. | Captures betweenness centrality for mart.graph_features. |  | 0.0300000000 |  |
| clustering_coefficient | NUMERIC(18, 10) | True |  | Clustering coefficient column for this project table. | Captures clustering coefficient for mart.graph_features. |  | 0.5000000000 |  |
| community_id | TEXT | True |  | Community id column for this project table. | Captures community id for mart.graph_features. |  | COMM_001 |  |
| community_size | INTEGER | True |  | Community size column for this project table. | Captures community size for mart.graph_features. |  | 10 |  |
| cycle_count | INTEGER | False |  | Cycle count column for this project table. | Captures cycle count for mart.graph_features. |  | 1 |  |
| shortest_path_to_flagged | INTEGER | True |  | Shortest path to flagged column for this project table. | Captures shortest path to flagged for mart.graph_features. |  | 2 |  |
| shared_device_count | INTEGER | False |  | Shared device count column for this project table. | Captures shared device count for mart.graph_features. |  | 3 |  |
| fan_in_count | INTEGER | False |  | Fan in count column for this project table. | Captures fan in count for mart.graph_features. |  | 4 |  |
| fan_out_count | INTEGER | False |  | Fan out count column for this project table. | Captures fan out count for mart.graph_features. |  | 5 |  |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for mart.graph_features. |  | 2025-01-01T12:00:00Z |  |

## aml schema

AML alerts, cases, case links, typology outputs, and investigation workflow records.

### aml.alerts

Rule-generated and model-generated AML alerts with evidence references.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| alert_id | TEXT | False | PK | Alert id column for this project table. | Captures alert id for aml.alerts. |  | ALERT_001 |  |
| account_id | TEXT | False | FK -> staging.accounts(account_id) | Account id column for this project table. | Captures account id for aml.alerts. |  | ACC_001 |  |
| customer_id | TEXT | True | FK -> staging.customers(customer_id) | Customer id column for this project table. | Captures customer id for aml.alerts. |  | CUST_001 |  |
| rule_name | TEXT | False |  | Rule name column for this project table. | Captures rule name for aml.alerts. |  | Structuring |  |
| typology | TEXT | False |  | Typology column for this project table. | Captures typology for aml.alerts. |  | structuring |  |
| severity | TEXT | False |  | Severity column for this project table. | Captures severity for aml.alerts. | Must be low, medium, high, or critical. | high |  |
| risk_score_rule | NUMERIC(5, 2) | False |  | Risk score rule column for this project table. | Captures risk score rule for aml.alerts. | Must be between 0 and 100. | 85.00 |  |
| reason_code | TEXT | False |  | Explanation code for why a rule or model created an alert. | Human-readable reason supporting alert transparency and review. |  | STRUCTURING_BELOW_THRESHOLD |  |
| evidence_ids | TEXT[] | False |  | Supporting transaction or entity identifiers for an alert. | Links an alert to supporting transactions or entities. |  | {TXN_001,TXN_002} |  |
| detection_window_start | TIMESTAMPTZ | True |  | Detection window start column for this project table. | Captures detection window start for aml.alerts. |  | 2025-01-01T00:00:00Z |  |
| detection_window_end | TIMESTAMPTZ | True |  | Detection window end column for this project table. | Captures detection window end for aml.alerts. |  | 2025-01-02T00:00:00Z |  |
| model_run_id | TEXT | True |  | Model run id column for this project table. | Model lineage identifier shared across runs, alerts, and reports. |  | MODEL_RUN_001 |  |
| alert_status | TEXT | False |  | Alert status column for this project table. | Captures alert status for aml.alerts. |  | New |  |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for aml.alerts. |  | 2025-01-01T12:00:00Z |  |
| updated_at | TIMESTAMPTZ | False |  | Updated at column for this project table. | Captures updated at for aml.alerts. |  | 2025-01-01T12:00:00Z |  |

### aml.cases

Grouped AML investigation cases with composite risk scores and statuses.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| case_id | TEXT | False | PK | Case id column for this project table. | Captures case id for aml.cases. |  | CASE_001 |  |
| primary_account_id | TEXT | True | FK -> staging.accounts(account_id) | Primary account id column for this project table. | Captures primary account id for aml.cases. |  | ACC_001 |  |
| primary_customer_id | TEXT | True | FK -> staging.customers(customer_id) | Primary customer id column for this project table. | Captures primary customer id for aml.cases. |  | CUST_001 |  |
| typologies | TEXT[] | False |  | Typologies column for this project table. | Captures typologies for aml.cases. |  | {structuring,fan_in} |  |
| total_transaction_value | NUMERIC(18, 2) | False |  | Total transaction value column for this project table. | Captures total transaction value for aml.cases. |  | 12500.00 |  |
| rule_typology_score | NUMERIC(5, 2) | False |  | Rule typology score column for this project table. | Captures rule typology score for aml.cases. |  | 80.00 |  |
| graph_risk_score | NUMERIC(5, 2) | False |  | Graph risk score column for this project table. | Captures graph risk score for aml.cases. |  | 70.00 |  |
| anomaly_score | NUMERIC(5, 2) | False |  | Anomaly score column for this project table. | Captures anomaly score for aml.cases. |  | 65.00 |  |
| customer_risk_score | NUMERIC(5, 2) | False |  | Customer risk score column for this project table. | Captures customer risk score for aml.cases. |  | 55.00 |  |
| jurisdiction_risk_score | NUMERIC(5, 2) | False |  | Jurisdiction risk score column for this project table. | Captures jurisdiction risk score for aml.cases. |  | 40.00 |  |
| case_risk_score | NUMERIC(5, 2) | False |  | Final composite case risk score used for prioritisation. | Supports investigation prioritisation and queue ordering. | Must be between 0 and 100. | 82.00 |  |
| severity | TEXT | False |  | Severity column for this project table. | Captures severity for aml.cases. | Must be low, medium, high, or critical. | high |  |
| status | TEXT | False |  | Workflow status for human review and disposition. | Tracks the human investigation lifecycle. | Must be a recognised case workflow status. | New |  |
| explanation | TEXT | True |  | Explanation column for this project table. | Captures explanation for aml.cases. |  | Multiple typology signals on account. |  |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for aml.cases. |  | 2025-01-01T12:00:00Z |  |
| updated_at | TIMESTAMPTZ | False |  | Updated at column for this project table. | Captures updated at for aml.cases. |  | 2025-01-01T12:00:00Z |  |

### aml.case_alerts

Bridge table linking alerts to generated investigation cases.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| case_id | TEXT | False | PK, FK -> aml.cases(case_id) | Case id column for this project table. | Captures case id for aml.case_alerts. |  | CASE_001 |  |
| alert_id | TEXT | False | PK, FK -> aml.alerts(alert_id) | Alert id column for this project table. | Captures alert id for aml.case_alerts. |  | ALERT_001 |  |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for aml.case_alerts. |  | 2025-01-01T12:00:00Z |  |

### aml.case_entities

Entities linked to investigation cases with relationship metadata.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| case_entity_id | BIGSERIAL | False | PK | Case entity id column for this project table. | Captures case entity id for aml.case_entities. |  | 1 |  |
| case_id | TEXT | False | FK -> aml.cases(case_id) | Case id column for this project table. | Captures case id for aml.case_entities. |  | CASE_001 |  |
| entity_type | TEXT | False |  | Entity type column for this project table. | Captures entity type for aml.case_entities. |  | account |  |
| entity_id | TEXT | False |  | Entity id column for this project table. | Captures entity id for aml.case_entities. |  | ACC_001 |  |
| relationship_type | TEXT | True |  | Relationship type column for this project table. | Captures relationship type for aml.case_entities. |  | primary_subject |  |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for aml.case_entities. |  | 2025-01-01T12:00:00Z |  |

## governance schema

Audit events, model runs, validation reports, lineage, and reproducibility artefacts.

### governance.audit_events

Runtime, pipeline, model, and analyst action audit events.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| audit_event_id | BIGSERIAL | False | PK | Audit event id column for this project table. | Unique audit record for traceability. |  | 1 |  |
| event_timestamp | TIMESTAMPTZ | False |  | Event timestamp column for this project table. | Captures event timestamp for governance.audit_events. |  | 2025-01-01T12:00:00Z |  |
| event_type | TEXT | False |  | Event type column for this project table. | Classifies runtime, validation, staging, rule, model, or analyst events. |  | raw_ingestion |  |
| component | TEXT | False |  | Component column for this project table. | Captures component for governance.audit_events. |  | ingestion |  |
| run_id | TEXT | True |  | Run id column for this project table. | Captures run id for governance.audit_events. |  | RUN_001 |  |
| pipeline_stage | TEXT | True |  | Pipeline stage column for this project table. | Captures pipeline stage for governance.audit_events. |  | raw_load |  |
| entity_type | TEXT | True |  | Entity type column for this project table. | Captures entity type for governance.audit_events. |  | dataset |  |
| entity_id | TEXT | True |  | Entity id column for this project table. | Captures entity id for governance.audit_events. |  | synthetic_scenario_seed_42_scenario_42 |  |
| action | TEXT | False |  | Action column for this project table. | Captures action for governance.audit_events. |  | load_persisted_dataset_to_raw |  |
| status | TEXT | True |  | Workflow status for human review and disposition. | Tracks the human investigation lifecycle. |  | completed |  |
| details | JSONB | False |  | Structured JSON details for audit and governance events. | Carries structured audit details for ingestion, validation, staging, models, cases, and analyst actions. |  | {"row_counts": {"transactions": 100}} |  |
| created_by | TEXT | False |  | Created by column for this project table. | Captures created by for governance.audit_events. |  | system |  |

### governance.model_runs

Model run metadata, parameters, metrics, and artefact references.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| model_run_id | TEXT | False | PK | Model run id column for this project table. | Model lineage identifier shared across runs, alerts, and reports. |  | MODEL_RUN_001 |  |
| experiment_name | TEXT | False |  | Experiment name column for this project table. | Captures experiment name for governance.model_runs. |  | aml_risk_scoring |  |
| model_name | TEXT | False |  | Model name column for this project table. | Captures model name for governance.model_runs. |  | isolation_forest |  |
| model_version | TEXT | True |  | Model version column for this project table. | Captures model version for governance.model_runs. |  | v1 |  |
| model_type | TEXT | False |  | Model type column for this project table. | Captures model type for governance.model_runs. |  | anomaly_detection |  |
| feature_version | TEXT | True |  | Feature version column for this project table. | Captures feature version for governance.model_runs. |  | features_v1 |  |
| training_start | TIMESTAMPTZ | True |  | Training start column for this project table. | Captures training start for governance.model_runs. |  | 2025-01-01T10:00:00Z |  |
| training_end | TIMESTAMPTZ | True |  | Training end column for this project table. | Captures training end for governance.model_runs. |  | 2025-01-01T11:00:00Z |  |
| parameters | JSONB | False |  | Model training or scoring parameters captured as JSONB. | Records model lineage and reproducible training configuration. |  | {"n_estimators": 100} |  |
| metrics | JSONB | False |  | Model performance and validation metrics captured as JSONB. | Stores model risk and validation metrics. |  | {"precision_at_k": 0.8} |  |
| artefact_uri | TEXT | True |  | Artefact uri column for this project table. | Location of the persisted model or model artefact. |  | runs:/MODEL_RUN_001/model |  |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for governance.model_runs. |  | 2025-01-01T12:00:00Z |  |

### governance.validation_reports

Validation report metadata and links to model runs.

| Column | Type | Nullable | Key | Description | Business meaning | Validation rules | Example | Lineage source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| validation_report_id | TEXT | False | PK | Validation report id column for this project table. | Unique validation report artefact identifier. |  | VR_001 |  |
| report_name | TEXT | False |  | Report name column for this project table. | Captures report name for governance.validation_reports. |  | model_validation_report |  |
| report_version | TEXT | False |  | Report version column for this project table. | Captures report version for governance.validation_reports. |  | v1 |  |
| model_run_id | TEXT | True | FK -> governance.model_runs(model_run_id) | Model run id column for this project table. | Model lineage identifier shared across runs, alerts, and reports. |  | MODEL_RUN_001 |  |
| report_path | TEXT | False |  | Path to the generated validation or governance report artefact. | Captures report path for governance.validation_reports. |  | reports/model_validation/report.md |  |
| report_type | TEXT | False |  | Report type column for this project table. | Captures report type for governance.validation_reports. |  | model_validation |  |
| summary | JSONB | False |  | Summary column for this project table. | Structured summary of validation findings and report outcomes. |  | {"passed": true} |  |
| created_at | TIMESTAMPTZ | False |  | Created at column for this project table. | Captures created at for governance.validation_reports. |  | 2025-01-01T12:00:00Z |  |

## Notes and Assumptions

- The dictionary is generated from static project metadata and does not inspect a live database.
- Column business meanings are curated for governance and model validation review.
- Staging lineage points back to raw payload fields where transformations currently source the values.
- Exploratory dataset summaries are intentionally out of scope for this artefact.
