# Raw Ingestion

Raw ingestion loads persisted reference dataset files into PostgreSQL raw tables. It is the first
database persistence step after local file generation.

## Source Dataset Layout

The loader expects a persisted dataset version with `dataset_metadata.json` and table files:

```text
data/<dataset_id>/<dataset_version>/
|-- countries.csv
|-- customers.csv
|-- accounts.csv
|-- counterparties.csv
|-- devices.csv
|-- transactions.csv
|-- dataset_summary.json
|-- dataset_metadata.json
```

Scenario-enriched datasets can also include `scenario_manifest.csv`, but that file remains a local
metadata artefact and is not loaded into PostgreSQL in this ticket.

## Metadata-Driven Loading

Ingestion resolves sources either from an explicit metadata file:

```bash
python scripts/ingest_raw.py ingest --metadata-path data/.../dataset_metadata.json
```

or from a dataset ID using `LATEST.json`:

```bash
python scripts/ingest_raw.py ingest-latest --dataset-id synthetic_scenario_seed_42_scenario_42
```

## Raw Table Mapping

| Dataset file | Raw table |
| --- | --- |
| `countries` | `raw.countries_raw` |
| `customers` | `raw.customers_raw` |
| `accounts` | `raw.accounts_raw` |
| `counterparties` | `raw.counterparties_raw` |
| `devices` | `raw.devices_raw` |
| `transactions` | `raw.transactions_raw` |

## Raw Payload Design

Each source row is stored as `raw_payload` JSONB. Common raw fields are:

- `source_system`
- `source_file`
- `raw_payload`
- `record_hash`

`raw.transactions_raw` also receives:

- `transaction_id`
- `sender_account_id`
- `receiver_account_id`
- `transaction_timestamp`
- `amount`
- `currency`

## Record Hash Design

`record_hash` is a SHA-256 digest of the sorted JSON payload. The hash is deterministic for the same
source row and supports later deduplication and lineage checks. This ticket does not deduplicate;
repeated ingestion appends records.

## Audit Events

By default, ingestion writes one `governance.audit_events` row with:

- `event_type`: `raw_ingestion`
- `component`: `ingestion`
- `action`: `load_persisted_dataset_to_raw`
- `details`: dataset ID, dataset version, source file, and row counts

Use `--no-audit` to skip audit writing for local diagnostics.

## Makefile Usage

```bash
make services-up
make db-reset
make generate-data-scenarios-small
make load-data-scenarios
```

Baseline ingestion:

```bash
make generate-data-small
make load-data-baseline
```

## Validation Before Ingestion

Persisted reference datasets can be validated before loading raw tables:

```bash
make validate-data-strict
make load-data-scenarios
```

Validation checks Pandera table schemas and cross-table integrity. A recommended workflow is to run
strict validation first, review any artefacts under `reports/validation_failures`, and then load the
scenario dataset only after validation is clean or accepted for local diagnostics.

## Transforming Raw Records To Staging

After raw ingestion, records can be transformed into clean relational staging tables:

```bash
make stage-data
```

The staging pipeline expands `raw_payload` JSONB records, normalises typed fields, validates the
transformed frames, upserts into `staging` tables, and writes a governance audit event.

## Limitations

Raw ingestion does not initialise, reset, or seed the database automatically. It does not perform
AML rules, graph construction, model training, scoring, or case generation. Staging transformations
are now handled by `make stage-data`.
