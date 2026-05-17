# Staging Transformations

Staging transformations convert PostgreSQL `raw` schema records into clean relational records in the
`staging` schema. Raw records keep full source rows in `raw_payload` JSONB; staging expands those
payloads into typed columns that later AML rules, graph construction, features, and dashboards can
consume.

## Raw-To-Staging Flow

1. Read raw records from PostgreSQL raw tables.
2. Expand each `raw_payload` JSON object into a pandas DataFrame.
3. Preserve useful lineage fields such as `raw_record_id`, `source_system`, `source_file`,
   `ingested_at`, and `record_hash` during transformation.
4. Normalise IDs, timestamps, country codes, currencies, booleans, numeric fields, and nullable
   strings.
5. Deduplicate records by staging primary key, keeping the latest raw record where lineage is
   available.
6. Validate transformed frames before loading.
7. Upsert records into staging tables.
8. Write a governance audit event.

## Table Mapping

| Raw table | Staging table |
| --- | --- |
| `raw.countries_raw` | `staging.countries` |
| `raw.customers_raw` | `staging.customers` |
| `raw.accounts_raw` | `staging.accounts` |
| `raw.counterparties_raw` | `staging.counterparties` |
| `raw.devices_raw` | `staging.devices` |
| `raw.transactions_raw` | `staging.transactions` |

## Field Normalisation Rules

- Empty strings, `nan`, `None`, `null`, pandas missing values, and `NaT` become nulls.
- Identifiers are stripped, whitespace-normalised, and uppercased.
- Country codes and currencies are uppercased.
- Booleans support Python booleans, numeric values, and strings such as `true`, `false`, `1`, `0`,
  `yes`, and `no`.
- Numeric values are parsed with pandas numeric parsing.
- Timestamps are parsed as UTC pandas timestamps.
- Risk scores are clipped to `0` through `100`.
- Transaction `is_cross_border` is recalculated from origin and destination country codes.

## Deduplication Rules

Each staging transformation deduplicates by the target primary key:

- `country_code`
- `customer_id`
- `account_id`
- `counterparty_id`
- `device_id`
- `transaction_id`

When lineage columns are available, the latest `ingested_at` and `raw_record_id` values determine
which record is kept. Otherwise, the last input occurrence is kept.

## Dependency-Safe Load Order

Staging tables are loaded in this order:

1. `countries`
2. `customers`
3. `accounts`
4. `counterparties`
5. `devices`
6. `transactions`

This order satisfies foreign key dependencies in the current PostgreSQL schema.

## Validation Before Load

The staging pipeline reuses existing validation schemas and referential checks before loading. The
current staging transaction table does not include labelled scenario metadata columns, so validation
adds transient scenario fields to a copy of the transaction DataFrame and loads only the real
staging table columns.

Use `--no-validate` only for local diagnostics when you need to inspect transformation output despite
validation failures.

## Upsert Behaviour

Staging loads use PostgreSQL `INSERT ... ON CONFLICT ... DO UPDATE` through SQLAlchemy bound
parameters. The loader does not use pandas `to_sql`. Empty DataFrames return a row count of `0`.

## Audit Event Writing

By default, staging writes one `governance.audit_events` row with:

- `event_type`: `staging_transformation`
- `component`: `staging`
- `action`: `transform_raw_to_staging`
- `status`: `completed`

The audit event details include row counts and pipeline metadata.

## CLI Usage

```bash
python scripts/stage_data.py stage
python scripts/stage_data.py stage --limit 1000
python scripts/stage_data.py stage --no-validate
python scripts/stage_data.py stage --no-audit
```

The CLI creates and disposes a PostgreSQL engine. It does not reset, initialise, seed, generate,
validate persisted files, or ingest raw files automatically.

## Makefile Usage

```bash
make stage-data
make stage-data-no-validate
make stage-data-limited
```

Full local workflow:

```bash
make services-up
make db-reset
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
```

## Limitations

This workflow implements raw-to-staging transformations only. It does not create account features,
execute AML rules, construct graphs, train models, score risk, or generate cases. The data
dictionary artefact documents this staging model separately.
