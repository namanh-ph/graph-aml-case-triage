# Account Feature Engineering

Account-level feature engineering computes the first behavioural feature table used by later AML
rules, anomaly detection, scoring, and model validation work.

## Inputs

The live workflow reads from PostgreSQL staging tables:

- `staging.accounts`
- `staging.transactions`

The default feature CLI path is read-only against PostgreSQL and writes local artefacts. Persistence
into the mart table is explicit through `--persist`. The CLI does not reset, initialise, seed,
ingest, stage, run rules, train models, or generate cases automatically.

## Feature Date Logic

Feature dates are normalised to midnight UTC calendar dates. When dates are not supplied, the date
range is derived from the minimum and maximum staged transaction timestamps.

Rolling windows include transactions where:

```text
feature_date - window_days < transaction_timestamp <= feature_date + 1 day
```

## Feature Definitions

Generated columns:

- `account_id`: staged account identifier.
- `feature_date`: daily feature date.
- `feature_version`: reproducible feature generation version.
- `txn_count_1d`: sent or received transaction count in the 1-day window.
- `txn_count_7d`: sent or received transaction count in the 7-day window.
- `total_sent_7d`: sum of amounts where the account is sender in the 7-day window.
- `total_received_7d`: sum of amounts where the account is receiver in the 7-day window.
- `avg_txn_amount_30d`: average sent or received transaction amount in the 30-day window.
- `max_txn_amount_30d`: maximum sent or received transaction amount in the 30-day window.
- `unique_counterparties_7d`: unique outbound recipients plus unique inbound senders in the
  7-day window.
- `in_out_ratio_7d`: sent value divided by received value in the 7-day window.

## Behavioural Features

Extended account features add non-geographic behaviour signals:

- `retained_balance_proxy`: total received value minus total sent value in the rolling weekly
  window. Negative values are allowed for pass-through behaviour.
- `below_threshold_count_24h`: outbound transactions where
  `reporting_threshold * below_threshold_margin <= amount < reporting_threshold` in the current
  24-hour activity window.
- `dormant_days_before_activity`: calendar-day gap between the most recent prior activity and the
  first transaction in the current activity window.
- `counterparty_entropy`: Shannon entropy over outbound recipient keys in the rolling entropy
  window.

## Jurisdiction Features

Extended account features also add jurisdiction risk signals:

- `cross_border_ratio_30d`: cross-border transaction count divided by total account transaction
  count in the rolling jurisdiction window.
- `high_risk_country_exposure`: value-weighted exposure using the maximum risk weight of each
  transaction's origin and destination countries.

## Extended Account Feature Table

The extended CSV includes:

```text
account_id
feature_date
feature_version
txn_count_1d
txn_count_7d
total_sent_7d
total_received_7d
avg_txn_amount_30d
max_txn_amount_30d
unique_counterparties_7d
in_out_ratio_7d
retained_balance_proxy
below_threshold_count_24h
dormant_days_before_activity
cross_border_ratio_30d
high_risk_country_exposure
counterparty_entropy
```

## Below-Threshold Activity

Below-threshold activity supports structuring review by counting outbound transactions close to but
below the reporting threshold. The default threshold is `10000.0` and the default lower-bound margin
is `0.95`.

## Dormant Account Behaviour

Dormant behaviour measures inactivity before current account activity. It is nullable because many
accounts either have no current activity or no prior activity.

## Counterparty Entropy

Counterparty entropy measures whether outbound transactions concentrate on one recipient or spread
across multiple recipients. A single counterparty has entropy `0.0`.

## High-Risk Country Exposure

High-risk exposure uses `staging.countries.risk_score / 100` when available. If a country is marked
high risk without a usable score, the weight is `1.0`; lower-risk countries without a score receive
`0.0`.

## Cross-Border Activity

Cross-border activity uses `is_cross_border` when available and otherwise derives the flag from
origin and destination countries.

## Account Universe Logic

By default, all staged accounts are included for every feature date, including accounts with zero
activity. Use `--active-only` to include only accounts observed as transaction senders or receivers.

## Artefact Outputs

Generated files are written to `reports/model_validation` by default:

```text
reports/model_validation/
|-- account_features.csv
|-- account_feature_summary.json
```

## CLI Usage

```bash
python scripts/generate_account_features.py staged
python scripts/generate_account_features.py staged --limit 1000
python scripts/generate_account_features.py staged --output-dir reports/model_validation
python scripts/generate_account_features.py staged --feature-version account_features_v1
python scripts/generate_account_features.py staged --extended
```

## Makefile Usage

```bash
make generate-account-features
make generate-account-features-limited
make generate-account-features-extended
make generate-account-features-extended-limited
```

## Feature Persistence

Feature persistence writes the extended account feature table into PostgreSQL
`mart.features_account_daily`. The persisted columns align with the generated non-graph behavioural
feature set and exclude database-managed columns such as `feature_id` and `created_at`.

```bash
python scripts/generate_account_features.py staged --extended --persist
python scripts/generate_account_features.py staged --extended --persist --no-audit
python scripts/generate_account_features.py staged --read-mart
```

## Mart Feature Table

`mart.features_account_daily` stores one row per account, feature date, and feature version. It is
the first analytics-ready feature table for later AML rules, scoring, and model validation work.

## Feature Versioning

`feature_version` is written to every row and defaults to `account_features_v1`. Override it with:

```bash
python scripts/generate_account_features.py staged --extended --persist --feature-version account_features_v2
```

## Idempotent Upserts

Feature persistence uses the unique upsert key:

```text
account_id, feature_date, feature_version
```

Running the same feature version repeatedly updates existing rows rather than duplicating them.

## Feature Persistence Audit Events

By default, persistence writes one `governance.audit_events` row with:

- `event_type = feature_persistence`
- `component = features`
- `action = persist_account_features`
- row count, account count, feature date count, feature version, and metadata in `details`

Use `--no-audit` only for diagnostic runs where audit writing is intentionally skipped.

## Reading Persisted Mart Features

Persisted rows can be inspected without recalculating features:

```bash
python scripts/generate_account_features.py staged --read-mart
python scripts/generate_account_features.py staged --read-mart --feature-version-filter account_features_v1
```

## Limitations

This layer persists account features only. It does not implement graph features, AML rules, scoring,
or cases. The next ticket defines the common AML alert schema.
