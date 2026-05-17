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

