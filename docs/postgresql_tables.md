# PostgreSQL Tables

The core PostgreSQL model defines raw source tables, staging operational tables, mart feature tables, AML alert and case tables, and governance artefact tables. This ticket creates SQL artefacts only; execution utilities are added later.

| Schema | Table | Purpose |
| --- | --- | --- |
| raw | `transactions_raw` | Source transaction records as JSONB payloads with traceability columns |
| raw | `customers_raw` | Source customer records as JSONB payloads |
| raw | `accounts_raw` | Source account records as JSONB payloads |
| raw | `counterparties_raw` | Source counterparty records as JSONB payloads |
| raw | `countries_raw` | Source jurisdiction reference records as JSONB payloads |
| raw | `devices_raw` | Source device and identifier records as JSONB payloads |
| staging | `transactions` | Standardised transaction records |
| staging | `customers` | Standardised customer profiles and risk attributes |
| staging | `accounts` | Standardised accounts linked to customers |
| staging | `counterparties` | Standardised external beneficiaries, merchants, and institutions |
| staging | `countries` | Standardised jurisdiction metadata and risk flags |
| staging | `devices` | Standardised device, IP, phone, and browser identifiers |
| mart | `features_account_daily` | Account-level behavioural features |
| mart | `graph_features` | Account-level graph analytics features |
| aml | `alerts` | Rule-generated and model-generated alerts |
| aml | `cases` | Grouped investigation cases |
| aml | `case_alerts` | Alert-to-case bridge records |
| aml | `case_entities` | Case-linked accounts, customers, counterparties, and other entities |
| governance | `audit_events` | Runtime and governance audit events |
| governance | `model_runs` | Model run parameters, metrics, and artefact references |
| governance | `validation_reports` | Validation report metadata and model run links |

## Data Flow

Raw tables preserve source payloads and lineage. Staging tables hold cleaned operational entities and transactions. Mart tables store features generated from staging data and graph analytics. AML tables store alerts, cases, and investigation links. Governance tables store audit events, model run metadata, and validation report metadata.

## Keys and Relationships

Staging entity tables use text primary keys from source or generated canonical IDs. `staging.accounts` references `staging.customers`. `staging.transactions` references sender and receiver accounts, counterparties, devices, and countries. Mart tables reference `staging.accounts`. AML alerts and cases reference staging accounts and customers. `aml.case_alerts` links cases and alerts. `governance.validation_reports` can reference `governance.model_runs`.

## Later Tickets

Later build tickets will execute these SQL files, add database connection utilities, load reference data, generate features, run AML rules, generate cases, and persist governance records.
