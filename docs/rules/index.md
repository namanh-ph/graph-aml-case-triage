# AML Rule Documentation Index

## Registered Rules
| Rule key | Rule name | Typology | Thresholds | Evidence docs |
| --- | --- | --- | ---: | ---: |
| `structuring` | Structuring | `structuring` | 9 | 1 |
| `fan_in` | Fan-in | `fan_in` | 8 | 2 |
| `fan_out` | Fan-out | `fan_out` | 9 | 2 |
| `rapid_movement` | Rapid movement | `rapid_movement` | 12 | 2 |
| `dormant_reactivation` | Dormant reactivation | `dormant_reactivation` | 11 | 2 |
| `circular_flow` | Circular flow | `circular_flow` | 15 | 2 |

## Rule Coverage Summary
- Rules documented: 6
- Missing rules: []
- Threshold docs: 64
- Evidence docs: 11
- Limitations: 18

## Typology Matrix
- Structuring: `structuring`
- Fan-in: `fan_in`
- Fan-out: `fan_out`
- Rapid movement: `rapid_movement`
- Dormant reactivation: `dormant_reactivation`
- Circular flow: `circular_flow`

## Alert Output Contract
All documented rules emit the common `AlertRecord` fields and include an example alert.

## Documentation Artefacts
- `docs/rules/aml_rule_documentation_pack.md`
- `docs/rules/<rule_key>.md`
- `reports/model_validation/aml_rule_documentation.json`

