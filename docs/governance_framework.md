# Governance Framework

## Governance Inventory And Lineage

The governance inventory provides a reproducibility layer over the AML project. It records table
lineage, configured process lineage, run dependency edges, local artefact registry entries, model
inventory, and validation inventory. Process lineage is configured in `config/governance.yaml` so
expected dependencies remain reviewable instead of hidden in code.

The inventory should be interpreted as a governance index over existing outputs. It uses persisted
tables, audit events, model and validation run metadata, and local validation/documentation files.
It does not prove every runtime column-level dependency unless supporting audit events or run
metadata exist. The artefact registry records file hashes, sizes, paths, and classifications to
support repeatable model risk review packs.

## Explainability Governance

The explainability layer converts persisted scores, labels, evidence packs, model comparison
outputs, and monitoring results into auditable feature attribution, score decomposition, reason
contribution, and model-card artefacts. It is a documentation and review layer only: it does not
train models, generate labels, call external APIs, or alter scoring thresholds.

Feature attribution uses stored supervised model metadata such as coefficients or tree importance
values where available. Local contribution rows are deterministic approximations and should be
interpreted as supporting evidence, especially for sparse reference data. Score decomposition
preserves existing component values and records missing component weights explicitly. Reason
contributions link rule, graph, anomaly, supervised, evidence, and label context to cases or
accounts where those persisted sources exist.

The consolidated model card documents intended use, data and label sources, model families,
validation results, threshold recommendations, monitoring status, limitations, and next steps.
Governance reviewers should treat missing attribution metadata as a model documentation gap rather
than as a runtime scoring failure.

Purpose: Define audit logging, reproducibility, human review, model risk controls, data lineage, validation evidence, and change management expectations.

## Data Dictionary

The generated data dictionary supports governance by documenting every raw, staging, mart, AML, and
governance table field with data type, business meaning, validation rules, examples, and lineage.
It provides a repeatable artefact for:

- data lineage review
- reproducibility checks
- model validation and model risk review
- feature review before modelling
- AML rule transparency
- auditability across ingestion, validation, staging, model, and case workflows

## Dataset Summary Artefacts

Exploratory dataset summaries add evidence about the generated or staged data values. They support:

- data quality review
- validation evidence
- model development readiness
- AML rule threshold review
- model risk documentation

## Feature Persistence Audit Events

Feature persistence writes governance audit events that support:

- feature lineage
- feature version tracking
- reproducibility
- later model run traceability
- model validation evidence

## Alert Persistence Audit Events

Alert persistence audit events support:

- rule execution traceability
- evidence lineage
- alert volume monitoring
- later case generation auditability
- model validation of alert quality

## Rule Execution Audit Events

Rule execution audit events support:

- rule run traceability
- threshold reproducibility
- alert volume monitoring
- evidence lineage
- later model validation of rule effectiveness

Fan-in rule execution audit events additionally support:

- collection-account risk traceability
- threshold reproducibility for unique sender counts
- evidence lineage for incoming transfers
- alert volume monitoring by receiving account
- later case grouping by common receiving account

Fan-out rule execution audit events additionally support:

- dispersion-account risk traceability
- threshold reproducibility for unique recipient counts
- evidence lineage for outgoing transfers
- alert volume monitoring by sending account
- later case grouping by common sending account

Rapid movement rule execution audit events additionally support:

- pass-through account risk traceability
- threshold reproducibility for outflow and retained ratios
- evidence lineage across inbound and outbound transaction sets
- alert volume monitoring by account and transaction flow pattern
- later case grouping by pass-through account behavior

Dormant reactivation rule execution audit events additionally support:

- dormant-account risk traceability
- threshold reproducibility
- prior-activity evidence lineage
- reactivation evidence lineage
- alert volume monitoring
- later case grouping by reactivated account

Circular flow detection artefacts and execution audit events additionally support:

- cycle detection traceability
- graph-like typology evidence
- threshold reproducibility
- transaction evidence lineage
- later case grouping by circular flow membership

Circular flow alert conversion audit events additionally support:

- cycle alert traceability
- transaction evidence lineage
- threshold reproducibility
- high-amount and long-cycle rule score review
- later case grouping by cycle membership

## Unified Rule Engine Audit

The unified rule engine writes a `rule_engine_execution` audit event when enabled. This event
supports:

- end-to-end deterministic rule execution traceability
- typology coverage monitoring
- total alert volume monitoring
- persisted alert count reconciliation
- reproducible rule configuration review
- later model validation and case generation traceability

## Formal AML Rule Documentation

Formal rule documentation supports:

- threshold reproducibility
- typology coverage review
- model risk review
- evidence lineage review
- false positive analysis
- change management
- future validation reporting

The Markdown rule pack and JSON metadata artefact provide auditable references for deterministic
rule definitions without requiring live services.

## Neo4j Connection And Constraint Utilities

Neo4j connection and constraint utilities support:

- graph data integrity
- repeatable graph construction
- evidence traceability
- constraint-backed node identity
- later graph analytics validation
- case graph explainability

This connection layer prepares graph connectivity and uniqueness constraints without running graph
analytics.

## Neo4j Graph Loading Governance

Graph loading supports:

- network evidence traceability
- alert-to-transaction lineage
- constraint-backed entity identity
- repeatable graph reconstruction
- graph reconciliation
- future graph feature validation

The loader preserves persisted alert evidence in Neo4j relationships without deleting graph data or
running analytics during the load step.

## Neo4j Graph Analytics Governance

Graph analytics artefacts support:

- network risk feature traceability
- feature reproducibility
- graph build validation
- alert proximity analysis
- community-based case grouping
- later model validation

The analytics layer writes local feature and summary artefacts only. It does not persist graph
features to PostgreSQL or alter Neo4j graph data.

## Graph Feature Persistence Governance

Persisting graph features supports:

- feature lineage
- graph build reproducibility
- feature version control
- network risk feature auditability
- model input traceability
- future validation reporting

The persistence workflow records feature date, feature version, graph build ID, graph database,
row counts, analytics metadata, and audit events so downstream models can be traced back to their
source graph build.

## Anomaly Scoring Governance

Isolation Forest anomaly scoring supports:

- unsupervised risk prioritisation
- feature lineage
- model version control
- score reproducibility
- MLflow experiment tracking
- score distribution monitoring
- future threshold validation

Persisted scores store model run ID, feature lineage, preprocessing metadata, model parameters,
metrics, and audit events so downstream risk scoring can explain which model and feature snapshot
produced each account score.

## Composite Account Risk Scoring Governance

Composite account risk scoring supports:

- transparent weighted component scoring
- score version control
- component coverage monitoring
- account risk score reproducibility
- audit event `risk_scoring`
- model and graph feature input traceability
- future case generation validation

Persisted scores retain configured weights, component scores, score date, score version, and
metadata in `mart.account_risk_scores`, making downstream case prioritisation explainable and
repeatable.

## Case Generation Governance

Case generation supports:

- deterministic alert grouping
- stable case IDs and case versions
- case evidence traceability
- audit event `case_generation`
- case-link reproducibility
- downstream case-level risk scoring validation

Generated cases are persisted to `aml.cases`, with alert and entity links in `aml.case_alerts` and
`aml.case_entities`. Audit details capture rows prepared, cases persisted, link counts, case
version, summary metrics, and caller metadata so case creation can be reproduced from the same
alerts and risk context.

## Case Risk Scoring Governance

Case risk scoring supports:

- formal case triage ranking
- configurable weighted component scores
- score version control
- audit event `case_risk_scoring`
- optional `aml.cases` snapshot updates
- evidence and component coverage monitoring
- future analyst lifecycle validation

Persisted scores in `aml.case_risk_scores` retain the configured weights, component values, score
date, score version, and metadata. The scoring workflow does not generate cases or change alert
semantics; it ranks already generated cases for downstream analyst workflow and dashboard pages.

## Case Evidence Governance

Case evidence generation supports:

- deterministic evidence packs and template explanations
- evidence version and explanation version control
- case, alert, transaction, account, graph, anomaly, and risk-score traceability
- evidence quality checks for missing alerts, transactions, graph features, and risk rows
- audit event `case_evidence_generation`
- future analyst lifecycle and Case Detail dashboard validation

Evidence packs persist to `aml.case_evidence_packs` with primary key
`case_id, evidence_version`. Explanations persist to `aml.case_explanations` with primary key
`case_id, explanation_version`. The explanation renderer uses fixed templates only; no LLM,
external API, or random phrasing is used.

## Case Lifecycle Governance

Case lifecycle actions support status changes, assignments, comments, closures, and archival.
Configured decision types include `assign`, `status_change`, `comment`, `escalate`,
`request_information`, `close_false_positive`, `close_suspicious`, `archive`, and `reopen`.
Closure actions require a decision reason and comment by default.

Lifecycle events are append-only in `aml.case_lifecycle_events`; current assignment state is stored
in `aml.case_assignments`; current status, assignee, queue, last decision reason, last decision
timestamp, and closure timestamp are additive snapshot fields on `aml.cases`. Every persisted
action writes audit event `case_lifecycle_action` when enabled, providing traceability for future
dashboard decision forms and analyst feedback labels.

## Dashboard Governance

The Streamlit dashboard reads persisted AML, case, evidence, explanation, and lifecycle records from
PostgreSQL. It does not launch upstream data preparation, rule execution, graph loading, model
training, risk scoring, case generation, or evidence generation workflows.

Case Detail lifecycle forms are the only mutating dashboard controls in this release. They call the
central case lifecycle backend, so status changes, assignments, and comments continue to write
`case_lifecycle_action` audit events when enabled. Future graph visualisation and account profile
pages should follow the same read-first pattern and route any mutation through audited backend
services.

Graph View and Account Profile now follow that read-first pattern. Graph View uses bounded
PostgreSQL reads over account risk, graph features, transactions, alerts, cases, and case entities
to render local network context; optional Neo4j helpers require an externally supplied driver and
are never connected at import time. Account Profile reads account/customer records, transaction
history, alert history, linked cases, behavioural features, graph features, anomaly scores, account
risk scores, and counterparties. These pages do not mutate lifecycle state or run upstream
pipelines.

Model Metrics, Audit Log, and Validation Report add the governance review layer. Model Metrics
reads persisted model runs, anomaly scores, account risk scores, and case risk scores to display
score distributions, ranked records, and precision@K status. Precision@K is computed only when a
binary label column exists; otherwise the dashboard marks rows as `label_unavailable`. Audit Log
reads `governance.audit_events` with component, event type, status, run ID, and text filters.
Validation Report browses local Markdown, JSON, CSV, and text artefacts under the configured report
directory and rejects path traversal. These pages are read-only and prepare the final end-to-end
demo polish layer.

## Demo Readiness Governance

The demo readiness pack supports reproducibility, execution traceability, validation artefact
indexing, local run evidence, portfolio review, model risk discussion, and auditability. It records
planned commands, dry-run and live run summaries, readiness checks for required files and packages,
database count validation, and local artefact indexes under `reports/model_validation`.

Reset behavior is deliberately explicit. The standard `demo-run` path does not reset PostgreSQL;
reset-enabled execution is isolated to `demo-run-with-reset` and the `--include-reset` CLI flag.

## Analyst Feedback Label Governance

Analyst feedback labels are sourced from audited case lifecycle closure decisions. `Closed
suspicious` is mapped to binary label `1`; `Closed false positive` is mapped to binary label `0`.
Open, escalated, information-requested, and archive-only states are excluded from label creation.

The label layer persists case labels to `aml.case_labels`, propagates account labels to
`aml.account_labels`, and writes supervised-readiness feature tables to
`mart.case_supervised_dataset` and `mart.account_supervised_dataset`. Persistence is idempotent by
versioned primary keys, and audit event `analyst_label_generation` records row counts, label
versions, dataset versions, quality summaries, and caller metadata.

Leakage controls require closure timestamps to follow case creation and feature timestamps to
precede labels where those timestamps are available. Reference and sparse analyst decisions remain
a known limitation; the outputs are intended for future supervised model training and threshold
recalibration, not for automatic model replacement in this ticket.

## Supervised Model Governance

The supervised AML baseline trains only from versioned analyst-label readiness datasets. Logistic
Regression provides an interpretable benchmark, while Random Forest is available for comparison
when label volume supports it. Training uses deterministic seeds, configured class weights for
imbalance, and time-aware validation splits by default.

Validation reports include precision, recall, F1, ROC-AUC, PR-AUC when both classes exist,
threshold metrics, and precision/recall@K. Scores are written to
`mart.supervised_model_scores`; model run metadata is written to
`governance.supervised_model_runs`; audit event `supervised_model_training` records persistence
counts, model version, dataset version, artefact paths, and summary metrics.

This supervised layer complements the existing Isolation Forest and composite score controls. It
does not alter rule scoring, anomaly scoring, account risk scoring, or case risk scoring semantics.

## Model Comparison Governance

Model comparison provides auditable champion-challenger evidence across case risk, supervised,
account risk, and anomaly score candidates when labelled entities exist. Threshold calibration
documents operating points using minimum precision and recall constraints, F1, and review volume.

Single-class or sparse-label outputs are treated as model risk limitations, not production approval
evidence. The workflow validates existing scores only and does not retrain models, generate labels,
or alter scoring logic.
## Monitoring And Drift Governance

The monitoring layer supports AML model risk review by documenting whether persisted scores, alert
volumes, case volumes, and segment behaviour remain stable across time. Baseline and comparison
windows are built from local persisted timestamps, and drift metrics include PSI, KS statistic,
mean shift, median shift, and categorical distribution shift.

Segment monitoring reviews available customer segment, jurisdiction, risk-band, typology, and rule
slices. Backtesting reports time-window metrics such as precision@K, recall@K, alert count, case
count, positive rate, and high-risk share where labels and scores exist. Sparse labels and reference
data are treated as limitations, not as production-grade performance evidence.

Monitoring artefacts are written to `reports/model_validation`, and persisted results live in the
`governance` schema. The workflow observes existing outputs only; it does not retrain models,
generate labels, change thresholds, or mutate scoring decisions.

## Security And Privacy Governance

The security control layer records local-first safeguards for sensitive AML data and analyst
actions. Column names are classified as public, internal, confidential, or restricted using
configured patterns. Recommended masking strategies include deterministic hashing, redaction,
preserve-last-four, and no masking for non-sensitive fields.

Role policies define viewer, analyst, senior analyst, governance reviewer, and admin actions.
Dashboard lifecycle actions can call the permission helpers before status changes, assignments,
comments, closures, or archival. CSV exports use sanitised mode by default, remove blocked columns,
and block sensitive exports unless explicitly enabled and authorised.

Local secrets scanning covers configured source, config, and documentation directories with file
extension and size controls. Findings store redacted previews only. Audit integrity checks validate
required audit columns, status values, and duplicate event signatures. These controls document
local safeguards and a production hardening roadmap; they do not replace identity management,
database encryption, secrets management, or independent audit retention.

## Release Readiness Governance

The release readiness layer records final portfolio evidence for review. Repository hygiene checks
confirm required files, required directories, forbidden local paths, and Makefile targets.
Documentation checks confirm required governance, validation, and walkthrough documents plus key
section strings. Artefact checks inspect the local validation report directory and produce a final
validation index.

Persisted release outputs live under the `governance` schema and are linked to audit events with
`event_type = release_readiness`. The evidence pack complements governance inventory and security
controls by showing what evidence exists and how a reviewer can reproduce the demo manually. It is
configured lineage and documentation evidence, not a production approval process.
