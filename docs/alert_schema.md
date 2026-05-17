# Common Alert Schema

The common alert schema standardises the records emitted by future AML rule engines, graph alerting,
model alerting, and manual review workflows.

## Alert Fields

Each alert record contains:

- `alert_id`: deterministic or externally supplied alert identifier.
- `account_id`: primary account associated with the alert.
- `customer_id`: optional owning customer identifier.
- `rule_name`: rule, model, graph, or manual trigger name.
- `typology`: AML typology such as structuring, fan-in, fan-out, rapid movement, circular flow, or
  dormant reactivation.
- `severity`: one of `low`, `medium`, `high`, or `critical`.
- `risk_score_rule`: rule-level score from `0` to `100`.
- `reason_code`: stable machine-readable explanation code.
- `evidence_ids`: transaction or entity identifiers supporting the alert.
- `detection_window_start` and `detection_window_end`: optional timestamp bounds for the evidence.
- `model_run_id`: optional model lineage reference.
- `alert_status`: human review lifecycle status.
- `created_at` and `updated_at`: UTC ISO timestamps.

## Severity Values

Valid severity values are:

```text
low
medium
high
critical
```

## Status Values

Valid alert statuses are:

```text
New
In review
Escalated
Information requested
Closed false positive
Closed suspicious
Archived
```

## Evidence ID Semantics

`evidence_ids` must contain at least one identifier. For rule alerts these will usually be
transaction IDs; graph and model alerts may also reference accounts, counterparties, devices, or
feature rows when later tickets add those paths.

## Detection Window Semantics

Detection windows are optional but must be parseable timestamps when present. When both bounds are
provided, the start must be less than or equal to the end.

## Deterministic Alert IDs

`build_alert_id` creates stable IDs from rule name, account ID, detection window start, and sorted
evidence IDs. `build_sequential_alert_id` is available for deterministic fixture or manual IDs.

## PostgreSQL Persistence

Alerts persist to:

```text
aml.alerts
```

Persistence uses `alert_id` as the upsert key and updates non-key alert columns on conflict.

## Audit Event Writing

Alert persistence writes `governance.audit_events` rows with:

- `event_type = alert_persistence`
- `component = alerts`
- `action = persist_alerts`

Audit details include alert count, rule name counts, severity counts, and optional metadata.

## Relationship To Future Rule Engines

Future typology rules must emit `AlertRecord` objects or alert DataFrames matching this schema.
The structuring, fan-in, fan-out, rapid movement, dormant reactivation, and circular flow rules now
produce common `AlertRecord` outputs.

Circular flow alerts use the canonical cycle primary account as `account_id`. Evidence IDs contain
the transaction IDs selected for the directed cycle path, and reason codes summarise cycle length,
total amount, and time span.

The unified AML rule engine aggregates `AlertRecord` outputs from all deterministic rules before
optional persistence to `aml.alerts`. Individual rule workflows still own the actual upsert step
when persistence is requested, which prevents duplicate persistence.

Formal rule documentation pages include the common `AlertRecord` fields and an example alert
dictionary aligned with the `aml.alerts` schema for each deterministic typology.

When alerts are loaded into Neo4j, `AlertRecord.evidence_ids` are used to create
`INVOLVES_TRANSACTION` relationships from `Alert` nodes to supporting `Transaction` nodes. The same
evidence transaction IDs can also trigger inverse transaction-to-alert graph links for analyst
navigation.

Alert nodes and alert-to-transaction relationships are used by graph analytics to compute alert
proximity features such as direct alert counts, high-risk alert counts, and shortest path to
flagged activity.

Alert proximity graph features are persisted in `mart.graph_features` and can be used alongside
alert severity and typology counts for downstream account risk scoring.

Alert outputs, graph features, and anomaly scores are separate artefacts. They are joined later by
`account_id` during composite risk scoring rather than being merged inside the alert schema layer.

Composite account risk scoring now joins persisted alerts, graph features, and anomaly scores by
`account_id`. Alert severity and `risk_score_rule` drive the rule-risk component, while alert counts
and high-severity counts are carried through to `mart.account_risk_scores` for case generation.

## Relationship To Case Generation

Case generation consumes persisted `aml.alerts` rows and groups them with account risk, graph
community, and transaction evidence into deterministic case records. Cases are stored separately in
`aml.cases`, with links in `aml.case_alerts` and `aml.case_entities`; alert schema utilities still
only define alert-level fields.

## Relationship To Case Risk Scoring

Case risk scoring joins generated case links back to `aml.alerts` to compute the alert-risk and
typology-diversity components. Alert records, graph features, anomaly scores, account risk scores,
and generated cases remain separate artefacts; they are combined only by readback utilities when
writing `aml.case_risk_scores`.

## Relationship To Case Evidence

Case evidence packs consume persisted alert fields without changing alert schema semantics. Alert
evidence includes alert ID, rule name, typology, severity, risk score, reason code, detection
window, and evidence transaction IDs. These fields are rendered into deterministic explanations and
stored separately in `aml.case_evidence_packs` and `aml.case_explanations` for future dashboard
case detail pages.

## Relationship To Case Lifecycle

Case lifecycle actions operate on generated `aml.cases` rows and do not change alert schema
semantics. Analyst status changes, assignments, comments, closures, and archival are recorded in
`aml.case_lifecycle_events`, with assignment state in `aml.case_assignments` and current snapshots
on `aml.cases`. These records will support future dashboard decision forms and analyst feedback
labels while keeping alert records immutable.

## Dashboard Alert Queue

The Streamlit Alert Queue page reads `aml.alerts` directly and displays alert ID, account ID,
customer ID, rule name, typology, severity, rule risk score, reason code, evidence IDs, and created
timestamp where available. It supports severity and typology filters plus account search.

The dashboard does not mutate alerts. Case Detail shows linked alerts through `aml.case_alerts`,
while lifecycle actions remain case-level decisions recorded separately in lifecycle tables.

## Dashboard Graph And Account Usage

Graph View reads `aml.alerts` as graph context only. Alert rows can become alert nodes linked to
flagged accounts and case context, while supporting transaction evidence remains traceable through
alert evidence IDs and `staging.transactions`.

Account Profile reads alert history for a selected account and joins it with transactions, linked
cases, risk scores, anomaly scores, and graph features. These dashboard pages do not alter alert
schema semantics or write alert updates.

## Dashboard Governance Pages

Model Metrics and Validation Report pages may display alert-derived risk-score coverage and local
validation artefacts, but they do not change alert records. Audit Log reads
`governance.audit_events` and can show alert persistence or rule-engine events alongside model,
case, and lifecycle events for traceability.
