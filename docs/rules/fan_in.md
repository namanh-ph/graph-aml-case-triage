# Fan-in Rule

## Purpose
Identify collection accounts receiving funds from many unique senders.

## Detection Logic
Many unique sender accounts transfer into one receiving account within a rolling seven-day window by default.

## Inputs
- Input tables: `staging.transactions`, `staging.accounts`
- Required columns: `transaction_id`, `sender_account_id`, `receiver_account_id`, `transaction_timestamp`, `amount`, `transaction_type`

## Thresholds
| Name | Default | Description | Rationale | Tuning guidance | Config path |
| --- | --- | --- | --- | --- | --- |
| `min_unique_senders` | `15` | Minimum unique senders. | Minimum unique senders. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_in.min_unique_senders` |
| `window_days` | `7` | Rolling detection window. | Rolling detection window. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_in.window_days` |
| `min_total_amount` | `0.0` | Minimum total received value. | Minimum total received value. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_in.detection.min_total_amount` |
| `transaction_types` | `('transfer', 'wire')` | Eligible transaction types. | Eligible transaction types. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_in.detection.transaction_types` |
| `include_internal_account_receipts` | `True` | Whether internal account receipts qualify. | Whether internal account receipts qualify. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_in.include_internal_account_receipts` |
| `base_risk_score` | `80.0` | Standard alert score. | Standard alert score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_in.base_risk_score` |
| `high_sender_risk_score` | `90.0` | Elevated sender score. | Elevated sender score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_in.high_sender_risk_score` |
| `high_sender_multiplier` | `1.5` | High-sender multiplier. | High-sender multiplier. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_in.high_sender_multiplier` |

## Alert Output
- Alert fields: `alert_id`, `account_id`, `customer_id`, `rule_name`, `typology`, `severity`, `risk_score_rule`, `reason_code`, `evidence_ids`, `detection_window_start`, `detection_window_end`, `model_run_id`, `alert_status`, `created_at`, `updated_at`

## Evidence
### transaction_ids
Transaction IDs from sender accounts into the receiving account.
- Example: `TXN_FI_001, TXN_FI_002`
- Source columns: `transaction_id`, `sender_account_id`, `receiver_account_id`

### sender_ids
Unique sending account IDs used to support the sender-count threshold.
- Example: `ACC_SRC_001, ACC_SRC_002`
- Source columns: `sender_account_id`


## Reason Code
15 unique senders within 7 days

## Risk Scoring
Use the base score unless unique sender count reaches the configured multiplier, then use the high-sender score.

## Example Scenario
A receiving account collects transfers from 15 unrelated senders in 7 days.

## Example Alert
```json
{
  "account_id": "ACC_COLLECTION_001",
  "alert_id": "ALERT_FAN_IN_EXAMPLE",
  "alert_status": "New",
  "created_at": "2025-01-01T00:00:00+00:00",
  "customer_id": "CUST_ACC_COLLECTION_001",
  "detection_window_end": "2025-01-01T23:59:59+00:00",
  "detection_window_start": "2025-01-01T00:00:00+00:00",
  "evidence_ids": [
    "TXN_EXAMPLE_001",
    "TXN_EXAMPLE_002"
  ],
  "model_run_id": null,
  "reason_code": "15 unique senders within 7 days",
  "risk_score_rule": 80.0,
  "rule_name": "Fan-in",
  "severity": "high",
  "typology": "fan_in",
  "updated_at": "2025-01-01T00:00:00+00:00"
}
```

## Limitations
- High-volume merchant accounts may produce benign fan-in patterns. Mitigation: Incorporate merchant, charity, and platform-account segment context.
- Customer segment and account type should be incorporated in later tuning. Mitigation: Use profile and feature tables for segment-aware suppression.
- Duplicate senders should not inflate unique sender counts. Mitigation: Continue using canonical sender account IDs and identity resolution.

## Validation Tests
- tests/test_fan_in_rule.py
- tests/test_fan_in_rule_fixtures.py
- tests/test_fan_flow_rule_separation.py

## Operational Notes
- Compare sender geographies and customer relationships during review.
- Monitor merchant-account false positives separately from personal accounts.

