# Dormant reactivation Rule

## Purpose
Identify long-inactive accounts that suddenly resume high-value outbound activity.

## Detection Logic
Find prior account activity, measure dormant days, then aggregate qualifying outbound reactivation transactions inside the reactivation window.

## Inputs
- Input tables: `staging.transactions`, `staging.accounts`
- Required columns: `transaction_id`, `sender_account_id`, `receiver_account_id`, `counterparty_id`, `transaction_timestamp`, `amount`, `transaction_type`

## Thresholds
| Name | Default | Description | Rationale | Tuning guidance | Config path |
| --- | --- | --- | --- | --- | --- |
| `dormant_days_threshold` | `120` | Dormancy period. | Dormancy period. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.dormant_days_threshold` |
| `reactivation_window_days` | `7` | Reactivation window. | Reactivation window. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.reactivation_window_days` |
| `min_outbound_amount` | `10000.0` | Minimum outbound amount. | Minimum outbound amount. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.min_outbound_amount` |
| `min_total_outbound_amount` | `10000.0` | Minimum total outbound amount. | Minimum total outbound amount. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.min_total_outbound_amount` |
| `min_outbound_transaction_count` | `1` | Minimum outbound count. | Minimum outbound count. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.min_outbound_transaction_count` |
| `outbound_transaction_types` | `('transfer', 'wire', 'cash_withdrawal')` | Outbound types. | Outbound types. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.outbound_transaction_types` |
| `include_counterparty_outflows` | `True` | Include external counterparty outflows. | Include external counterparty outflows. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.include_counterparty_outflows` |
| `include_internal_account_outflows` | `True` | Include internal account outflows. | Include internal account outflows. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.include_internal_account_outflows` |
| `base_risk_score` | `80.0` | Standard alert score. | Standard alert score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.base_risk_score` |
| `high_value_risk_score` | `90.0` | High-value score. | High-value score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.high_value_risk_score` |
| `high_value_multiplier` | `2.0` | High-value multiplier. | High-value multiplier. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.dormant_reactivation.high_value_multiplier` |

## Alert Output
- Alert fields: `alert_id`, `account_id`, `customer_id`, `rule_name`, `typology`, `severity`, `risk_score_rule`, `reason_code`, `evidence_ids`, `detection_window_start`, `detection_window_end`, `model_run_id`, `alert_status`, `created_at`, `updated_at`

## Evidence
### prior_activity_transaction_id
Prior activity transaction ID establishing observable account history.
- Example: `TXN_DR_PRIOR_001`
- Source columns: `transaction_id`, `sender_account_id`, `receiver_account_id`

### reactivation_outbound_transaction_ids
Outbound reactivation transaction IDs inside the reactivation window.
- Example: `TXN_DR_REACT_001`
- Source columns: `transaction_id`, `sender_account_id`, `amount`


## Reason Code
120 inactive days followed by 10000.00 outbound value within 7 days

## Risk Scoring
Use the base score unless total outbound amount reaches the configured high-value multiplier, then use the high-value score.

## Example Scenario
An account has no activity for 120 days, then sends 10,000 USD outbound within 7 days.

## Example Alert
```json
{
  "account_id": "ACC_DORMANT_001",
  "alert_id": "ALERT_DORMANT_REACTIVATION_EXAMPLE",
  "alert_status": "New",
  "created_at": "2025-01-01T00:00:00+00:00",
  "customer_id": "CUST_ACC_DORMANT_001",
  "detection_window_end": "2025-01-01T23:59:59+00:00",
  "detection_window_start": "2025-01-01T00:00:00+00:00",
  "evidence_ids": [
    "TXN_EXAMPLE_001",
    "TXN_EXAMPLE_002"
  ],
  "model_run_id": null,
  "reason_code": "120 inactive days followed by 10000.00 outbound value within 7 days",
  "risk_score_rule": 80.0,
  "rule_name": "Dormant reactivation",
  "severity": "high",
  "typology": "dormant_reactivation",
  "updated_at": "2025-01-01T00:00:00+00:00"
}
```

## Limitations
- New accounts without observable history should not be treated as dormant by default. Mitigation: Require prior activity evidence before triggering.
- Seasonal accounts can reactivate legitimately. Mitigation: Add customer profile, seasonality, and account-purpose review.
- Account status and customer profile context should be added later. Mitigation: Join staged account status and future customer risk features.

## Validation Tests
- tests/test_dormant_reactivation_rule.py
- tests/test_dormant_reactivation_window_detection.py
- tests/test_movement_dormancy_dormant_thresholds.py

## Operational Notes
- Analysts should verify whether the account was closed, dormant, or simply seasonal.
- Review account takeover signals when rapid outbound activity appears after dormancy.

