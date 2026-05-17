# Supervised AML Baseline Model Card

## Intended Use
Interpretable supervised benchmark for AML triage prioritisation.

## Label Source
Analyst lifecycle closure decisions from supervised-readiness datasets.

## Model
- Name: `supervised_aml_baseline`
- Version: `supervised_aml_baseline_v1`
- Family: `logistic_regression`
- Dataset version: `d`

## Features
- `case_risk_score`
- `alert_count`

## Validation Metrics
```json
{
  "accuracy": 0.6,
  "f1": 0.75,
  "false_negative": 0,
  "false_positive": 2,
  "pr_auc": 0.6,
  "precision": 0.6,
  "recall": 1.0,
  "roc_auc": 0.5,
  "row_count": 5,
  "threshold": 0.5,
  "true_negative": 0,
  "true_positive": 3,
  "warning": null
}
```

## Limitations
Sparse reference analyst labels limit statistical confidence.
This model complements Isolation Forest and composite risk scoring.

## Leakage Controls
Training uses supervised-readiness labels and timestamp-aware validation splits.

## Reference Data Caveat
Outputs are portfolio demonstration artefacts, not production model approvals.