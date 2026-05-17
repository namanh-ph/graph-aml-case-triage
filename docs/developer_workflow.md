# Developer Workflow

## Governance Inventory

Use `python scripts/governance.py inventory run` or `make governance-inventory-run` to build a
local-first inventory of existing persisted outputs. The workflow reads table metadata, audit
events, model run tables, validation run tables, configured process dependencies from
`config/governance.yaml`, and bounded local artefacts under `docs` and `reports/model_validation`.
It does not run upstream workflows, train models, generate labels, or change thresholds.

The inventory writes lineage nodes, lineage edges, artefact registry rows, process inventory,
model inventory, validation inventory, a summary JSON file, and a Markdown report. Persisted runs
are available under the `governance` schema when `--persist` is supplied.

## Explainability And Model Cards

Run `make explainability-run` to build local explainability artefacts from existing persisted
outputs, or `make explainability-run-persist` to persist them under the governance schema. The
workflow reads supervised model runs, supervised scores, case and account risk scores, evidence
packs, analyst labels, model comparison results, and monitoring outputs. It does not retrain
models, generate labels, run monitoring, call external APIs, or alter thresholds.

Global feature importance is derived from persisted supervised model metadata when available. Local
feature contributions are deterministic approximations from score metadata and are limited when
feature values were not persisted. Composite score decomposition explains case and account score
components without changing scoring weights. Reason contributions combine score components,
evidence packs, label context, and supervised feature rows where present. The consolidated model
card in `reports/model_validation/consolidated_model_card.md` brings these outputs together with
validation and monitoring summaries.

This project uses `uv`, `make`, Docker Compose, pytest, Ruff, and mypy for local development.

## First-Time Setup

```bash
cp .env.example .env
make setup
make check-env
make info
```

## Quality Checks

Run the full static and test suite before handing off changes:

```bash
make check
```

This runs linting, type checking, and tests. Individual commands are also available:

```bash
make lint
make typecheck
make test
make test-cov
```

## Local Services

Start PostgreSQL and Neo4j when a later ticket needs local infrastructure:

```bash
make services-up
make services-ps
```

Optional MLflow service:

```bash
make mlflow-up
```

Stop services when done:

```bash
make services-down
```

PostgreSQL schema SQL files have been defined under `src/graph_aml/database/sql/`. They are static artefacts for now and will be executed by database utilities in later tickets.

```bash
python -m pytest tests/test_database_schemas.py
python -m pytest tests/test_database_schema_sql_files.py
```

Core PostgreSQL table DDL has also been defined as static SQL artefacts. It will be executed by database utilities in later tickets.

```bash
python -m pytest tests/test_database_tables.py
python -m pytest tests/test_database_table_sql_files.py
```

Local database utilities can initialise the schema and core table artefacts when PostgreSQL is running:

```bash
cp .env.example .env
make services-up
make db-check
make db-init
make db-list-schemas
make db-list-staging-tables
```

Local reset and smoke seed commands can recreate the database and add deterministic records for
query and dashboard smoke testing:

```bash
cp .env.example .env
make services-up
make db-check
make db-recreate-and-seed
make db-list-schemas
make db-list-staging-tables
```

Smoke seed data is intentionally small and exists only to test database utilities before the full
reference data generator is implemented.

## Reference Data

Generate local baseline files for later ingestion tickets:

```bash
make generate-data-small
make reference-summary
python -m pytest tests/test_synthetic_dataset_integrity.py
```

Generated files are written under `data/`. Loading those files into PostgreSQL comes in a
later ingestion ticket.

Generate labelled AML scenario files for later rule tests:

```bash
make generate-data-scenarios-small
make reference-summary
python -m pytest tests/test_synthetic_aml_scenario_patterns.py
```

Persisted reference datasets are written into versioned directories with metadata, checksums, and
latest pointers:

```bash
make generate-data-scenarios-small
make reference-summary-scenarios
python -m pytest tests/test_synthetic_persisted_readback.py
```

Load persisted scenario data into PostgreSQL raw tables:

```bash
cp .env.example .env
make services-up
make db-reset
make generate-data-scenarios-small
make load-data-scenarios
```

Raw ingestion appends records into the `raw` schema and stores full source rows as JSONB payloads.
Staging transformations can standardise raw JSONB payloads into relational staging tables.

Validate persisted scenario data before loading it:

```bash
make generate-data-scenarios-small
make validate-data
make validate-data-strict
make validate-data-audit
make load-data-scenarios
```

Validation artefacts are written under `reports/validation_failures`, and `make validate-data-audit`
records one governance audit event when PostgreSQL is available.

Transform raw records into staging tables:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
```

Staging expands raw JSONB payloads into relational records, validates the transformed frames, upserts
into `staging` tables, and writes a governance audit event.

Generate the data dictionary governance artefact:

```bash
make generate-data-dictionary
python -m pytest tests/test_data_dictionary_writers.py
```

The data dictionary documents SQL table definitions, business meanings, validation rules, lineage,
and examples. Dataset summaries profile actual generated and staged values.

Generate exploratory dataset summary artefacts:

```bash
make generate-data-scenarios-small
make validate-data-strict
make generate-dataset-summary
```

For staged profiling:

```bash
make services-up
make db-reset
make load-data-scenarios
make stage-data
make generate-dataset-summary-staged
```

Dataset summaries profile counts, date ranges, amount distributions, suspicious labels, scenario
coverage, and data quality metrics.

Generate account-level feature artefacts from staging:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make generate-account-features
```

Account feature artefacts are local CSV and JSON files for model validation and downstream rule
development.

Generate extended behavioural and jurisdiction feature artefacts:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make generate-account-features-extended
```

Extended features add retained balance proxy, below-threshold counts, dormant days, cross-border
ratio, high-risk country exposure, and counterparty entropy.

Persist extended account features into the mart table and inspect persisted rows:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make persist-account-features
make read-mart-account-features
```

Feature persistence writes `mart.features_account_daily` rows and governance audit events.

Inspect the common alert schema utilities:

```bash
make alerts-schema-info
python -m pytest tests/test_alert_schema.py
python -m pytest tests/test_alert_persistence.py
```

Run and persist structuring alerts:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-structuring-rule-persist
make alerts-read
```

Focused fixture tests now cover structuring edge cases.

Run the focused structuring fixture suite:

```bash
make test-structuring-fixtures
python -m pytest tests/test_structuring_rule.py
```

Fan-in rule workflow is now available.

Run and persist fan-in alerts:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-fan-in-rule-persist
make alerts-read
```

Fan-out rule workflow is now available.

Run and persist fan-out alerts:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-fan-out-rule-persist
make alerts-read
```

Joint fan-in and fan-out fixture hardening is now available.

Run the focused fan-in and fan-out fixture suite:

```bash
make test-fan-flow-fixtures
python -m pytest tests/test_fan_in_rule.py
python -m pytest tests/test_fan_out_rule.py
```

Rapid movement rule workflow is now available.

Run and persist rapid movement alerts:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-rapid-movement-rule-persist
make alerts-read
```

Dormant reactivation rule workflow is now available.

Run and persist dormant reactivation alerts:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-dormant-reactivation-rule-persist
make alerts-read
```

Joint rapid movement and dormant reactivation fixture hardening is now available.

Run the focused movement and dormancy fixture suite:

```bash
make test-movement-dormancy-fixtures
python -m pytest tests/test_rapid_movement_rule.py
python -m pytest tests/test_dormant_reactivation_rule.py
```

Circular flow detection and alert conversion workflows are now available.

Run detection and write local artefacts:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make detect-circular-flows
make run-circular-flow-rule-persist
make alerts-read
```

Run all enabled deterministic rules through the unified engine:

```bash
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make rules-list
make run-aml-rules-persist
make alerts-read
```

Generate and validate formal AML rule documentation:

```bash
make rules-docs-list
make rules-docs-validate
make generate-rule-docs
python -m pytest tests/test_rule_documentation_files.py
```

Run Neo4j connection utility checks:

```bash
cp .env.example .env
make services-up
make graph-config
make graph-health
make graph-constraints-ensure
make graph-constraints-list
```

Load staged PostgreSQL data and persisted AML alerts into Neo4j:

```bash
cp .env.example .env
make services-up
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-aml-rules-persist
make graph-health
make graph-constraints-ensure
make graph-load
```

Compute Neo4j graph analytics features:

```bash
cp .env.example .env
make services-up
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-aml-rules-persist
make graph-load
make graph-analytics
```

Persist graph analytics features to PostgreSQL:

```bash
cp .env.example .env
make services-up
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-aml-rules-persist
make graph-load
make graph-analytics
make graph-features-persist
make graph-features-summary
```

Train, score, and persist the Isolation Forest anomaly model:

```bash
cp .env.example .env
make services-up
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-aml-rules-persist
make graph-load
make graph-features-persist
make model-isolation-forest-persist
make anomaly-scores-summary
```

Composite risk scoring combines rule alerts, graph features, and anomaly scores into a single account-level score.

Score and optionally persist composite account risk:

```bash
cp .env.example .env
make services-up
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-aml-rules-persist
make graph-load
make graph-features-persist
make model-isolation-forest-persist
make account-risk-score-persist
make account-risk-summary
```

Generate and persist deterministic AML investigation cases:

```bash
cp .env.example .env
make services-up
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-aml-rules-persist
make graph-load
make graph-features-persist
make model-isolation-forest-persist
make account-risk-score-persist
make cases-generate-persist
make cases-summary
```

Case generation reads persisted alerts, account risk scores, graph features, accounts, and evidence
transactions. It writes deterministic case records to `aml.cases` and link rows to
`aml.case_alerts` and `aml.case_entities`; the next layer adds final case-level risk scoring and
explanations for analyst review.

Score and optionally persist generated cases:

```bash
cp .env.example .env
make services-up
make generate-data-scenarios-small
make validate-data-strict
make load-data-scenarios
make stage-data
make run-aml-rules-persist
make graph-load
make graph-features-persist
make model-isolation-forest-persist
make account-risk-score-persist
make cases-generate-persist
make case-risk-score-persist
make case-risk-summary
```

Case risk scoring reads generated cases and linked evidence, then persists formal scores to
`aml.case_risk_scores`. Optional snapshot fields on `aml.cases` support fast triage reads. Analyst
lifecycle actions and dashboard workflows are reserved for later tickets.

## Dashboard

The Streamlit dashboard is a local read layer over persisted PostgreSQL artefacts. Prepare data
through the backend workflow first, then run:

```bash
make dashboard-health
make dashboard-summary
make dashboard
```

Implemented pages are Overview, Alert Queue, Case Queue, and Case Detail. Case Detail reads
evidence packs, deterministic explanations, and lifecycle timelines, then exposes guarded forms for
status changes, assignments, and comments. Those forms call the audited lifecycle backend only after
an explicit submit. The dashboard does not run ingestion, detection, graph loading, model training,
risk scoring, case generation, or evidence generation automatically.

Graph View and Account Profile extend the dashboard without changing that safety model. Graph View
builds a bounded PostgreSQL-first network from selected case IDs, account IDs, communities, or risk
bands, then renders account, counterparty, transaction, alert, and case context. Account Profile
reads account/customer context, transactions, alerts, linked cases, behavioural features, graph
features, anomaly scores, account risk scores, and counterparties. Both pages are read-only;
only Case Detail lifecycle forms mutate state.

```bash
make dashboard-graph-summary
python scripts/dashboard.py account-summary --account-id SAMPLE_ACCOUNT_ID
```

Model Metrics, Audit Log, and Validation Report complete the first governance dashboard surface:

```bash
make dashboard-model-summary
make dashboard-audit-summary
make dashboard-validation-index
```

Model Metrics reads `governance.model_runs`, `mart.account_anomaly_scores`,
`mart.account_risk_scores`, and `aml.case_risk_scores`. Audit Log reads
`governance.audit_events` with component, event type, status, run ID, and safe text filters.
Validation Report reads local artefacts only under the configured report directory. These pages do
not call MLflow servers, train models, run scoring, mutate lifecycle state, or generate reports.

## End-to-End Demo Workflow

The demo script orchestrates existing commands rather than duplicating business logic. It plans and
runs the local sequence for data generation, validation, staging, rule persistence, graph loading,
graph features, model scores, account risk scores, case generation, case risk scores, evidence
packs, dashboard health, and validation indexing.

```bash
cp .env.example .env
make services-up
make demo-readiness
make demo-run-dry
make demo-run
make demo-validate
make dashboard
```

Use `make demo-run-with-reset` only when intentionally resetting local PostgreSQL state. Unit tests
do not run the full demo, Docker, PostgreSQL, Neo4j, or Streamlit; they validate command planning,
safety checks, dry-run behavior, and local artefact generation.

## Case Evidence Workflow

Case evidence generation runs after case risk scoring. It reads `aml.cases`, `aml.case_alerts`,
`aml.case_entities`, `aml.alerts`, `staging.transactions`, `mart.account_risk_scores`,
`aml.case_risk_scores`, `mart.graph_features`, and `mart.account_anomaly_scores`, then builds
structured evidence packs and deterministic explanations.

```bash
make case-evidence-build
make case-evidence-build-persist
make case-evidence-read
make case-evidence-summary
```

Evidence packs are persisted to `aml.case_evidence_packs`; explanation text is persisted to
`aml.case_explanations`. The workflow is read-only with respect to alert, graph, model, account
risk, case generation, and case risk semantics. Analyst lifecycle actions and Streamlit Case Detail
pages consume these evidence records in later tickets.

## Case Lifecycle Workflow

Lifecycle commands make generated cases operationally reviewable before the dashboard is built.
Supported statuses are `New`, `In review`, `Escalated`, `Information requested`,
`Closed false positive`, `Closed suspicious`, and `Archived`. The configured transition matrix
allows review, escalation, information requests, closure, and archival while keeping terminal
statuses restricted to archival.

```bash
python scripts/cases.py lifecycle status --case-id SAMPLE_CASE_ID --to-status "In review" --decision-reason "Start review"
python scripts/cases.py lifecycle assign --case-id SAMPLE_CASE_ID --assigned-to local_analyst
python scripts/cases.py lifecycle comment --case-id SAMPLE_CASE_ID --comment "Reviewed initial evidence pack"
make case-lifecycle-events
make case-lifecycle-assignments
make case-lifecycle-summary
```

Lifecycle events are append-only in `aml.case_lifecycle_events`, current assignments are in
`aml.case_assignments`, and current case snapshots are stored on `aml.cases`. Each action writes
audit event `case_lifecycle_action` when audit is enabled. These records feed dashboard decision
forms and future analyst feedback labels.

## Analyst Feedback Label Workflow

Analyst label generation runs after lifecycle closures exist. It converts explicit closure
decisions into supervised-readiness rows without mutating lifecycle history or training a model.
`Closed suspicious` maps to label `1`; `Closed false positive` maps to label `0`.

```bash
make labels-build
make labels-build-persist
make labels-read-case
make labels-read-account
make labels-summary
```

Case labels are stored in `aml.case_labels`, account labels in `aml.account_labels`, and
supervised-readiness datasets in `mart.case_supervised_dataset` and
`mart.account_supervised_dataset`. Leakage checks require labels to occur after case creation and,
where feature timestamps exist, features to predate labels. Sparse reference labels are expected in
local demos; this layer prepares future supervised training data but does not train a model.

## Supervised Model Baseline Workflow

Supervised model training reads existing supervised-readiness datasets. It does not generate
labels, run upstream pipelines, or replace Isolation Forest and composite risk scoring.

```bash
make labels-build-persist
make model-supervised-train
make model-supervised-train-persist
make model-supervised-read-scores
make model-supervised-read-runs
make model-supervised-summary
```

Logistic Regression is the default interpretable benchmark. Random Forest can be selected with
`python scripts/models.py supervised train --model-family random_forest`. The split is time-aware by
default, holding out the latest labelled rows for validation. Metrics include precision, recall,
F1, ROC-AUC, PR-AUC where both classes exist, threshold grids, and precision/recall@K. Class
imbalance is handled with configured class weights.

## Model Comparison Workflow

Use `make model-comparison-run` to compare existing persisted scores against analyst feedback
labels and write local validation artefacts. Use `make model-comparison-run-persist` to also persist
comparison runs, metrics, threshold recommendations, and champion-challenger rows.

The comparison requires labelled case or account entities plus at least one candidate score table.
It computes precision@K, recall@K, threshold operating metrics, and champion selection without
retraining models, generating labels, or changing account or case risk scoring semantics.

## Cleaning

Remove Python and tooling caches:

```bash
make clean
```

## Day-to-Day Command Order

```bash
cp .env.example .env
make setup
make check-env
make info
make check
make services-up
make services-ps
make run-dashboard
```
## Monitoring And Drift Validation

Run monitoring after risk scores, labels, supervised scores, and model comparison outputs are
available:

```bash
make monitoring-run
make monitoring-run-persist
make monitoring-read-runs
make monitoring-read-drift
make monitoring-read-volume
make monitoring-read-segments
make monitoring-read-backtesting
make monitoring-summary
```

The monitoring workflow builds baseline and comparison windows from persisted timestamps, computes
PSI, KS statistic, mean shift, median shift, categorical distribution shift, score stability,
alert and case volume changes, segment metrics, and backtesting metrics. It reads persisted data and
writes validation artefacts; it does not train models, generate labels, alter thresholds, or run
upstream workflows.

## Security Controls Workflow

Security controls are run with `make security-controls-run` or persisted with
`make security-controls-run-persist`. The workflow reads table-column metadata and audit events,
builds a sensitive field inventory, evaluates role permissions, scans configured local source and
documentation directories for secret-like strings, and runs audit integrity checks.

Use `make security-mask-preview` to inspect a bounded masked sample from an allowed project schema.
Sanitised export helpers mask sensitive fields and remove blocked columns. Sensitive exports are
disabled by default. The workflow does not run upstream pipelines, train models, generate labels,
alter thresholds, or call external services.

## Release Readiness Workflow

Release readiness is run locally with `make release-readiness-run` or persisted with
`make release-readiness-run-persist`. The local-only path checks repository hygiene,
documentation completeness, validation artefact availability, and builds a reviewer evidence pack
without PostgreSQL.

The release pack writes `release_readiness_report.md`, `release_validation_index.csv`,
`release_evidence_index.csv`, `release_readiness_summary.json`, and Markdown files under
`release_pack/` for portfolio summary, architecture summary, dashboard walkthrough, command
transcript template, and demo validation checklist. The workflow packages existing evidence only;
it does not run upstream workflows, train models, generate labels, or change thresholds.
