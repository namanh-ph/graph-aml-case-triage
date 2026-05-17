# Data Dictionary

The data dictionary is a generated governance and model validation artefact for the Graph-Based AML
Case Triage project. It documents source fields, transformed fields, business meanings, data types,
validation rules, lineage, and assumptions across the project data model.

## Source Metadata

The generator uses:

- typed project configuration for project name and version
- PostgreSQL schema metadata from `graph_aml.database.schemas`
- PostgreSQL table metadata from `graph_aml.database.tables`
- curated column definitions based on the SQL DDL
- curated validation rules, lineage notes, examples, and business descriptions

It does not connect to PostgreSQL or inspect live database metadata.

## Table Coverage

The dictionary covers:

- `raw`: source capture tables with JSONB payloads and lineage columns
- `staging`: cleaned and standardised relational tables
- `mart`: account feature and graph feature tables
- `aml`: alert, case, case-alert, and case-entity workflow tables
- `governance`: audit events, model runs, and validation reports

## Column Definition Fields

Each column definition includes:

- column name
- data type
- nullable flag
- primary key flag
- foreign key reference
- description
- business meaning
- validation rules
- example value
- lineage source

## Artefacts

The generator writes three artefacts:

```text
reports/model_validation/
|-- feature_dictionary.md
|-- data_dictionary.json
|-- data_dictionary.csv
```

The Markdown file is intended for human review. The JSON file is deterministic and suitable for
governance packaging. The CSV file has one row per column and is suitable for spreadsheet review.

## CLI Usage

```bash
python scripts/generate_data_dictionary.py generate
python scripts/generate_data_dictionary.py generate --output-dir reports/model_validation
```

## Makefile Usage

```bash
make generate-data-dictionary
```

## Governance Relationship

The data dictionary supports validation, staging review, feature engineering, model risk governance,
AML rule transparency, and auditability by making field meaning and lineage explicit before later
analytics tickets add features, rules, graph construction, models, scoring, and cases.

## Limitations

This artefact documents the schema and model contract. It does not produce exploratory dataset
summaries, account feature calculations, AML rules, graph analytics, model training, scoring, or case
generation.

Dataset summary artefacts now complement the data dictionary by profiling actual generated or staged
data values, including counts, distributions, labels, scenario coverage, and data quality metrics.

The initial account-level feature engineering layer calculates the first subset of
`mart.features_account_daily`: rolling counts, sent and received values, amount statistics, unique
counterparties, and in-out ratios. Mart table persistence is implemented in a later ticket.

The extended account feature set now covers the full non-graph behavioural subset of
`mart.features_account_daily`, including retained balance proxy, below-threshold counts, dormant
days, cross-border ratio, high-risk country exposure, and counterparty entropy.

`mart.features_account_daily` is now populated by the feature persistence workflow. The persisted
columns should remain aligned with the generated data dictionary and the upsert key
`account_id, feature_date, feature_version`.

The common alert schema is aligned with the `aml.alerts` table documented in the data dictionary.
Future rule engines should emit records that match those documented fields before persistence.
