# AML Rule Documentation Pack

## Overview
This pack documents the deterministic AML rules registered in the unified rule engine.

## Registered Rule Matrix
| Rule key | Rule name | Typology |
| --- | --- | --- |
| `structuring` | Structuring | `structuring` |
| `fan_in` | Fan-in | `fan_in` |
| `fan_out` | Fan-out | `fan_out` |
| `rapid_movement` | Rapid movement | `rapid_movement` |
| `dormant_reactivation` | Dormant reactivation | `dormant_reactivation` |
| `circular_flow` | Circular flow | `circular_flow` |

## Common Alert Contract
`alert_id`, `account_id`, `customer_id`, `rule_name`, `typology`, `severity`, `risk_score_rule`, `reason_code`, `evidence_ids`, `detection_window_start`, `detection_window_end`, `model_run_id`, `alert_status`, `created_at`, `updated_at`

## Individual Rule Documentation

# Structuring Rule

## Purpose
Identify repeated below-threshold outbound transfers designed to avoid currency transaction reporting thresholds.

## Detection Logic
Multiple outbound transfers below the reporting threshold are grouped by account inside a rolling 24-hour window by default. Candidate evidence is retained when the count threshold is met.

## Inputs
- Input tables: `staging.transactions`, `staging.accounts`
- Required columns: `transaction_id`, `sender_account_id`, `counterparty_id`, `transaction_timestamp`, `amount`, `transaction_type`

## Thresholds
| Name | Default | Description | Rationale | Tuning guidance | Config path |
| --- | --- | --- | --- | --- | --- |
| `reporting_threshold` | `10000.0` | Upper reporting amount. | Upper reporting amount. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.reporting_threshold` |
| `below_threshold_margin` | `0.9` | Below-threshold band. | Below-threshold band. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.below_threshold_margin` |
| `min_transaction_count` | `8` | Minimum transfers. | Minimum transfers. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.min_transaction_count` |
| `window_hours` | `24` | Rolling detection window. | Rolling detection window. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.window_hours` |
| `transaction_types` | `('transfer', 'wire')` | Eligible transaction types. | Eligible transaction types. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.detection.transaction_types` |
| `include_counterparty_payments` | `True` | Whether counterparty payments are candidates. | Whether counterparty payments are candidates. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.include_counterparty_payments` |
| `base_risk_score` | `80.0` | Standard alert score. | Standard alert score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.base_risk_score` |
| `high_count_risk_score` | `90.0` | Elevated count score. | Elevated count score. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.high_count_risk_score` |
| `high_count_multiplier` | `1.5` | High-count multiplier. | High-count multiplier. controls deterministic candidate selection or scoring. | Tune using historical alert review, scenario fixtures, and false-positive analysis. | `rules.structuring.high_count_multiplier` |

## Alert Output
- Alert fields: `alert_id`, `account_id`, `customer_id`, `rule_name`, `typology`, `severity`, `risk_score_rule`, `reason_code`, `evidence_ids`, `detection_window_start`, `detection_window_end`, `model_run_id`, `alert_status`, `created_at`, `updated_at`

## Evidence
### transaction_ids
Transaction IDs for below-threshold transfers inside the detection window.
- Example: `TXN_STR_001, TXN_STR_002, TXN_STR_003`
- Source columns: `transaction_id`, `sender_account_id`, `transaction_timestamp`, `amount`


## Reason Code
8 transfers below threshold within 24 hours

## Risk Scoring
Use the base rule score unless the transfer count reaches the configured high-count multiplier, then use the high-count score.

## Example Scenario
An account sends eight 9,500 USD transfers to external counterparties within 24 hours.

## Example Alert
```json
{
  "account_id": "ACC_STRUCTURING_001",
  "alert_id": "ALERT_STRUCTURING_EXAMPLE",
  "alert_status": "New",
  "created_at": "2025-01-01T00:00:00+00:00",
  "customer_id": "CUST_ACC_STRUCTURING_001",
  "detection_window_end": "2025-01-01T23:59:59+00:00",
  "detection_window_start": "2025-01-01T00:00:00+00:00",
  "evidence_ids": [
    "TXN_EXAMPLE_001",
    "TXN_EXAMPLE_002"
  ],
  "model_run_id": null,
  "reason_code": "8 transfers below threshold within 24 hours",
  "risk_score_rule": 80.0,
  "rule_name": "Structuring",
  "severity": "high",
  "typology": "structuring",
  "updated_at": "2025-01-01T00:00:00+00:00"
}
```

## Limitations
- Threshold calibration depends on jurisdiction. Mitigation: Tune thresholds by market, product, and local reporting obligation.
- Cash deposits and transfers may need different thresholds in a real system. Mitigation: Split typology variants or add channel-specific parameters later.
- Reference data may produce cleaner patterns than production banking data. Mitigation: Validate against noisy production-like backtests before deployment.

## Validation Tests
- tests/test_structuring_rule.py
- tests/test_structuring_rule_fixtures_thresholds.py
- tests/test_structuring_rule_scenario_alignment.py

## Operational Notes
- Review account type and expected cash activity before analyst escalation.
- Repeated false positives should feed jurisdiction-specific threshold tuning.

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

