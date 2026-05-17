# Circular flow Rule

## Purpose
Identify funds returning near the origin through directed transaction cycles.

## Detection Logic
Construct a directed account transaction graph, detect simple cycles within a configurable hop limit, select transaction evidence, then convert detections into AlertRecord outputs.

## Inputs
- Input tables: `staging.transactions`, `staging.accounts`
- Required columns: `transaction_id`, `sender_account_id`, `receiver_account_id`, `counterparty_id`, `transaction_timestamp`, `amount`, `transaction_type`

## Thresholds
| Name | Default | Description | Rationale | Tuning guidance | Config path |
| --- | --- | --- | --- | --- | --- |
| `max_cycle_hops` | `4` | Maximum cycle length. | Maximum cycle length. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.max_cycle_hops` |
| `min_cycle_hops` | `2` | Minimum cycle length. | Minimum cycle length. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.min_cycle_hops` |
| `min_total_amount` | `0.0` | Minimum cycle value. | Minimum cycle value. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.min_total_amount` |
| `max_time_span_hours` | `168` | Maximum cycle time span. | Maximum cycle time span. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.max_time_span_hours` |
| `transaction_types` | `('transfer', 'wire')` | Eligible transaction types. | Eligible transaction types. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.transaction_types` |
| `include_counterparty_edges` | `False` | Include counterparty edges. | Include counterparty edges. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.include_counterparty_edges` |
| `include_self_loops` | `False` | Include self-loop edges. | Include self-loop edges. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.include_self_loops` |
| `max_cycles_per_account` | `3` | Per-account cycle cap. | Per-account cycle cap. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.max_cycles_per_account` |
| `max_total_cycles` | `500` | Total cycle cap. | Total cycle cap. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.detection.max_total_cycles` |
| `severity` | `high` | Alert severity. | Alert severity. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.alert.severity` |
| `base_risk_score` | `85.0` | Standard alert score. | Standard alert score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.alert.base_risk_score` |
| `high_amount_risk_score` | `90.0` | High-amount alert score. | High-amount alert score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.alert.high_amount_risk_score` |
| `high_amount_threshold` | `50000.0` | High-amount score threshold. | High-amount score threshold. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.alert.high_amount_threshold` |
| `long_cycle_risk_score` | `90.0` | Long-cycle alert score. | Long-cycle alert score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.alert.long_cycle_risk_score` |
| `long_cycle_hop_threshold` | `4` | Long-cycle hop threshold. | Long-cycle hop threshold. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.circular_flow.alert.long_cycle_hop_threshold` |

## Alert Output
- Alert fields: `alert_id`, `account_id`, `customer_id`, `rule_name`, `typology`, `severity`, `risk_score_rule`, `reason_code`, `evidence_ids`, `detection_window_start`, `detection_window_end`, `model_run_id`, `alert_status`, `created_at`, `updated_at`

## Evidence
### cycle_transaction_ids
Transaction IDs along the directed cycle path.
- Example: `TXN_CF_001, TXN_CF_002, TXN_CF_003, TXN_CF_004`
- Source columns: `transaction_id`, `sender_account_id`, `receiver_account_id`

### cycle_path
Canonical directed account path used for analyst review.
- Example: `ACC_A -> ACC_B -> ACC_C -> ACC_A`
- Source columns: `sender_account_id`, `receiver_account_id`


## Reason Code
4-account circular flow with 25000.00 total value over 36.0 hours

## Risk Scoring
Use the base score by default, the high-amount score when total cycle value reaches the high-amount threshold, and the long-cycle score when cycle length reaches the long-cycle hop threshold. If multiple elevated conditions apply, use the maximum score.

## Example Scenario
Four accounts transfer value around a directed loop and return funds near the origin within 36 hours.

## Example Alert
```json
{
  "account_id": "ACC_CF_A",
  "alert_id": "ALERT_CIRCULAR_FLOW_EXAMPLE",
  "alert_status": "New",
  "created_at": "2025-01-01T00:00:00+00:00",
  "customer_id": "CUST_ACC_CF_A",
  "detection_window_end": "2025-01-01T23:59:59+00:00",
  "detection_window_start": "2025-01-01T00:00:00+00:00",
  "evidence_ids": [
    "TXN_EXAMPLE_001",
    "TXN_EXAMPLE_002"
  ],
  "model_run_id": null,
  "reason_code": "4-account circular flow with 25000.00 total value over 36.0 hours",
  "risk_score_rule": 85.0,
  "rule_name": "Circular flow",
  "severity": "high",
  "typology": "circular_flow",
  "updated_at": "2025-01-01T00:00:00+00:00"
}
```

## Limitations
- Cycle detection over reference data may be cleaner than production flow networks. Mitigation: Backtest against noisy transaction networks before production deployment.
- Multi-edge transaction evidence may require additional analyst summarisation. Mitigation: Add graph evidence summaries and rollups in later documentation artefacts.
- Neo4j graph evidence and community context will be added later. Mitigation: Integrate graph database paths and community metrics in future tickets.

## Validation Tests
- tests/test_circular_flow_detection.py
- tests/test_circular_flow_alerts.py
- tests/test_circular_flow_rule.py

## Operational Notes
- Review whether cycle participants share customers, devices, or counterparties.
- Use detection artefacts to explain cycle path and transaction evidence.

