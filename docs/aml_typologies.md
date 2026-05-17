# AML Typologies

Purpose: Explain the AML typologies targeted by the MVP, including structuring, fan-in, fan-out, rapid movement, circular flow, and dormant reactivation.

## Common Alert Schema

All typology rules must emit the common alert schema:

```text
alert_id
account_id
customer_id
rule_name
typology
severity
risk_score_rule
reason_code
evidence_ids
detection_window_start
detection_window_end
model_run_id
```

## Structuring

Structuring, also known as smurfing, is the repeated movement of funds in amounts just below a
reporting threshold. The implemented deterministic rule looks for outbound `transfer` or `wire`
transactions from the same account where:

- `amount >= reporting_threshold * below_threshold_margin`
- `amount < reporting_threshold`
- at least `min_transaction_count` transactions occur within `window_hours`

Default configuration:

```text
reporting_threshold = 10000.0
below_threshold_margin = 0.90
min_transaction_count = 8
window_hours = 24
severity = high
base_risk_score = 80.0
high_count_risk_score = 90.0
```

Each alert records the evidence transaction IDs, the detection window start and end, and a reason
code such as `8 transfers below threshold within 24 hours`. The rule uses a higher score when the
transaction count is at least `min_transaction_count * high_count_multiplier`.

Known limitations: the MVP keeps one strongest overlapping window per account, uses staged
transaction data only, and does not yet combine structuring evidence with graph, peer-group, or case
history context. Labelled scenario labels provide evaluation data, but the rule does not require
labels to detect candidates.

### Fixture Coverage

Structuring fixture tests cover:

- exact trigger cases
- below-threshold boundary inclusion
- reporting-threshold exclusion
- rolling-window start and end boundaries
- multiple triggering accounts
- counterparty payments
- deterministic alert IDs
- scenario-label alignment with reference structuring injections

## Fan-In

Fan-in describes collection-account behavior where many sending accounts transfer value into one
receiving account over a short period. The implemented deterministic rule looks for inbound
`transfer` or `wire` transactions where:

- `receiver_account_id` is present
- `sender_account_id != receiver_account_id`
- at least `min_unique_senders` unique senders are observed within `window_days`
- total value in the window is at least `min_total_amount`

Default configuration:

```text
min_unique_senders = 15
window_days = 7
min_total_amount = 0.0
severity = high
base_risk_score = 80.0
high_sender_risk_score = 90.0
```

Each alert records the receiving account, evidence transaction IDs, detection window start and end,
and a reason code such as `15 unique senders within 7 days`. The rule uses a higher score when the
unique sender count is at least `min_unique_senders * high_sender_multiplier`.

Known limitations: the MVP keeps one strongest overlapping window per receiving account, uses
staged account-to-account receipts, and does not yet enrich fan-in evidence with graph communities,
shared devices, or case history. Reference fan-in labels provide deterministic evaluation data, but
the rule does not require labels to detect candidates.

### Fixture Coverage

Fan-in fixture tests cover:

- exact trigger and one-below-threshold non-trigger cases
- duplicate sender handling
- rolling-window boundaries and overlapping-window selection
- multiple receiving accounts
- internal account receipt handling
- evidence isolation from fan-out-only activity
- deterministic alert IDs
- scenario-label alignment with reference fan-in injections

## Fan-Out

Fan-out describes dispersion-account behavior where one sending account transfers value to many
unique recipients over a short period. The implemented deterministic rule looks for outbound
`transfer` or `wire` transactions where:

- `sender_account_id` is present
- a recipient key exists from `receiver_account_id` or `counterparty_id`
- self-transfers are excluded
- the recipient source is enabled by configuration
- `amount > 0`

Rolling-window detection uses each candidate transaction timestamp as a window start and includes
transactions where `window_start <= transaction_timestamp <= window_start + window_days`. The
default threshold is `20` unique recipients within `7` days, with optional `min_total_amount`
filtering. The MVP keeps one strongest overlapping window per sending account, prioritising unique
recipient count, transaction count, total amount, and earliest window start.

Fan-out alerts use the common `AlertRecord` schema with:

- rule name `Fan-out`
- typology `fan_out`
- default severity `high`
- base rule score `80.0`
- high-recipient score `90.0` when recipient count reaches the configured multiplier
- reason code such as `20 unique recipients within 7 days`
- evidence transaction IDs from the detected window

Known limitations: the MVP does not yet enrich fan-out evidence with shared devices, recipient
network structure, graph communities, or historical case context. Reference fan-out labels provide
deterministic evaluation data, but the rule does not require labels to detect candidates.

### Fixture Coverage

Fan-out fixture tests cover:

- exact trigger and one-below-threshold non-trigger cases
- duplicate recipient handling
- rolling-window boundaries and overlapping-window selection
- multiple sending accounts
- internal account and counterparty recipient handling
- evidence isolation from fan-in-only activity
- deterministic alert IDs
- scenario-label alignment with reference fan-out injections

## Rapid Movement

Rapid movement describes pass-through behavior where an account receives value and quickly sends a
high proportion of that received value onward. The implemented deterministic rule treats inbound
transactions as `receiver_account_id` activity and outbound transactions as `sender_account_id`
activity with either an internal receiver account or external counterparty recipient.

For each inbound transaction timestamp, the rule opens a window where
`window_start <= transaction_timestamp <= window_start + outflow_window_hours`. It aggregates
same-account inbound and outbound value inside that window and triggers when:

- total received is at least `min_total_received`
- outbound transaction count is at least `min_outgoing_transaction_count`
- `total_sent_out / total_received >= min_outflow_ratio`
- `max(total_received - total_sent_out, 0) / total_received <= max_retained_ratio`

Default configuration:

```text
outflow_window_hours = 48
min_total_received = 1000.0
min_outflow_ratio = 0.90
max_retained_ratio = 0.10
severity = high
base_risk_score = 80.0
high_ratio_risk_score = 90.0
```

Each alert records the pass-through account, inbound and outbound evidence transaction IDs,
detection window start and end, and a reason code such as
`90 percent of received value sent out within 48 hours`. The rule uses the high ratio score when
the outflow ratio is at least `high_ratio_threshold`.

Known limitations: the MVP keeps one strongest overlapping window per account, uses staged
transaction data only, and does not yet reason about prior balance, fees, graph path continuity, or
case history. Reference rapid movement labels provide deterministic evaluation data, but the rule
does not require labels to detect candidates.

### Fixture Coverage

Rapid movement fixture tests cover:

- exact trigger and one-below-threshold non-trigger cases
- outflow ratio boundary
- retained ratio boundary
- rolling-window and reactivation-window boundary fixtures shared with dormant tests
- multiple pass-through accounts
- counterparty and internal-account outflows
- evidence isolation and deterministic alert IDs
- cross-rule separation from dormant reactivation evidence
- scenario-label alignment with reference rapid movement injections

## Dormant Reactivation

Dormant reactivation describes accounts with a long observable inactivity period followed by
sudden high-value outbound movement. The implemented deterministic rule builds account activity
history from both sender-side outbound and receiver-side inbound activity, then evaluates outbound
reactivation candidates from the same account.

For each high-value outbound candidate, the rule finds the most recent prior activity for that
account, computes the calendar-day inactivity gap, and opens a reactivation window from the
candidate timestamp through `candidate timestamp + reactivation_window_days`. It triggers when:

- `dormant_days_before_activity >= dormant_days_threshold`
- outbound transaction count is at least `min_outbound_transaction_count`
- total outbound value is at least `min_total_outbound_amount`
- each outbound candidate meets `min_outbound_amount`

Outbound movement may be to an internal `receiver_account_id` or an external `counterparty_id`,
depending on configuration. Self-transfers are excluded.

Default configuration:

```text
dormant_days_threshold = 120
reactivation_window_days = 7
min_outbound_amount = 10000.0
min_total_outbound_amount = 10000.0
severity = high
base_risk_score = 80.0
high_value_risk_score = 90.0
```

Each alert records the reactivated account, prior activity evidence followed by reactivation
transaction evidence, detection window start and end, and a reason code such as
`120 inactive days followed by 10000.00 outbound value within 7 days`. The rule uses the high-value
score when total outbound value reaches `min_total_outbound_amount * high_value_multiplier`.

Known limitations: the MVP requires an observable prior activity row, keeps one strongest
overlapping reactivation window per account, uses staged transaction data only, and does not yet
combine dormancy evidence with account takeover signals, graph relationships, device changes, or
case history. Reference dormant reactivation labels provide deterministic evaluation data, but the
rule does not require labels to detect candidates.

### Fixture Coverage

Dormant reactivation fixture tests cover:

- exact trigger and one-below-threshold non-trigger cases
- dormant-day boundary
- outbound-value boundary
- reactivation-window boundaries
- prior inbound and outbound activity evidence
- multiple dormant accounts
- counterparty and internal-account outflows
- evidence isolation and deterministic alert IDs
- cross-rule separation from rapid movement evidence
- scenario-label alignment with reference dormant reactivation injections

## Circular Flow Detection

Circular flow describes funds returning near the origin through a directed transaction chain. The
implemented detection layer builds an account-edge table from qualifying `transfer` and `wire`
transactions, then uses NetworkX simple-cycle detection to identify account cycles.

A cycle is a directed path such as `ACC_A -> ACC_B -> ACC_C -> ACC_A`. The default hop limit keeps
cycles with `min_cycle_hops <= cycle_length <= max_cycle_hops`, currently 2 through 4 hops. The
time-span filter compares the earliest and latest evidence transaction timestamps and defaults to a
maximum of 168 hours. The minimum total amount filter uses the sum of all transaction evidence
selected for the cycle path.

Evidence includes every transaction for each directed step in the canonical cycle. If multiple
transactions connect the same source and target, all are preserved as evidence. Cycle paths are
canonicalised by rotating the smallest account ID to the start while preserving direction, which
keeps cycle IDs deterministic across equivalent rotations.

Circular flow alerts are built from detection rows. The primary account is the first account in the
canonical cycle, customer IDs are attached from `staging.accounts`, and evidence IDs contain the
transaction IDs selected for the cycle path. The reason code uses the format
`4-account circular flow with 25000.00 total value over 36.0 hours`.

The default alert severity is `high`. Rule-level scoring uses a base score of `85.0`, a high-amount
score of `90.0` when total cycle value reaches `50000.0`, and a long-cycle score of `90.0` when the
cycle length reaches 4 hops. If multiple elevated conditions apply, the highest applicable score is
used. Persisted circular flow alerts are written to `aml.alerts`.

Known limitations: this layer detects cycles in staged transaction data only and uses simple
directed cycles rather than Neo4j graph algorithms. Reference `circular_flow` scenario labels provide
deterministic alignment data, but labels are not required for detection. Future graph analytics and
case grouping can reuse cycle membership, canonical paths, and transaction evidence.

### Fixture Coverage

Circular flow fixture tests cover:

- two-hop, three-hop, and four-hop exact trigger cases
- overlong-cycle and acyclic non-triggers
- hop-limit and minimum-cycle-length boundaries
- time-span and minimum-total-amount filters
- cycle canonicalisation and deterministic cycle IDs
- transaction evidence extraction and isolation
- alert conversion, customer ID attachment, reason codes, and risk scores
- counterparty-like edge handling
- JSON and CSV artefact serialisation
- scenario-label alignment with reference circular flow injections

## Unified AML Rule Engine

The unified AML rule engine registers the implemented deterministic typologies under canonical rule
keys:

- `structuring`
- `fan_in`
- `fan_out`
- `rapid_movement`
- `dormant_reactivation`
- `circular_flow`

Rule enablement is driven by `config/rules.yaml`, with CLI inclusions and exclusions available for
focused runs. Each registered rule keeps its own threshold configuration and emits the shared
`AlertRecord` output contract. The staged unified runner aggregates those alerts before optional
persistence to `aml.alerts`.

When persistence is enabled, individual rule workflows perform the alert upserts so alerts are not
persisted twice. Individual rule audit events are preserved, and the unified runner adds one
engine-level audit event with rules run, generated alert count, persisted alert count, and summary
metadata. Individual rule CLIs remain available for debugging specific typologies; `run_aml_rules.py`
is the shared runner for all enabled deterministic rules.

## Formal Rule Documentation

Detailed rule pages now live under `docs/rules/`, while this typology overview remains a high-level
summary. The formal documentation layer includes threshold rationale, tuning guidance, evidence
semantics, reason code formats, rule-level scoring logic, known limitations, validation tests, and
example `AlertRecord` payloads for every deterministic rule.

The generated JSON documentation artefact at
`reports/model_validation/aml_rule_documentation.json` supports validation, governance review, and
future model-risk reporting without requiring PostgreSQL or staged data.
