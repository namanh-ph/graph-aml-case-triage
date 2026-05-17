.PHONY: setup install check-env info verify-scaffold lint format typecheck test test-cov check services-up services-down services-restart services-logs services-ps postgres-up neo4j-up mlflow-up db-check db-version db-list-schemas db-list-staging-tables db-init db-reset db-seed-smoke db-delete-smoke-seed db-recreate-and-seed run-pipeline generate-data generate-data-small generate-data-scenarios generate-data-scenarios-small reference-summary reference-summary-scenarios validate-data validate-data-baseline validate-data-strict validate-data-audit load-data load-data-baseline load-data-scenarios stage-data stage-data-no-validate stage-data-limited generate-data-dictionary generate-dataset-summary generate-dataset-summary-baseline generate-dataset-summary-staged generate-account-features generate-account-features-limited generate-account-features-extended generate-account-features-extended-limited persist-account-features persist-account-features-no-audit read-mart-account-features alerts-schema-info alerts-read run-structuring-rule run-structuring-rule-persist run-structuring-rule-limited test-structuring-fixtures run-fan-in-rule run-fan-in-rule-persist run-fan-in-rule-limited run-fan-out-rule run-fan-out-rule-persist run-fan-out-rule-limited run-rapid-movement-rule run-rapid-movement-rule-persist run-rapid-movement-rule-limited run-dormant-reactivation-rule run-dormant-reactivation-rule-persist run-dormant-reactivation-rule-limited detect-circular-flows detect-circular-flows-limited detect-circular-flows-no-artefacts run-circular-flow-rule run-circular-flow-rule-persist run-circular-flow-rule-limited rules-list run-aml-rules run-aml-rules-persist run-aml-rules-limited run-aml-rules-no-artefacts rules-docs-list rules-docs-validate generate-rule-docs graph-config graph-health graph-constraints-list graph-constraints-ensure graph-load graph-load-limited graph-load-no-alerts graph-load-no-reconcile graph-analytics graph-analytics-no-artefacts graph-analytics-connected-components graph-analytics-greedy-modularity graph-features-persist graph-features-persist-no-artefacts graph-features-read graph-features-summary model-isolation-forest model-isolation-forest-persist model-isolation-forest-limited model-isolation-forest-no-mlflow anomaly-scores-read anomaly-scores-summary model-supervised-train model-supervised-train-persist model-supervised-train-limited model-supervised-read-scores model-supervised-read-runs model-supervised-summary model-comparison-run model-comparison-run-persist model-comparison-run-limited model-comparison-read-runs model-comparison-read-champion model-comparison-summary account-risk-score account-risk-score-persist account-risk-score-limited account-risk-score-no-artefacts account-risk-read account-risk-summary cases-generate cases-generate-persist cases-generate-limited cases-generate-no-artefacts cases-read cases-summary case-risk-score case-risk-score-persist case-risk-score-limited case-risk-score-no-artefacts case-risk-read case-risk-summary case-evidence-build case-evidence-build-persist case-evidence-build-limited case-evidence-build-no-artefacts case-evidence-read case-evidence-summary case-lifecycle-events case-lifecycle-assignments case-lifecycle-summary case-lifecycle-start-review case-lifecycle-assign-sample labels-build labels-build-persist labels-build-limited labels-read-case labels-read-account labels-summary dashboard dashboard-config dashboard-health dashboard-summary dashboard-graph-summary dashboard-account-summary dashboard-model-summary dashboard-audit-summary dashboard-validation-index demo-plan demo-plan-with-reset demo-readiness demo-run-dry demo-run demo-run-with-reset demo-validate demo-artefacts test-fan-flow-fixtures test-movement-dormancy-fixtures build-graph run-rules train-model generate-cases run-dashboard clean clean-caches
.PHONY: monitoring-run monitoring-run-persist monitoring-run-limited monitoring-read-runs monitoring-read-drift monitoring-read-volume monitoring-read-segments monitoring-read-backtesting monitoring-summary
.PHONY: explainability-run explainability-run-persist explainability-run-limited explainability-read-runs explainability-read-features explainability-read-decomposition explainability-read-reasons explainability-read-model-cards explainability-summary
.PHONY: governance-inventory-run governance-inventory-run-persist governance-inventory-run-limited governance-inventory-read-runs governance-inventory-read-lineage governance-inventory-read-artefacts governance-inventory-read-processes governance-inventory-read-models governance-inventory-read-validations governance-inventory-summary
.PHONY: security-controls-run security-controls-run-persist security-controls-run-limited security-controls-read-runs security-controls-read-fields security-controls-read-permissions security-controls-read-secrets security-controls-read-audit-integrity security-controls-summary security-mask-preview
.PHONY: release-readiness-run release-readiness-run-persist release-readiness-no-artefacts release-readiness-read-runs release-readiness-read-checks release-readiness-read-artefacts release-readiness-read-evidence release-readiness-read-portfolio release-readiness-summary
.PHONY: transform-data export-gold

# Environment and setup
setup:
	uv sync --extra dev

install: setup

check-env:
	python scripts/dev.py check-env

info:
	python scripts/dev.py info

verify-scaffold:
	python scripts/dev.py verify-scaffold

# Code quality
lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check . --fix

typecheck:
	uv run mypy src/graph_aml

test:
	uv run pytest

test-cov:
	uv run pytest --cov=src/graph_aml --cov-report=term-missing

check: lint typecheck test

# Local infrastructure
services-up:
	docker compose up -d postgres neo4j

services-down:
	docker compose down

services-restart:
	docker compose restart postgres neo4j

services-logs:
	docker compose logs -f

services-ps:
	docker compose ps

postgres-up:
	docker compose up -d postgres

neo4j-up:
	docker compose up -d neo4j

mlflow-up:
	docker compose --profile mlflow up -d mlflow

# Database utilities
db-check:
	python scripts/db.py check

db-version:
	python scripts/db.py version

db-list-schemas:
	python scripts/db.py list-schemas

db-list-staging-tables:
	python scripts/db.py list-tables --schema staging

db-init:
	python scripts/db.py init

db-reset:
	python scripts/db.py reset --yes

db-seed-smoke:
	python scripts/db.py seed-smoke

db-delete-smoke-seed:
	python scripts/db.py delete-smoke-seed --yes

db-recreate-and-seed:
	python scripts/db.py reset --yes
	python scripts/db.py seed-smoke

# Application aliases
run-pipeline:
	@echo "Run: make generate-data-scenarios-small && make validate-data-strict && make load-data-scenarios && make stage-data"

# One-shot: silver parquet -> populated mart/aml PG tables (gold source)
# Prereqs: docker services up, db-init done, data/silver/*.parquet present
pipeline-full: load-data stage-data persist-account-features graph-load graph-features-persist run-aml-rules-persist model-isolation-forest-persist account-risk-score-persist cases-generate-persist case-risk-score-persist case-evidence-build-persist
	@echo "Pipeline complete. mart.* and aml.* tables populated. Ready for: make export-gold"

# Resume pipeline after raw + staging are already populated (skip load-data + stage-data)
pipeline-after-staging: persist-account-features graph-load graph-features-persist run-aml-rules-persist model-isolation-forest-persist account-risk-score-persist cases-generate-persist case-risk-score-persist case-evidence-build-persist
	@echo "Pipeline (post-staging) complete. mart.* and aml.* tables populated. Ready for: make export-gold"
.PHONY: pipeline-full pipeline-after-staging

# Data layer: transform raw CSV deliverables into columnar Parquet for analytics
transform-data:
	python scripts/transform_to_parquet.py

# Gold layer: derive gold parquet directly from silver (no Postgres required)
build-gold:
	python scripts/build_gold_from_silver.py

# Gold layer: export PG mart/aml/governance tables to data/gold/*.parquet
export-gold:
	python scripts/export_gold.py

load-data:
	python scripts/ingest_raw.py

stage-data:
	python scripts/stage_data.py stage

stage-data-no-validate:
	python scripts/stage_data.py stage --no-validate

stage-data-limited:
	python scripts/stage_data.py stage --limit 1000

generate-data-dictionary:
	python scripts/generate_data_dictionary.py generate

generate-account-features:
	python scripts/generate_account_features.py staged

generate-account-features-limited:
	python scripts/generate_account_features.py staged --limit 1000

generate-account-features-extended:
	python scripts/generate_account_features.py staged --extended

generate-account-features-extended-limited:
	python scripts/generate_account_features.py staged --extended --limit 1000

persist-account-features:
	python scripts/generate_account_features.py staged --extended --persist --min-feature-date 2025-03-31 --max-feature-date 2025-03-31

persist-account-features-no-audit:
	python scripts/generate_account_features.py staged --extended --persist --no-audit

read-mart-account-features:
	python scripts/generate_account_features.py staged --read-mart

alerts-schema-info:
	python scripts/alerts.py schema-info

alerts-read:
	python scripts/alerts.py read

run-structuring-rule:
	python scripts/run_structuring_rule.py run

run-structuring-rule-persist:
	python scripts/run_structuring_rule.py run --persist

run-structuring-rule-limited:
	python scripts/run_structuring_rule.py run --limit 1000

test-structuring-fixtures:
	python -m pytest tests/test_structuring_rule_fixtures_trigger.py \
		tests/test_structuring_rule_fixtures_non_trigger.py \
		tests/test_structuring_rule_fixtures_thresholds.py \
		tests/test_structuring_rule_fixtures_windows.py \
		tests/test_structuring_rule_fixtures_multi_account.py \
		tests/test_structuring_rule_fixtures_counterparties.py \
		tests/test_structuring_rule_fixtures_reason_evidence.py \
		tests/test_structuring_rule_fixtures_risk_score.py \
		tests/test_structuring_rule_scenario_alignment.py \
		tests/test_structuring_rule_deterministic_ids.py \
		tests/test_structuring_rule_mutation_safety.py \
		tests/test_structuring_rule_invalid_inputs.py \
		tests/test_structuring_fixture_helpers.py

run-fan-in-rule:
	python scripts/run_fan_in_rule.py run

run-fan-in-rule-persist:
	python scripts/run_fan_in_rule.py run --persist

run-fan-in-rule-limited:
	python scripts/run_fan_in_rule.py run --limit 1000

run-fan-out-rule:
	python scripts/run_fan_out_rule.py run

run-fan-out-rule-persist:
	python scripts/run_fan_out_rule.py run --persist

run-fan-out-rule-limited:
	python scripts/run_fan_out_rule.py run --limit 1000

run-rapid-movement-rule:
	python scripts/run_rapid_movement_rule.py run

run-rapid-movement-rule-persist:
	python scripts/run_rapid_movement_rule.py run --persist

run-rapid-movement-rule-limited:
	python scripts/run_rapid_movement_rule.py run --limit 1000

run-dormant-reactivation-rule:
	python scripts/run_dormant_reactivation_rule.py run

run-dormant-reactivation-rule-persist:
	python scripts/run_dormant_reactivation_rule.py run --persist

run-dormant-reactivation-rule-limited:
	python scripts/run_dormant_reactivation_rule.py run --limit 1000

detect-circular-flows:
	python scripts/detect_circular_flows.py run

detect-circular-flows-limited:
	python scripts/detect_circular_flows.py run --limit 1000

detect-circular-flows-no-artefacts:
	python scripts/detect_circular_flows.py run --no-artefacts

run-circular-flow-rule:
	python scripts/run_circular_flow_rule.py run

run-circular-flow-rule-persist:
	python scripts/run_circular_flow_rule.py run --persist

run-circular-flow-rule-limited:
	python scripts/run_circular_flow_rule.py run --limit 1000

rules-list:
	python scripts/run_aml_rules.py list

run-aml-rules:
	python scripts/run_aml_rules.py run

run-aml-rules-persist:
	python scripts/run_aml_rules.py run --persist

run-aml-rules-limited:
	python scripts/run_aml_rules.py run --limit 1000

run-aml-rules-no-artefacts:
	python scripts/run_aml_rules.py run --no-artefacts

rules-docs-list:
	python scripts/generate_rule_documentation.py list

rules-docs-validate:
	python scripts/generate_rule_documentation.py validate

generate-rule-docs:
	python scripts/generate_rule_documentation.py generate

graph-config:
	python scripts/graph.py config

graph-health:
	python scripts/graph.py health

graph-constraints-list:
	python scripts/graph.py constraints-list

graph-constraints-ensure:
	python scripts/graph.py constraints-ensure

graph-load:
	python scripts/graph.py load

graph-load-limited:
	python scripts/graph.py load --limit 1000

graph-load-no-alerts:
	python scripts/graph.py load --no-alerts

graph-load-no-reconcile:
	python scripts/graph.py load --no-reconcile

graph-analytics:
	python scripts/graph.py analytics

graph-analytics-no-artefacts:
	python scripts/graph.py analytics --no-artefacts

graph-analytics-connected-components:
	python scripts/graph.py analytics --community-algorithm connected_components

graph-analytics-greedy-modularity:
	python scripts/graph.py analytics --community-algorithm greedy_modularity

graph-features-persist:
	python scripts/graph.py features-persist

graph-features-persist-no-artefacts:
	python scripts/graph.py features-persist --no-artefacts

graph-features-read:
	python scripts/graph.py features-read --latest

graph-features-summary:
	python scripts/graph.py features-summary

model-isolation-forest:
	python scripts/models.py isolation-forest train-score

model-isolation-forest-persist:
	python scripts/models.py isolation-forest train-score --persist

model-isolation-forest-limited:
	python scripts/models.py isolation-forest train-score --limit 1000

model-isolation-forest-no-mlflow:
	python scripts/models.py isolation-forest train-score --no-mlflow

anomaly-scores-read:
	python scripts/models.py anomaly-scores read --latest

anomaly-scores-summary:
	python scripts/models.py anomaly-scores summary

model-supervised-train:
	python scripts/models.py supervised train

model-supervised-train-persist:
	python scripts/models.py supervised train --persist

model-supervised-train-limited:
	python scripts/models.py supervised train --limit 1000

model-supervised-read-scores:
	python scripts/models.py supervised read-scores

model-supervised-read-runs:
	python scripts/models.py supervised read-runs

model-supervised-summary:
	python scripts/models.py supervised summary

model-comparison-run:
	python scripts/validation.py model-comparison run

model-comparison-run-persist:
	python scripts/validation.py model-comparison run --persist

model-comparison-run-limited:
	python scripts/validation.py model-comparison run --limit 1000

model-comparison-read-runs:
	python scripts/validation.py model-comparison read-runs

model-comparison-read-champion:
	python scripts/validation.py model-comparison read-champion --champion-only

model-comparison-summary:
	python scripts/validation.py model-comparison summary

monitoring-run:
	python scripts/validation.py monitoring run

monitoring-run-persist:
	python scripts/validation.py monitoring run --persist

monitoring-run-limited:
	python scripts/validation.py monitoring run --limit 1000

monitoring-read-runs:
	python scripts/validation.py monitoring read-runs

monitoring-read-drift:
	python scripts/validation.py monitoring read-drift

monitoring-read-volume:
	python scripts/validation.py monitoring read-volume

monitoring-read-segments:
	python scripts/validation.py monitoring read-segments

monitoring-read-backtesting:
	python scripts/validation.py monitoring read-backtesting

monitoring-summary:
	python scripts/validation.py monitoring summary

explainability-run:
	python scripts/validation.py explainability run

explainability-run-persist:
	python scripts/validation.py explainability run --persist

explainability-run-limited:
	python scripts/validation.py explainability run --limit 1000

explainability-read-runs:
	python scripts/validation.py explainability read-runs

explainability-read-features:
	python scripts/validation.py explainability read-features

explainability-read-decomposition:
	python scripts/validation.py explainability read-decomposition

explainability-read-reasons:
	python scripts/validation.py explainability read-reasons

explainability-read-model-cards:
	python scripts/validation.py explainability read-model-cards

explainability-summary:
	python scripts/validation.py explainability summary

governance-inventory-run:
	python scripts/governance.py inventory run

governance-inventory-run-persist:
	python scripts/governance.py inventory run --persist

governance-inventory-run-limited:
	python scripts/governance.py inventory run --limit 1000

governance-inventory-read-runs:
	python scripts/governance.py inventory read-runs

governance-inventory-read-lineage:
	python scripts/governance.py inventory read-lineage

governance-inventory-read-artefacts:
	python scripts/governance.py inventory read-artefacts

governance-inventory-read-processes:
	python scripts/governance.py inventory read-processes

governance-inventory-read-models:
	python scripts/governance.py inventory read-models

governance-inventory-read-validations:
	python scripts/governance.py inventory read-validations

governance-inventory-summary:
	python scripts/governance.py inventory summary

security-controls-run:
	python scripts/security.py controls run

security-controls-run-persist:
	python scripts/security.py controls run --persist

security-controls-run-limited:
	python scripts/security.py controls run --limit 1000

security-controls-read-runs:
	python scripts/security.py controls read-runs

security-controls-read-fields:
	python scripts/security.py controls read-fields

security-controls-read-permissions:
	python scripts/security.py controls read-permissions

security-controls-read-secrets:
	python scripts/security.py controls read-secrets

security-controls-read-audit-integrity:
	python scripts/security.py controls read-audit-integrity

security-controls-summary:
	python scripts/security.py controls summary

security-mask-preview:
	python scripts/security.py mask-preview --schema aml --table cases

release-readiness-run:
	python scripts/release.py readiness run --local-only

release-readiness-run-persist:
	python scripts/release.py readiness run --persist

release-readiness-no-artefacts:
	python scripts/release.py readiness run --local-only --no-artefacts

release-readiness-read-runs:
	python scripts/release.py readiness read-runs

release-readiness-read-checks:
	python scripts/release.py readiness read-checks

release-readiness-read-artefacts:
	python scripts/release.py readiness read-artefacts

release-readiness-read-evidence:
	python scripts/release.py readiness read-evidence

release-readiness-read-portfolio:
	python scripts/release.py readiness read-portfolio

release-readiness-summary:
	python scripts/release.py readiness summary

account-risk-score:
	python scripts/scoring.py account-risk score

account-risk-score-persist:
	python scripts/scoring.py account-risk score --persist

account-risk-score-limited:
	python scripts/scoring.py account-risk score --limit 1000

account-risk-score-no-artefacts:
	python scripts/scoring.py account-risk score --no-artefacts

account-risk-read:
	python scripts/scoring.py account-risk read --latest

account-risk-summary:
	python scripts/scoring.py account-risk summary

cases-generate:
	python scripts/cases.py generate

cases-generate-persist:
	python scripts/cases.py generate --persist

cases-generate-limited:
	python scripts/cases.py generate --limit 1000

cases-generate-no-artefacts:
	python scripts/cases.py generate --no-artefacts

cases-read:
	python scripts/cases.py read

cases-summary:
	python scripts/cases.py summary

case-risk-score:
	python scripts/cases.py risk-score

case-risk-score-persist:
	python scripts/cases.py risk-score --persist

case-risk-score-limited:
	python scripts/cases.py risk-score --limit 1000

case-risk-score-no-artefacts:
	python scripts/cases.py risk-score --no-artefacts

case-risk-read:
	python scripts/cases.py risk-read --latest

case-risk-summary:
	python scripts/cases.py risk-summary

case-evidence-build:
	python scripts/cases.py evidence-build

case-evidence-build-persist:
	python scripts/cases.py evidence-build --persist

case-evidence-build-limited:
	python scripts/cases.py evidence-build --limit 1000

case-evidence-build-no-artefacts:
	python scripts/cases.py evidence-build --no-artefacts

case-evidence-read:
	python scripts/cases.py evidence-read

case-evidence-summary:
	python scripts/cases.py evidence-summary

case-lifecycle-events:
	python scripts/cases.py lifecycle events

case-lifecycle-assignments:
	python scripts/cases.py lifecycle assignments

case-lifecycle-summary:
	python scripts/cases.py lifecycle summary

case-lifecycle-start-review:
	python scripts/cases.py lifecycle status --case-id SAMPLE_CASE_ID --to-status "In review" --decision-reason "Start review"

case-lifecycle-assign-sample:
	python scripts/cases.py lifecycle assign --case-id SAMPLE_CASE_ID --assigned-to local_analyst

labels-build:
	python scripts/labels.py build

labels-build-persist:
	python scripts/labels.py build --persist

labels-build-limited:
	python scripts/labels.py build --limit 1000

labels-read-case:
	python scripts/labels.py read case-labels

labels-read-account:
	python scripts/labels.py read account-labels

labels-summary:
	python scripts/labels.py summary

test-fan-flow-fixtures:
	python -m pytest tests/test_fan_flow_fixture_helpers.py \
		tests/test_fan_flow_joint_triggers.py \
		tests/test_fan_flow_rule_separation.py \
		tests/test_fan_flow_threshold_boundaries.py \
		tests/test_fan_flow_window_boundaries.py \
		tests/test_fan_flow_overlapping_windows.py \
		tests/test_fan_flow_evidence_isolation.py \
		tests/test_fan_flow_reason_codes.py \
		tests/test_fan_flow_risk_scores.py \
		tests/test_fan_flow_deterministic_ids.py \
		tests/test_fan_flow_counterparty_handling.py \
		tests/test_fan_flow_mutation_safety.py \
		tests/test_fan_flow_invalid_inputs.py \
		tests/test_fan_flow_scenario_alignment.py

test-movement-dormancy-fixtures:
	python -m pytest tests/test_movement_dormancy_fixture_helpers.py \
		tests/test_movement_dormancy_joint_triggers.py \
		tests/test_movement_dormancy_rule_separation.py \
		tests/test_movement_dormancy_rapid_thresholds.py \
		tests/test_movement_dormancy_dormant_thresholds.py \
		tests/test_movement_dormancy_window_boundaries.py \
		tests/test_movement_dormancy_overlapping_windows.py \
		tests/test_movement_dormancy_evidence_isolation.py \
		tests/test_movement_dormancy_reason_codes.py \
		tests/test_movement_dormancy_risk_scores.py \
		tests/test_movement_dormancy_deterministic_ids.py \
		tests/test_movement_dormancy_counterparty_handling.py \
		tests/test_movement_dormancy_mutation_safety.py \
		tests/test_movement_dormancy_invalid_inputs.py \
		tests/test_movement_dormancy_scenario_alignment.py

build-graph:
	python scripts/graph.py load

run-rules:
	python scripts/run_aml_rules.py run

train-model:
	python scripts/models.py isolation-forest train-score

generate-cases:
	python scripts/cases.py generate

dashboard:
	streamlit run app/streamlit_app.py

dashboard-config:
	python scripts/dashboard.py config

dashboard-health:
	python scripts/dashboard.py health

dashboard-summary:
	python scripts/dashboard.py summary

dashboard-graph-summary:
	python scripts/dashboard.py graph-summary

dashboard-account-summary:
	python scripts/dashboard.py account-summary --account-id SAMPLE_ACCOUNT_ID

dashboard-model-summary:
	python scripts/dashboard.py model-summary

dashboard-audit-summary:
	python scripts/dashboard.py audit-summary

dashboard-validation-index:
	python scripts/dashboard.py validation-index

demo-plan:
	python scripts/demo.py plan

demo-plan-with-reset:
	python scripts/demo.py plan --include-reset

demo-readiness:
	python scripts/demo.py readiness --write-artefacts

demo-run-dry:
	python scripts/demo.py run --dry-run

demo-run:
	python scripts/demo.py run --write-artefacts

demo-run-with-reset:
	python scripts/demo.py run --include-reset --write-artefacts

demo-validate:
	python scripts/demo.py validate --write-artefacts

demo-artefacts:
	python scripts/demo.py artefacts

run-dashboard:
	uv run streamlit run app/streamlit_app.py

# Cleaning
clean:
	python scripts/dev.py clean

clean-caches:
	python scripts/dev.py clean
