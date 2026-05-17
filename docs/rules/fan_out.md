# Fan-out Rule

## Purpose
Identify dispersion accounts sending funds to many unique recipients.

## Detection Logic
One sending account transfers to many unique recipients within a rolling seven-day window by default.

## Inputs
- Input tables: `staging.transactions`, `staging.accounts`
- Required columns: `transaction_id`, `sender_account_id`, `receiver_account_id`, `counterparty_id`, `transaction_timestamp`, `amount`, `transaction_type`

## Thresholds
| Name | Default | Description | Rationale | Tuning guidance | Config path |
| --- | --- | --- | --- | --- | --- |
| `min_unique_recipients` | `20` | Minimum recipients. | Minimum recipients. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.min_unique_recipients` |
| `window_days` | `7` | Rolling detection window. | Rolling detection window. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.window_days` |
| `min_total_amount` | `0.0` | Minimum total sent value. | Minimum total sent value. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.detection.min_total_amount` |
| `transaction_types` | `('transfer', 'wire')` | Eligible transaction types. | Eligible transaction types. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.detection.transaction_types` |
| `include_counterparties` | `True` | Include external recipients. | Include external recipients. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.include_counterparties` |
| `include_internal_accounts` | `True` | Include internal recipients. | Include internal recipients. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.include_internal_accounts` |
| `base_risk_score` | `80.0` | Standard alert score. | Standard alert score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.base_risk_score` |
| `high_recipient_risk_score` | `90.0` | Elevated recipient score. | Elevated recipient score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.high_recipient_risk_score` |
| `high_recipient_multiplier` | `1.5` | High-recipient multiplier. | High-recipient multiplier. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.fan_out.high_recipient_multiplier` |

## Alert Output
- Alert fields: `alert_id`, `account_id`, `customer_id`, `rule_name`, `typology`, `severity`, `risk_score_rule`, `reason_code`, `evidence_ids`, `detection_window_start`, `detection_window_end`, `model_run_id`, `alert_status`, `created_at`, `updated_at`

## Evidence
### transaction_ids
Transaction IDs from sending account to distinct recipient accounts or counterparties.
- Example: `TXN_FO_001, TXN_FO_002`
- Source columns: `transaction_id`, `sender_account_id`, `receiver_account_id`, `counterparty_id`

### recipient_ids
Recipient keys derived from receiver account IDs or counterparty IDs.
- Example: `ACC_RECIPIENT_001, CP_EXT_001`
- Source columns: `receiver_account_id`, `counterparty_id`


## Reason Code
20 unique recipients within 7 days

## Risk Scoring
Use the base score unless unique recipient count reaches the configured multiplier, then use the high-recipient score.

## Example Scenario
A sending account distributes funds to 20 recipients over one week.

## Example Alert
```json
{
  "account_id": "ACC_DISPERSION_001",
  "alert_id": "ALERT_FAN_OUT_EXAMPLE",
  "alert_status": "New",
  "created_at": "2025-01-01T00:00:00+00:00",
  "customer_id": "CUST_ACC_DISPERSION_001",
  "detection_window_end": "2025-01-01T23:59:59+00:00",
  "detection_window_start": "2025-01-01T00:00:00+00:00",
  "evidence_ids": [
    "TXN_EXAMPLE_001",
    "TXN_EXAMPLE_002"
  ],
  "model_run_id": null,
  "reason_code": "20 unique recipients within 7 days",
  "risk_score_rule": 80.0,
  "rule_name": "Fan-out",
  "severity": "high",
  "typology": "fan_out",
  "updated_at": "2025-01-01T00:00:00+00:00"
}
```

## Limitations
- Payroll or marketplace payout accounts may produce benign fan-out patterns. Mitigation: Use account purpose and customer segment controls in later tuning.
- Counterparty quality and customer segment should be reviewed in later versions. Mitigation: Join risk-rated counterparty and customer profile features when available.
- Recipient identity resolution may affect unique recipient counts. Mitigation: Improve recipient entity resolution before production deployment.

## Validation Tests
- tests/test_fan_out_rule.py
- tests/test_fan_out_rule_fixtures.py
- tests/test_fan_flow_counterparty_handling.py

## Operational Notes
- Validate whether the account has expected payout or payroll activity.
- Review recipient clustering and repeated recipient names where available.

