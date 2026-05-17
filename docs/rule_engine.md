# Rule Engine

The rule engine package contains deterministic AML rules that read cleaned staging data, emit the
common alert schema, optionally persist alerts, and write governance audit events.

## Implemented Rule

Current implemented rule:

- `Structuring`: repeated outbound transfers below a reporting threshold within a rolling window.
- `Fan-in`: many unique sending accounts transferring into one receiving account within a rolling
  window.
- `Fan-out`: one sending account transferring to many unique recipients within a rolling window.
- `Rapid movement`: incoming funds quickly sent onward by the same account.
- `Dormant reactivation`: long inactivity followed by high-value outbound activity.
- `Circular flow`: directed transaction cycles within a configurable hop limit.

## Common Inputs

Rules currently read:

- `staging.transactions`
- `staging.accounts`

Rules require transaction ID, sender account ID, transaction timestamp, amount, and transaction
type. Fan-in requires receiver account ID. Fan-out requires receiver account ID and counterparty ID
so it can build a recipient key from internal account recipients or external counterparties. Account
records are used to attach customer IDs to generated alerts. Rapid movement uses receiver account
IDs for inbound value and sender account IDs plus receiver or counterparty recipients for outflows.
Dormant reactivation uses all account activity to establish inactivity and high-value sender-side
outflows for reactivation detection. Circular flow detection builds directed account edges from
staged transactions, and circular flow alert conversion also reads staged accounts for customer ID
attachment.

## Common Outputs

Rules emit `AlertRecord` objects with:

- deterministic `alert_id`
- `account_id` and optional `customer_id`
- `rule_name` and `typology`
- `severity` and `risk_score_rule`
- human-readable `reason_code`
- evidence transaction IDs
- detection window start and end

## Persistence And Audit

When persistence is requested, alerts are upserted into `aml.alerts` through the common alert
persistence layer. Rule execution writes `governance.audit_events` with rule name, generated alert
count, persisted alert count, and threshold metadata.

## CLI Usage

```bash
python scripts/run_structuring_rule.py run
python scripts/run_structuring_rule.py run --persist
python scripts/run_structuring_rule.py run --limit 1000
python scripts/run_structuring_rule.py run --reporting-threshold 10000 --min-transaction-count 8
python scripts/run_fan_in_rule.py run
python scripts/run_fan_in_rule.py run --persist
python scripts/run_fan_in_rule.py run --min-unique-senders 15 --window-days 7
python scripts/run_fan_out_rule.py run
python scripts/run_fan_out_rule.py run --persist
python scripts/run_fan_out_rule.py run --min-unique-recipients 20 --window-days 7
python scripts/run_rapid_movement_rule.py run
python scripts/run_rapid_movement_rule.py run --persist
python scripts/run_rapid_movement_rule.py run --outflow-window-hours 48 --min-outflow-ratio 0.90
python scripts/run_dormant_reactivation_rule.py run
python scripts/run_dormant_reactivation_rule.py run --persist
python scripts/run_dormant_reactivation_rule.py run --dormant-days-threshold 120 --min-total-outbound-amount 10000
```

## Makefile Usage

```bash
make run-structuring-rule
make run-structuring-rule-persist
make run-structuring-rule-limited
make run-fan-in-rule
make run-fan-in-rule-persist
make run-fan-in-rule-limited
make run-fan-out-rule
make run-fan-out-rule-persist
make run-fan-out-rule-limited
make run-rapid-movement-rule
make run-rapid-movement-rule-persist
make run-rapid-movement-rule-limited
make run-dormant-reactivation-rule
make run-dormant-reactivation-rule-persist
make run-dormant-reactivation-rule-limited
```

## Unified Rule Registry And Runner

The unified engine registers deterministic AML rules as `RuleDefinition` records. Each definition
contains a canonical rule key, rule name, typology, config class, in-memory runner, staged runner,
and capability flags such as circular-flow artefact support.

`DEFAULT_RULE_ORDER` is:

- `structuring`
- `fan_in`
- `fan_out`
- `rapid_movement`
- `dormant_reactivation`
- `circular_flow`

Rule key aliases support common CLI spellings such as `fan-in`, `fan-out`, `rapid-movement`,
`dormant-reactivation`, and `circular-flow`. `config/rules.yaml` drives rule enablement and
threshold construction. The config loader supports the nested circular-flow detection and alert
settings while preserving flat detection settings for older local config files.

The in-memory engine runs selected rule callables against DataFrames without persistence, audit, or
artefact writes. The staged engine reuses each individual `run_*_rule_from_staged` workflow, passes
through persistence and audit flags, and lets those workflows perform alert upserts when persistence
is enabled. This avoids duplicate alert persistence. The engine aggregates alerts, generated and
persisted counts, unique account counts, rule counts, typology counts, and circular-flow artefact
paths.

Individual rule audit events remain rule-specific. The unified staged workflow can additionally
write one engine-level `governance.audit_events` row with `event_type = rule_engine_execution` and
`action = run_aml_rule_engine`.

CLI and Makefile usage:

```bash
python scripts/run_aml_rules.py list
python scripts/run_aml_rules.py run
python scripts/run_aml_rules.py run --rules structuring fan-in fan-out
python scripts/run_aml_rules.py run --exclude-rules circular-flow
python scripts/run_aml_rules.py run --persist
python scripts/run_aml_rules.py run --limit 1000
make rules-list
make run-aml-rules
make run-aml-rules-persist
make run-aml-rules-limited
make run-aml-rules-no-artefacts
```

## Fan-In Rule

Fan-in reads `staging.transactions` and `staging.accounts`. Candidate filtering keeps internal
account receipts with valid sender and receiver accounts, excludes self-transfers, filters to
configured transaction types, and sets the canonical alert `account_id` to the receiving account.

Rolling-window detection counts unique senders per receiver within `window_days`, applies
`min_total_amount`, keeps evidence transaction IDs, and emits the strongest overlapping window per
receiving account. Alerts persist to `aml.alerts` through the common alert persistence layer. Rule
execution audit events use `action = run_fan_in_rule`.

## Fan-Out Rule

Fan-out reads `staging.transactions` and `staging.accounts`. Candidate filtering keeps outbound
transactions with a valid sending account and a recipient key from either `receiver_account_id` or
`counterparty_id`, excludes self-transfers, filters to configured transaction types, and sets the
canonical alert `account_id` to the sending account.

Rolling-window detection counts unique recipients per sender within `window_days`, applies
`min_total_amount`, keeps evidence transaction IDs, and emits the strongest overlapping window per
sending account. Alerts persist to `aml.alerts` through the common alert persistence layer. Rule
execution audit events use `action = run_fan_out_rule`.

## Rapid Movement Rule

Rapid movement reads `staging.transactions` and `staging.accounts`. Inbound filtering keeps
transactions with a valid receiving account and configured inbound transaction type. Outbound
filtering keeps transactions from the same account to either an internal receiver or external
counterparty recipient, excludes self-transfers, and applies configured outbound transaction types.

Detection uses each inbound timestamp as a rolling window start, aggregates same-account inbound
and outbound value within `outflow_window_hours`, and triggers when total received, outgoing
transaction count, outflow ratio, and retained ratio thresholds are met. Alerts contain inbound
evidence IDs followed by outbound evidence IDs and persist to `aml.alerts` through the common alert
persistence layer. Rule execution audit events use `action = run_rapid_movement_rule`.

## Dormant Reactivation Rule

Dormant reactivation reads `staging.transactions` and `staging.accounts`. Activity history includes
sender-side outbound activity and receiver-side inbound activity. Candidate filtering keeps
high-value outbound transactions with a valid sending account and recipient, excludes self-transfers,
and honours internal-account and counterparty outflow source configuration.

Detection finds the most recent prior activity before each outbound candidate, computes the
calendar-day dormant period, and aggregates qualifying outbound candidates inside the configured
reactivation window. It triggers when the dormant period, outbound transaction count, and total
outbound value thresholds are met. Alerts contain prior activity evidence followed by reactivation
evidence IDs and persist to `aml.alerts` through the common alert persistence layer. Rule execution
audit events use `action = run_dormant_reactivation_rule`.

## Future Extensions

Later tickets add graph-based features, formal rule artefacts, and model-generated alerts. Those
components should reuse the same alert schema and audit patterns.

## Circular Flow Rule

Circular flow has two workflows. The detection-only workflow reads `staging.transactions`, prepares
qualifying transaction rows as directed edges from `sender_account_id` to `receiver_account_id`, and
writes local detection artefacts. The alert-producing workflow reads both `staging.transactions` and
`staging.accounts`, runs detection, converts detections into common `AlertRecord` outputs, and can
persist alerts to `aml.alerts`.

Detection builds a NetworkX `MultiDiGraph` for transaction evidence and a simple directed graph for
cycle search. Simple cycles are canonicalised by rotating the lexicographically smallest account to
the start while preserving direction. Evidence extraction then selects all transaction rows for each
directed cycle step, producing deterministic cycle IDs, evidence IDs, and cycle paths such as
`ACC_A -> ACC_B -> ACC_C -> ACC_A`.

The detection-only staged runner can write local artefacts to `reports/model_validation`:

- `circular_flow_detections.json`
- `circular_flow_detections.csv`
- `circular_flow_summary.json`

The alert-producing workflow additionally writes:

- `circular_flow_alerts.json`

Circular flow alerts use the canonical cycle primary account as `account_id`, attach `customer_id`
from staged accounts where available, preserve cycle transaction IDs as `evidence_ids`, and use
reason codes that summarise cycle length, total amount, and time span. Detection-only audit events
use `action = detect_circular_flows`; alert-producing rule executions use
`action = run_circular_flow_rule`.

CLI and Makefile usage:

```bash
python scripts/detect_circular_flows.py run
python scripts/detect_circular_flows.py run --limit 1000
python scripts/detect_circular_flows.py run --max-cycle-hops 4 --max-time-span-hours 168
python scripts/run_circular_flow_rule.py run
python scripts/run_circular_flow_rule.py run --persist
python scripts/run_circular_flow_rule.py run --limit 1000
make detect-circular-flows
make detect-circular-flows-limited
make detect-circular-flows-no-artefacts
make run-circular-flow-rule
make run-circular-flow-rule-persist
make run-circular-flow-rule-limited
```

## Structuring Fixture Test Coverage

Structuring fixture tests are intentionally small and deterministic. They complement the
scenario-generation tests by isolating thresholds, rolling-window boundaries, evidence IDs, reason
codes, counterparty handling, invalid inputs, and deterministic alert IDs. The tests protect the
common alert schema contract and run without live services.

## Fan-In And Fan-Out Fixture Test Coverage

Fan-in and fan-out fixture tests are intentionally small and deterministic. They complement
scenario-generation tests by isolating collection-account and dispersion-account patterns without
requiring live services. Joint fixture tests protect against cross-rule leakage, evidence ID
contamination, and alert ID collisions while preserving the common `AlertRecord` contract.

## Rapid Movement And Dormant Reactivation Fixture Test Coverage

Rapid movement and dormant reactivation fixture tests are intentionally small and deterministic.
They complement scenario-generation tests by isolating pass-through account behavior, dormancy gaps,
reactivation windows, ratio thresholds, and outbound value thresholds without requiring live
services. Joint fixture tests protect against cross-rule leakage between rapid movement and dormant
reactivation evidence, preserve deterministic alert ID behavior, and protect the common
`AlertRecord` schema contract.

## Circular Flow Fixture Test Coverage

Circular flow fixture tests are intentionally small and deterministic. They complement scenario
generation tests by isolating hop limits, cycle canonicalisation, evidence extraction,
counterparty-like edge handling, serialisation, local artefact writing, alert conversion, customer ID
attachment, and common alert validation without requiring live services.

## Rule Documentation Generation

AML rule documentation is generated from typed metadata in the rules package. Coverage validation
checks every registered deterministic rule for business purpose, detection logic, inputs,
thresholds, rationale, evidence semantics, reason code format, scoring logic, limitations, example
alerts, and validation tests.

Documentation generation is independent from staged data and database connectivity. The CLI exposes
list, validate, and generate commands:

```bash
python scripts/generate_rule_documentation.py list
python scripts/generate_rule_documentation.py validate
python scripts/generate_rule_documentation.py generate
make generate-rule-docs
```

Generated Markdown pages live under `docs/rules/`, and the JSON metadata artefact is written to
`reports/model_validation/aml_rule_documentation.json`.

## Relationship To Neo4j Graph Loading

Deterministic AML alerts will later be linked to graph nodes in Neo4j after staged graph loading is
implemented. The rule engine remains the alert producer; the graph layer will provide connected
customer, account, counterparty, transaction, alert, and case context for analytics and explanation.

Persisted AML alerts can now be loaded into Neo4j and connected to the flagged account and evidence
transactions. The rule engine still owns alert generation and persistence; the graph loader consumes
`aml.alerts` as graph input after rules have run.

Deterministic AML alerts are now graph-enriched after loading through account-level Neo4j graph
analytics features. The rule engine behaviour is unchanged; graph analytics consumes alert nodes
and relationships downstream to produce network context for later scoring.

Persisted AML alerts and persisted Neo4j graph analytics features can now be joined by `account_id`
for downstream account risk scoring. The rule engine remains unchanged and continues to own
deterministic alert generation.

Deterministic rule alerts now complement unsupervised Isolation Forest anomaly scores for
downstream case triage. Composite risk scoring will combine these separate artefacts in the next
layer without changing rule execution behaviour.

Composite account risk scoring now reads persisted `aml.alerts` as the rule-risk component and
combines it with graph features, anomaly scores, customer risk, and jurisdiction risk. Rule engine
behaviour remains unchanged; the scoring layer consumes persisted alert outputs by `account_id`.

## Relationship To Case Generation

Case generation consumes persisted `aml.alerts` after rule execution and groups them into
investigation cases by account, customer, graph community, circular flow, and common counterparty.
The rule engine still owns deterministic alert production only; generated cases are written by the
case layer to `aml.cases`, `aml.case_alerts`, and `aml.case_entities`.

## Relationship To Case Risk Scoring

Case risk scoring consumes generated cases and their linked `aml.alerts` rows. Alert severity and
`risk_score_rule` contribute the alert-risk component, but rule execution and alert persistence are
unchanged. The case risk layer persists formal triage scores to `aml.case_risk_scores` for analyst
lifecycle actions and future dashboard pages.

## Relationship To Case Evidence

Case evidence generation reads persisted rule alerts through case-alert links and carries alert IDs,
rule names, typologies, severity, reason codes, detection windows, and evidence IDs into
`aml.case_evidence_packs`. Deterministic explanations reference those alert fields through fixed
templates. The rule engine remains unchanged and is not invoked by the evidence CLI.
