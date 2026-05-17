# Graph Model

## Neo4j Connection Utilities

Neo4j is the graph database used for customer-account-counterparty network analysis in the local
AML case triage stack. The current graph layer adds connection configuration, driver lifecycle
helpers, health checks, parameterised Cypher execution utilities, and schema constraint helpers.

Configuration is loaded from `config/graph.yaml` and environment variables such as `NEO4J_URI`,
`NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE`. The password is never stored in the YAML
configuration file.

Node uniqueness constraints are prepared for:

- `Customer.customer_id`
- `Account.account_id`
- `Transaction.transaction_id`
- `Counterparty.counterparty_id`
- `Device.device_id`
- `Country.country_code`
- `Alert.alert_id`
- `Case.case_id`

The connection utility layer is separate from graph loading. Graph analytics features such as
centrality, PageRank, community detection, shortest paths, and graph evidence views will be built
after graph construction exists.

## Neo4j Graph Schema And Loading

The graph loading layer converts staged PostgreSQL data and persisted AML alerts into a repeatable
Neo4j graph. Node labels are:

- `Customer` keyed by `customer_id`
- `Account` keyed by `account_id`
- `Transaction` keyed by `transaction_id`
- `Counterparty` keyed by `counterparty_id`
- `Country` keyed by `country_code`
- `Alert` keyed by `alert_id`

Relationship types are:

- `OWNS`: customer to account
- `SENT`: account to transaction
- `RECEIVED`: transaction to receiving account
- `PAID_TO`: transaction to counterparty
- `LOCATED_IN`: customer, account, transaction, or counterparty to country
- `TRIGGERS`: evidence transaction to alert
- `FLAGS_ACCOUNT`: alert to primary flagged account
- `INVOLVES_TRANSACTION`: alert to evidence transaction

Source tables are `staging.customers`, `staging.accounts`, `staging.transactions`,
`staging.counterparties`, `staging.countries`, and `aml.alerts`. Alert evidence IDs are exploded to
link alerts to supporting transaction nodes. Country relationships use customer jurisdiction,
account home country, transaction country, and counterparty country where available.

Loading uses parameterised batched Cypher with `MERGE` for idempotent node and relationship upserts.
Constraints are ensured before loading unless explicitly skipped. Reconciliation compares attempted
load counts with current graph counts and writes JSON diagnostics with the load summary under
`reports/model_validation`.

Graph analytics is a separate layer and is intentionally not computed during graph loading.

## Neo4j Graph Analytics Features

Graph analytics reads the loaded Neo4j graph and projects graph rows into NetworkX. The analytics
workflow builds two views:

- a full directed graph for customers, accounts, transactions, counterparties, countries, and
  alerts
- an account-flow graph that condenses account-to-transaction-to-account or counterparty paths into
  account-level movement edges

Account-level features include:

- degree, in-degree, out-degree, and centrality variants
- PageRank and betweenness centrality
- clustering coefficients and deterministic community assignments
- directed cycle counts up to the configured hop limit
- fan-in, fan-out, neighbour, counterparty, transaction count, and sent/received amount metrics
- direct alert counts, high-risk alert counts, and shortest path to high-risk alerts

Community detection is NetworkX-based and supports connected components and greedy modularity.
Cycle counts use directed simple-cycle detection on the account-flow graph. Alert proximity uses
`Alert` nodes and alert-to-account or alert-to-transaction relationships to measure flagged-node
nearness without mutating graph data.

Local analytics artefacts are written to `reports/model_validation`:

- `graph_features.csv`
- `graph_features.json`
- `graph_analytics_summary.json`

## Graph Feature Persistence

Graph feature persistence uses the account-level graph analytics feature frame as its source and
writes it to:

```text
mart.graph_features
```

The table primary key is:

```text
account_id, feature_date, feature_version, graph_build_id
```

`feature_date` anchors the feature snapshot date, `feature_version` identifies the graph feature
schema and computation version, and `graph_build_id` identifies the graph build or projection used
for the feature run. When a build ID is not supplied, it is generated deterministically from the
feature date, feature version, and graph database. Row-level `metadata` JSON stores analytics
summary, projection metadata, and caller-supplied run context.

Persistence uses PostgreSQL `ON CONFLICT` upserts, so rerunning the same feature date, version, and
graph build updates the same rows rather than creating duplicates. The workflow writes
`graph_feature_persistence` audit events to `governance.audit_events` and includes rows prepared,
rows persisted, account count, feature version, and graph build ID.

Readback utilities support filtered reads, latest feature-set reads, version discovery, and compact
summary statistics. These persisted graph features become model inputs for anomaly scoring,
composite account risk scoring, and later case prioritisation.

Persisted graph features are now consumed by the Isolation Forest anomaly scoring layer alongside
behavioural and jurisdiction account features.

## Composite Account Risk Scoring Relationship

Persisted graph features are also used by composite account risk scoring. The graph risk component
turns PageRank, degree, betweenness, cycle count, high-risk alert count, and proximity-to-flagged
activity into percentile scores, then combines those graph indicators with rule, anomaly, customer,
and jurisdiction risk components. The result is persisted to `mart.account_risk_scores` for the
upcoming case generation layer.

## Case Generation Relationship

Case generation uses persisted graph features, especially `community_id`, to group alerted accounts
that belong to the same graph community. Graph-derived context remains an input to case grouping and
priority only; final case-level risk scoring is implemented in a later layer.

## Case Risk Scoring Relationship

Case risk scoring reuses persisted account-level graph features for the graph-risk component of a
generated case. PageRank, degree, cycle count, community size, high-risk alert count, and proximity
to flagged activity are converted into bounded component scores across the case's related accounts.
The graph layer remains read-only during case risk scoring; scores are written to
`aml.case_risk_scores`.

## Case Evidence Relationship

Case evidence generation reads persisted `mart.graph_features` for each case's primary and related
accounts. Evidence packs include PageRank, degree, betweenness, community ID, community size, cycle
count, high-risk alert counts, shortest path to flagged activity, fan-in, fan-out, and connected
account counts where available. These records support future Case Detail graph context without
calling Neo4j during evidence unit tests.

## Dashboard Graph View And Account Profile

Graph View is a PostgreSQL-first dashboard projection for suspicious account networks. It seeds
from a case ID, account ID, graph community, or risk band and reads `mart.account_risk_scores`,
`mart.graph_features`, `staging.transactions`, `aml.alerts`, `aml.cases`, and `aml.case_entities`.
The view is bounded by configured hop, node, and edge limits before rendering through PyVis or
Plotly.

Optional Neo4j dashboard readers are available for account neighbourhoods, but they require an
explicit caller-supplied driver and do not connect at import time. Account Profile complements
Graph View by showing account/customer context, transaction history, alert history, linked cases,
behavioural features, graph features, anomaly scores, account risk scores, and counterparties.

Both pages read persisted data only and do not run graph loading, graph analytics, feature
persistence, scoring, evidence generation, or lifecycle mutation.

## Dashboard Governance Relationship

Model Metrics reuses graph-derived risk outputs indirectly through `mart.account_risk_scores` and
`aml.case_risk_scores`; it does not rerun graph analytics. Audit Log can display graph load,
analytics, and feature-persistence audit events from `governance.audit_events`. Validation Report
previews graph artefacts from the configured local report directory while enforcing path
restrictions. Final end-to-end demo polish comes after these read-only governance pages.
