# Portfolio Walkthrough

## Governance Inventory Walkthrough

The governance inventory demonstrates how the project can answer model risk questions about
source tables, process dependencies, generated artefacts, model versions, validation versions, and
reproducibility metadata. Run `make governance-inventory-run-persist` after the demo, supervised
model, comparison, monitoring, and explainability layers have produced outputs. Review
`reports/model_validation/governance_inventory_report.md` and the companion CSV/JSON artefacts for
lineage nodes, lineage edges, artefact hashes, process inventory, model inventory, and validation
inventory.

This layer is observational: it documents existing persisted state and local artefacts. It does
not re-run pipelines, generate labels, retrain models, or alter triage thresholds.

## Explainability Walkthrough

After labels, supervised scores, model comparison, and monitoring have been persisted, run
`make explainability-run-persist` to produce the portfolio-grade explanation pack. The pack includes
global feature importance, local feature contributions where metadata exists, case and account score
decomposition, reason contribution rows, an explainability summary JSON file, and
`reports/model_validation/consolidated_model_card.md`.

Use the model card to explain the system purpose, intended use, label source, model families,
threshold recommendations, monitoring findings, reference data limitations, and recommended next
steps. Use score decomposition and reason contributions to show why a high-risk case or account was
prioritised while preserving the existing deterministic case explanations and score weights.

## Project Purpose

Graph-Based AML Case Triage and Risk Scoring System is a local-first portfolio project that
demonstrates how reference financial activity can be transformed into AML alerts, graph analytics,
case risk scores, evidence packs, analyst lifecycle records, and dashboard views.

## Local-First Architecture

The stack uses PostgreSQL for persisted facts and marts, Neo4j for graph loading and analytics,
Python for deterministic rules and scoring, and Streamlit for local analyst review. The project is
designed to run from local commands and reference data without cloud services or external APIs.

## Data Pipeline

Reference customer, account, and transaction data is generated, validated, loaded to raw tables,
and staged into PostgreSQL. Validation artefacts document row counts, schema checks, and local
quality results.

## AML Rule Engine

Deterministic AML typology rules generate persisted alerts with stable IDs, evidence transaction
references, reason codes, severity, and risk scores. The unified rule engine keeps rule execution
auditable and repeatable.

## Neo4j Graph Analytics

Persisted transactions and alerts can be loaded into Neo4j. Graph analytics compute communities,
centrality, component context, and other graph features that are also persisted back to PostgreSQL
for scoring and dashboard use.

## Anomaly and Risk Scoring

Isolation Forest anomaly scores, composite account risk scores, and case-level risk scores are
versioned and persisted. Score distributions and ranked records are available through the dashboard
and validation artefacts.

## Case Triage

Case generation groups related alerts into deterministic cases, then case risk scoring ranks those
cases for review. Case evidence packs collect typologies, alerts, transactions, account context,
graph context, risk drivers, chronology, and recommended review focus. Explanations use fixed
templates only; no LLM is used.

## Case Lifecycle

Analyst workflow support includes status changes, assignments, comments, closure decisions, and
append-only lifecycle events. Every persisted action writes an audit event when audit is enabled.

## Analyst Feedback Labels

Reviewed closure outcomes can be converted into supervised-learning-ready labels. `Closed
suspicious` becomes label `1`, and `Closed false positive` becomes label `0`. The label layer
creates case labels, propagates account labels from primary and related accounts, joins available
risk and graph features, and writes versioned readiness datasets without training a supervised
model.

## Supervised Baseline Models

The supervised baseline trains from the analyst-label readiness datasets. Logistic Regression acts
as the transparent benchmark for model risk discussion, while Random Forest is available as a
stronger comparison model. Training uses deterministic splits, class imbalance controls,
precision/recall@K, threshold metrics, PR-AUC where valid, model cards, local joblib artefacts,
and PostgreSQL score/run persistence.

## Dashboard Pages

The Streamlit dashboard includes Overview, Alert Queue, Case Queue, Case Detail, Graph View,
Account Profile, Model Metrics, Audit Log, and Validation Report pages. Pages read persisted data
and local artefacts; only explicit Case Detail lifecycle forms mutate state.

## Governance and Audit Controls

Audit events cover ingestion, validation, rules, graph, model, scoring, cases, evidence, lifecycle,
and dashboard checks. Model and validation pages support model risk discussion by showing run
metadata, score distributions, precision@K fallback rows when labels are unavailable, and local
validation report previews.

## Demo Commands

```bash
cp .env.example .env
make services-up
make demo-readiness
make demo-plan
make demo-run-dry
make demo-run
make demo-validate
make demo-artefacts
make dashboard
```

Use `make demo-run-with-reset` only when intentionally resetting local PostgreSQL state.

## Known Limitations

The project uses reference data, deterministic rules, unsupervised scoring, and sparse analyst
labels. Precision metrics are limited unless binary analyst labels are present. The system is
a local portfolio implementation, not a production monitoring platform.

## Future Extensions

## Model Comparison And Champion Selection

The validation layer compares persisted case, account, anomaly, and supervised score candidates
against analyst feedback labels. It reports precision, recall, F1, ROC-AUC, PR-AUC, precision@K,
recall@K, and threshold review volume, then recommends operating thresholds and selects a champion
candidate for portfolio discussion.

It is deliberately validation-only: no models are retrained and no analyst labels are generated.

## Future Extensions

Natural next steps include richer graph visualisation, account profile drill-downs, automated demo
screenshots, and controlled deployment packaging.
## Monitoring And Stability Validation

The portfolio demo includes a monitoring validation pack for feature drift, score drift, alert
volume drift, case volume drift, segment stability, and backtesting. It compares baseline and
comparison windows from local persisted timestamps and reports PSI, KS statistic, mean shift,
median shift, categorical distribution shift, high-risk share, precision@K, recall@K, and volume
change metrics where data exists.

Segment analysis covers customer segment, jurisdiction, typology, rule, and risk-band slices when
those fields are available. Backtesting summarises time-window behaviour without retraining models
or changing thresholds. Monitoring artefacts are written to `reports/model_validation` and
persisted to the `governance` schema for auditability.

## Security Controls And Privacy Safeguards

The portfolio demo now includes a local security controls pack. It inventories sensitive fields,
shows recommended masking strategies, documents role-action permissions, validates privacy-safe
exports, scans local files for redacted secret-like findings, and checks audit event integrity.

The Validation Report page can preview `security_control_report.md`,
`sensitive_field_inventory.csv`, `security_permission_matrix.csv`, `secrets_scan_findings.csv`,
`audit_integrity_checks.csv`, and `security_control_summary.json` when they exist. These controls
strengthen financial-systems review evidence while staying local-only: they do not add production
SSO, database encryption, cloud secrets management, or external API calls.

## Release Readiness And Final Evidence Pack

The final portfolio layer creates a release readiness checklist and evidence pack for reviewers.
Repository checks cover required files, directories, forbidden paths, and Makefile targets.
Documentation checks verify walkthrough and governance documents. Artefact checks index model cards,
validation reports, monitoring outputs, explainability outputs, governance inventory, and security
controls.

The release pack writes `portfolio_summary.md`, `architecture_summary.md`,
`dashboard_walkthrough.md`, `command_transcript_template.md`, and
`demo_validation_checklist.md` under `reports/model_validation/release_pack`. These files describe
the local-first architecture, dashboard review path, reproducible command transcript, limitations,
and next steps without re-running any upstream workflow.
