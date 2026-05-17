# Rapid movement Rule

## Purpose
Identify pass-through accounts where incoming funds quickly leave the account.

## Detection Logic
Aggregate inbound value and outbound value inside a configurable outflow window, then flag high outflow ratio and low retained value.

## Inputs
- Input tables: `staging.transactions`, `staging.accounts`
- Required columns: `transaction_id`, `sender_account_id`, `receiver_account_id`, `counterparty_id`, `transaction_timestamp`, `amount`, `transaction_type`

## Thresholds
| Name | Default | Description | Rationale | Tuning guidance | Config path |
| --- | --- | --- | --- | --- | --- |
| `outflow_window_hours` | `48` | Pass-through window. | Pass-through window. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.outflow_window_hours` |
| `min_total_received` | `1000.0` | Minimum inbound value. | Minimum inbound value. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.min_total_received` |
| `min_outflow_ratio` | `0.9` | Minimum outbound ratio. | Minimum outbound ratio. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.min_outflow_ratio` |
| `max_retained_ratio` | `0.1` | Maximum retained ratio. | Maximum retained ratio. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.max_retained_ratio` |
| `min_outgoing_transaction_count` | `1` | Minimum outgoing transaction count. | Minimum outgoing transaction count. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.min_outgoing_transaction_count` |
| `inbound_transaction_types` | `('transfer', 'wire', 'cash_deposit')` | Inbound types. | Inbound types. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.inbound_transaction_types` |
| `outbound_transaction_types` | `('transfer', 'wire', 'cash_withdrawal')` | Outbound types. | Outbound types. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.outbound_transaction_types` |
| `include_counterparty_outflows` | `True` | Include external counterparty outflows. | Include external counterparty outflows. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.include_counterparty_outflows` |
| `include_internal_account_outflows` | `True` | Include internal account outflows. | Include internal account outflows. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.include_internal_account_outflows` |
| `base_risk_score` | `80.0` | Standard alert score. | Standard alert score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.base_risk_score` |
| `high_ratio_risk_score` | `90.0` | Elevated ratio score. | Elevated ratio score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.high_ratio_risk_score` |
| `high_ratio_threshold` | `0.98` | High-ratio threshold. | High-ratio threshold. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.rapid_movement.high_ratio_threshold` |

## Alert Output
- Alert fields: `alert_id`, `account_id`, `customer_id`, `rule_name`, `typology`, `severity`, `risk_score_rule`, `reason_code`, `evidence_ids`, `detection_window_start`, `detection_window_end`, `model_run_id`, `alert_status`, `created_at`, `updated_at`

## Evidence
### inbound_transaction_ids
Inbound transaction IDs inside the pass-through detection window.
- Example: `TXN_RM_IN_001`
- Source columns: `transaction_id`, `receiver_account_id`, `amount`

### outbound_transaction_ids
Outbound transaction IDs following the inbound activity inside the same window.
- Example: `TXN_RM_OUT_001`
- Source columns: `transaction_id`, `sender_account_id`, `receiver_account_id`, `counterparty_id`


## Reason Code
90 percent of received value sent out within 48 hours

## Risk Scoring
Use the base score for standard detections and the high-ratio score when the outflow ratio reaches the configured high-ratio threshold.

## Example Scenario
An account receives 10,000 USD and sends out 9,200 USD within 48 hours.

## Example Alert
```json
{
  "account_id": "ACC_PASS_THROUGH_001",
  "alert_id": "ALERT_RAPID_MOVEMENT_EXAMPLE",
  "alert_status": "New",
  "created_at": "2025-01-01T00:00:00+00:00",
  "customer_id": "CUST_ACC_PASS_THROUGH_001",
  "detection_window_end": "2025-01-01T23:59:59+00:00",
  "detection_window_start": "2025-01-01T00:00:00+00:00",
  "evidence_ids": [
    "TXN_EXAMPLE_001",
    "TXN_EXAMPLE_002"
  ],
  "model_run_id": null,
  "reason_code": "90 percent of received value sent out within 48 hours",
  "risk_score_rule": 80.0,
  "rule_name": "Rapid movement",
  "severity": "high",
  "typology": "rapid_movement",
  "updated_at": "2025-01-01T00:00:00+00:00"
}
```

## Limitations
- Legitimate settlement accounts can have high pass-through ratios. Mitigation: Add product, account purpose, and customer segment context.
- Balance data would improve retained-value interpretation. Mitigation: Incorporate balance snapshots or available-balance features later.
- Time-zone and business-day handling should be reviewed before production use. Mitigation: Align timestamp handling to operational calendars and branch jurisdictions.

## Validation Tests
- tests/test_rapid_movement_rule.py
- tests/test_rapid_movement_window_detection.py
- tests/test_movement_dormancy_rapid_thresholds.py

## Operational Notes
- Review inbound source and outbound destination relationship before escalation.
- Segment settlement-like accounts separately during threshold tuning.

