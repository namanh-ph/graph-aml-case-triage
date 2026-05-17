# Dataset Summary

Exploratory dataset summaries profile generated or staged AML data values for data quality review,
validation evidence, feature engineering readiness, and later model validation work.

## Persisted Reference Profiling

Persisted profiling reads a versioned reference dataset through `dataset_metadata.json`. It does not
connect to PostgreSQL.

```bash
python scripts/generate_dataset_summary.py persisted --metadata-path data/<dataset_id>/<version>/dataset_metadata.json
python scripts/generate_dataset_summary.py latest --dataset-id synthetic_scenario_seed_42_scenario_42
```

## Staged PostgreSQL Profiling

Staged profiling reads clean records from PostgreSQL `staging` tables. It is read-only and does not
run raw ingestion or staging transformations automatically.

```bash
python scripts/generate_dataset_summary.py staged
python scripts/generate_dataset_summary.py staged --limit 1000
```

## Metrics Included

The summary includes:

- table row counts
- customer, account, counterparty, device, and country counts
- transaction count and timestamp range
- transaction amount distribution with percentiles
- transaction type, channel, currency, and country-pair counts
- cross-border transaction counts and ratio
- suspicious label counts and ratio
- typology counts
- scenario count, scenario typology counts, scenario transaction count, and coverage ratio
- missing-value and duplicate-key summaries
- optional validation result summary for persisted datasets

## Artefact Outputs

Generated files are written to `reports/model_validation` by default:

```text
reports/model_validation/
|-- dataset_summary.md
|-- dataset_summary.json
|-- dataset_summary.csv
```

Markdown is for human review, JSON is for deterministic governance packaging, and CSV provides a
compact key-value export for spreadsheet review.

## Makefile Usage

```bash
make generate-data-scenarios-small
make generate-dataset-summary
make generate-dataset-summary-baseline
make generate-dataset-summary-staged
```

## Limitations

This ticket produces exploratory summaries only. It does not calculate account-level features,
behavioural features, AML rules, graph structures, model scores, alerts, or cases.

Account-level feature engineering now uses the staged transactions profiled by dataset summaries to
calculate rolling counts, sent and received values, amount statistics, unique counterparties, and
in-out ratios.

Dataset summaries also support feature quality review by exposing transaction date ranges,
suspicious labels, typologies, country exposure, and transaction amount distributions before feature
artefacts are generated.
