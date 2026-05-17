# Model Validation

## Governance Inventory Evidence

Governance inventory outputs complement model comparison, monitoring, explainability, and model
cards by documenting what artefacts and persisted run records exist for review. The inventory
includes table nodes, process nodes, dependency edges, model inventory rows, validation inventory
rows, and hashed report/documentation artefacts.

Lineage is partly configured and partly observed. Configured process dependencies describe the
expected production path from ingestion through rules, graph analytics, scoring, labels,
supervised modelling, model comparison, monitoring, and explainability. Audit events and run
tables add run-level evidence where available. Sparse or missing audit history should be treated
as a limitation in the validation pack.

## Explainability And Model Card Consolidation

Explainability artefacts are generated from persisted model and validation outputs. Global feature
importance summarises supervised model drivers when coefficients or feature importances are stored
in `governance.supervised_model_runs`. Local contribution rows are deterministic approximations
from persisted feature-value metadata and are unavailable when that metadata is absent.

Composite score decomposition reports case and account score components such as rule, graph,
anomaly, customer, jurisdiction, value, and evidence-density scores without changing weights or
score semantics. Reason contributions combine rule-like components, graph and anomaly context,
supervised feature contributions, case evidence packs, and analyst label context where available.

The consolidated model card ties together data sources, reference data caveats, label mapping,
supervised baseline information, model comparison and threshold calibration results, drift
monitoring, score decomposition, limitations, and next steps. It complements model comparison and
monitoring by explaining the existing outputs rather than retraining or recalibrating them.

## Isolation Forest Anomaly Scoring

The Isolation Forest layer reads persisted account behavioural features from
`mart.features_account_daily` and persisted graph analytics features from `mart.graph_features`.
The feature matrix is account-level, deterministic, and keyed by `account_id`.

Preprocessing excludes `account_id`, imputes missing numeric values using the configured strategy
(`median`, `mean`, or `zero`), and applies the configured scaling strategy (`standard`, `robust`,
or `none`). Imputation values, scaling values, feature names, and model parameters are stored with
the persisted score metadata for reproducibility.

The model uses scikit-learn `IsolationForest` with deterministic configuration from
`config/model.yaml`. Raw model outputs are transformed so higher `anomaly_score` values indicate
more anomalous accounts. Risk bands are assigned from percentile thresholds:

- `high` at or above `score_percentile_high`
- `medium` at or above `score_percentile_medium`
- `low` otherwise

Persisted scores are written to `mart.account_anomaly_scores` with the primary key
`account_id, score_date, model_name, model_version, model_run_id`. The row stores feature lineage,
model parameters, preprocessing metadata, score metrics, and caller metadata. Upserts are
idempotent for the same score date, model name, model version, and run ID.

MLflow logging is optional. When enabled, the workflow logs model parameters, training row count,
feature count, score summary metrics, and local validation artefacts.

Known limitations:

- The model is unsupervised and does not prove suspicious activity by itself.
- Scores depend on the available feature snapshot and should be reviewed alongside deterministic
  AML rule alerts.
- Risk-band thresholds are configurable governance thresholds, not supervised probability cutoffs.

Validation checks cover configuration, feature input shape, preprocessing determinism, score ranges,
risk bands, persistence SQL, readback utilities, local artefacts, and optional MLflow logging.
Composite risk scoring will combine rule alerts, graph features, and anomaly scores in the next
layer.

## Composite Account Risk Scoring

Composite account risk scoring combines five transparent components:

```text
account_risk_score =
  rule_risk_score * weight_rule
  + graph_risk_score * weight_graph
  + anomaly_risk_score * weight_anomaly
  + customer_risk_score * weight_customer
  + jurisdiction_risk_score * weight_jurisdiction
```

The weights, severity mappings, graph subcomponent weights, and risk-band thresholds are configured
in `config/scoring.yaml`. Component scores are bounded to `0..100`, ranked by descending composite
score, and assigned `low`, `medium`, `high`, or `critical` bands.

Inputs are persisted `aml.alerts`, `mart.graph_features`, `mart.account_anomaly_scores`, and
staged account/customer jurisdiction attributes. Persisted outputs are written to
`mart.account_risk_scores` with primary key `account_id, score_date, score_name, score_version`.
Rows include component scores, coverage, weights JSON, metadata JSON, and audit lineage for later
case generation.

## Case Generation Validation

Case generation reads persisted alerts, account risk scores, graph features, accounts, and evidence
transactions. Grouping strategies cover same account, same customer, shared graph community,
circular flow evidence, and common counterparties. Generated cases receive stable IDs from the
grouping strategy, group key, alert IDs, and case version.

Persisted outputs are `aml.cases`, `aml.case_alerts`, and `aml.case_entities`. Validation checks
cover required columns, duplicate case IDs, duplicate case-alert links, non-empty status and
severity, bounded priority scores, row-count comparisons, and JSON artefact summaries. Final
case-level risk scoring and analyst-facing explanations come next.

## Case Risk Scoring

Case risk scoring reads generated cases, case-alert links, persisted alerts, account risk scores,
graph features, anomaly scores, and evidence transaction context. The composite score is:

```text
case_risk_score =
  alert_risk_score * weight_alert
  + account_risk_score * weight_account
  + graph_risk_score * weight_graph
  + anomaly_risk_score * weight_anomaly
  + typology_diversity_score * weight_typology
  + evidence_value_score * weight_evidence
```

Subcomponents are bounded to `0..100`, risk bands come from `config/scoring.yaml`, and cases are
ranked by descending case risk score then `case_id`. Scores persist to `aml.case_risk_scores` with
primary key `case_id, score_date, score_name, score_version`. Optional snapshot columns on
`aml.cases` carry the latest score, band, and rank for read paths that only need case rows.

Validation checks cover component ranges, duplicate case IDs, risk bands, rank values, persistence
metadata columns, row-count comparisons, and JSON artefacts. Audit event `case_risk_scoring`
records row counts, snapshot update counts, score version, summary metrics, and metadata. Analyst
lifecycle actions and dashboard triage pages are later layers.

## Case Evidence and Explanation Validation

Case evidence generation reads generated cases, case links, alerts, evidence transactions, account
risk scores, case risk scores, graph features, and anomaly scores. Evidence sections cover
typology context, alert evidence, transaction evidence, account context, graph context, risk
drivers, chronology, evidence quality, and recommended review focus.

The deterministic explanation renderer uses fixed templates for case summary, typology summary,
risk-driver summary, transaction summary, graph summary, and review-focus bullets. Outputs persist
to `aml.case_evidence_packs` with primary key `case_id, evidence_version` and
`aml.case_explanations` with primary key `case_id, explanation_version`.

Validation checks cover required columns, duplicate versioned rows, non-empty explanation text,
JSON-serialisable evidence fields, missing evidence coverage, chronology counts, review-focus
counts, and row-count comparisons. Audit event `case_evidence_generation` records evidence and
explanation row counts, versions, summary metrics, and metadata for future analyst lifecycle and
Case Detail dashboard validation.

## Case Lifecycle Validation

Lifecycle validation covers append-only action events, current assignment snapshots, configured
statuses, allowed transitions, decision types, and closure requirements. Event frames must include
non-empty action IDs, case IDs, action types, analyst IDs, and timestamps with no duplicate action
IDs. Assignment frames require non-empty case IDs.

Persistence writes `aml.case_lifecycle_events` and `aml.case_assignments`, then updates additive
snapshot fields on `aml.cases`. Audit event `case_lifecycle_action` records action ID, case ID,
action type, source and target status, current status, analyst ID, snapshot update flags, and
metadata. These validation artefacts provide the bridge to future dashboard decision forms and
future analyst feedback labels.

## Dashboard Validation Surface

Dashboard helpers validate alert queues, case queues, and case detail bundles before display.
Quality summaries report persisted overview counts and visible queue rows. Unit tests mock SQL reads
so dashboard validation does not require live PostgreSQL.

The dashboard surfaces existing model, risk, evidence, and lifecycle artefacts for analyst review.
It does not retrain models, recompute scores, or generate validation reports. Dedicated model
validation report pages are reserved for a later dashboard ticket.

## Dashboard Graph And Account Validation

Graph View validation covers configuration limits, PostgreSQL graph seed readers, optional Neo4j
record conversion, graph frame normalisation, duplicate node and edge removal, node size scaling,
and local PyVis or Plotly rendering helpers. Account Profile validation covers account header,
transaction, alert, case, feature, counterparty, summary metric, component, and download helpers.

Both surfaces are tested with mocked SQL reads so PostgreSQL and Neo4j are not required for unit
tests. Optional live smoke tests are skipped unless
`RUN_DASHBOARD_GRAPH_ACCOUNT_INTEGRATION_TESTS=1` is set.

## Dashboard Governance Validation

Model Metrics reads `governance.model_runs`, `mart.account_anomaly_scores`,
`mart.account_risk_scores`, and `aml.case_risk_scores`. It reports score distribution statistics,
risk-band counts, top-ranked records, and precision@K rows. If no binary label column is available,
precision@K rows are explicitly marked `label_unavailable`.

Audit Log reads `governance.audit_events` and supports component, event type, status, run ID, and
safe text search over selected fields and details text. Validation Report lists and previews local
artefacts under `reports/model_validation` or the configured report directory, constrained to
allowed extensions and safe resolved paths.

These dashboard pages do not train models, call MLflow servers, recompute scores, mutate lifecycle
state, or generate validation reports. Optional live smoke tests are skipped unless
`RUN_DASHBOARD_GOVERNANCE_INTEGRATION_TESTS=1` is set.

## Demo Validation and Readiness Checks

The demo validation layer checks local database counts after a run and indexes artefacts under
`reports/model_validation`. Count thresholds cover transactions, accounts, alerts, generated cases,
case risk scores, case evidence packs, audit events, and validation files. Unmet thresholds are
reported as warnings so a partial local run can still be inspected.

The readiness report verifies required files, directories, and Python packages without connecting
to PostgreSQL, Neo4j, or Streamlit. The run summary records planned or executed steps, command
statuses, output tails, and reset metadata. The artefact index records file names, relative paths,
extensions, sizes, and modified timestamps.

Reference labels remain a limitation. Precision@K should be interpreted as `label_unavailable`
unless a binary analyst label column exists in the relevant score table.

## Analyst Feedback Labels and Supervised Readiness

Analyst feedback labels convert reviewed lifecycle outcomes into validation-ready binary targets.
`Closed suspicious` produces a positive label, and `Closed false positive` produces a negative
label. The mapping is versioned in `config/scoring.yaml` under `analyst_labels`.

Case-level datasets join case labels to case risk features. Account-level datasets propagate case
labels to primary and related accounts, then join account risk scores, anomaly scores, graph
features, and available behavioural features. Missing feature values are preserved rather than
imputed so downstream validation can measure coverage honestly.

Quality checks validate required columns, binary labels, duplicate IDs by version, label timestamp
presence, class balance, minimum label thresholds, and row-count comparisons. Leakage controls
reject labels before case creation and reject features timestamped after the label where timestamp
columns exist. Sparse reference labels should be treated as supervised-learning readiness signals,
not evidence of production model performance.

## Supervised AML Baseline Validation

The supervised baseline consumes `mart.case_supervised_dataset` or
`mart.account_supervised_dataset`. Feature matrices exclude IDs, labels, label names, timestamps,
metadata, and non-numeric fields. Missing numeric values are imputed inside a scikit-learn pipeline,
with optional standardisation and filtering of constant or high-missing features.

The default validation strategy is time-based: the latest labelled rows are held out for
validation. Stratified random splitting is available for compact experiments. Logistic Regression
uses balanced class weights by default, and Random Forest offers an optional stronger benchmark.

Metrics include accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion counts, threshold grid
metrics, and precision/recall@K. Single-class validation outputs warnings for AUC metrics rather
than fabricating results. Sparse reference analyst labels limit statistical confidence, so these
models should be interpreted as baselines for future feedback learning.

## Model Comparison And Threshold Calibration

Model comparison evaluates labelled entities against candidate score sources including
`aml.case_risk_scores`, `mart.supervised_model_scores`, `mart.account_risk_scores`, and
`mart.account_anomaly_scores`. Precision@K and recall@K describe top-ranked triage effectiveness,
while threshold calibration estimates precision, recall, F1, and review volume at candidate
operating thresholds.

Champion-challenger selection ranks candidates using the configured primary metric and tie breakers.
Sparse labels and single-class labels should be flagged as limitations. The workflow validates
existing persisted scores only and does not retrain supervised models or modify composite risk
scoring.
## Drift Monitoring, Backtesting, And Segment Stability

Monitoring evaluates whether persisted AML outputs are stable across baseline and comparison
windows. The default configuration uses adjacent 30-day windows and also supports weekly, monthly,
and quarterly backtesting windows.

Drift metrics include population stability index, KS statistic, mean shift, median shift, and
categorical distribution shift. Score monitoring summarises score distributions, high-risk share,
and top-K score behaviour. Volume monitoring compares alert, case, typology, and rule volumes
between windows and assigns stable, warning, critical, or insufficient-data bands.

Segment monitoring reviews available customer segment, jurisdiction, risk-band, typology, and rule
slices. Label metrics such as positive rate, precision@K, and recall@K are computed only when labels
exist. Sparse reference labels should be interpreted as validation-readiness signals rather than
production evidence.

Monitoring outputs are persisted under `governance.monitoring_runs`,
`governance.drift_metrics`, `governance.score_monitoring_metrics`,
`governance.volume_monitoring_metrics`, `governance.segment_monitoring_metrics`, and
`governance.backtesting_metrics`. Local artefacts include `drift_monitoring_report.md`,
`drift_metrics.csv`, `segment_monitoring_metrics.csv`, and `backtesting_metrics.csv`.

This layer complements model comparison and threshold calibration by observing score stability and
operational volumes over time. It does not retrain models, generate labels, or alter thresholds.

## Security Controls And Privacy Validation

Security validation produces a sensitive field inventory, permission matrix, secrets scan findings,
audit integrity checks, and a Markdown control report. The outputs are stored in governance tables
and mirrored under `reports/model_validation` for review with the rest of the validation pack.

Sensitive fields are classified from table-column metadata. Masking recommendations are
deterministic and configurable, with hashing for identifiers, redaction for direct contact details,
and preserve-last-four for operational IDs where useful. The local fallback salt is suitable only
for development and should be replaced by an environment-provided salt for reviewed runs.

Security results should be interpreted as local control evidence. Production deployment would still
need authentication, authorisation enforcement at the service and database layers, encryption,
managed secrets, and independent audit log retention.

## Release Readiness Validation Pack

Release readiness consolidates final validation evidence into a portfolio review pack. It checks
required validation reports, model cards, monitoring reports, governance inventory artefacts, and
security reports, then writes `release_validation_index.csv` and `release_readiness_report.md`.

The portfolio pack adds a dashboard walkthrough, command transcript template, architecture summary,
demo validation checklist, known limitations, and next-step narrative. Local-only release checks can
run without PostgreSQL; persisted runs add governance tables and audit events. This layer packages
existing validation evidence only and does not run analytical workflows or change thresholds.
