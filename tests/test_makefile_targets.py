"""Static tests for Makefile target coverage."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"

REQUIRED_TARGETS = {
    "setup",
    "install",
    "check-env",
    "info",
    "verify-scaffold",
    "lint",
    "format",
    "typecheck",
    "test",
    "test-cov",
    "check",
    "services-up",
    "services-down",
    "services-restart",
    "services-logs",
    "services-ps",
    "postgres-up",
    "neo4j-up",
    "mlflow-up",
    "db-check",
    "db-version",
    "db-list-schemas",
    "db-list-staging-tables",
    "db-init",
    "db-reset",
    "db-seed-smoke",
    "db-delete-smoke-seed",
    "db-recreate-and-seed",
    "run-pipeline",
    "generate-data",
    "generate-data-small",
    "generate-data-scenarios",
    "generate-data-scenarios-small",
    "reference-summary",
    "reference-summary-scenarios",
    "validate-data",
    "validate-data-baseline",
    "validate-data-strict",
    "validate-data-audit",
    "load-data",
    "load-data-baseline",
    "load-data-scenarios",
    "stage-data",
    "stage-data-no-validate",
    "stage-data-limited",
    "generate-data-dictionary",
    "generate-dataset-summary",
    "generate-dataset-summary-baseline",
    "generate-dataset-summary-staged",
    "generate-account-features",
    "generate-account-features-limited",
    "generate-account-features-extended",
    "generate-account-features-extended-limited",
    "persist-account-features",
    "persist-account-features-no-audit",
    "read-mart-account-features",
    "alerts-schema-info",
    "alerts-read",
    "run-structuring-rule",
    "run-structuring-rule-persist",
    "run-structuring-rule-limited",
    "test-structuring-fixtures",
    "run-fan-in-rule",
    "run-fan-in-rule-persist",
    "run-fan-in-rule-limited",
    "run-fan-out-rule",
    "run-fan-out-rule-persist",
    "run-fan-out-rule-limited",
    "run-rapid-movement-rule",
    "run-rapid-movement-rule-persist",
    "run-rapid-movement-rule-limited",
    "run-dormant-reactivation-rule",
    "run-dormant-reactivation-rule-persist",
    "run-dormant-reactivation-rule-limited",
    "detect-circular-flows",
    "detect-circular-flows-limited",
    "detect-circular-flows-no-artefacts",
    "run-circular-flow-rule",
    "run-circular-flow-rule-persist",
    "run-circular-flow-rule-limited",
    "rules-list",
    "run-aml-rules",
    "run-aml-rules-persist",
    "run-aml-rules-limited",
    "run-aml-rules-no-artefacts",
    "rules-docs-list",
    "rules-docs-validate",
    "generate-rule-docs",
    "graph-config",
    "graph-health",
    "graph-constraints-list",
    "graph-constraints-ensure",
    "graph-load",
    "graph-load-limited",
    "graph-load-no-alerts",
    "graph-load-no-reconcile",
    "graph-analytics",
    "graph-analytics-no-artefacts",
    "graph-analytics-connected-components",
    "graph-analytics-greedy-modularity",
    "graph-features-persist",
    "graph-features-persist-no-artefacts",
    "graph-features-read",
    "graph-features-summary",
    "model-isolation-forest",
    "model-isolation-forest-persist",
    "model-isolation-forest-limited",
    "model-isolation-forest-no-mlflow",
    "anomaly-scores-read",
    "anomaly-scores-summary",
    "model-comparison-run",
    "model-comparison-run-persist",
    "model-comparison-run-limited",
    "model-comparison-read-runs",
    "model-comparison-read-champion",
    "model-comparison-summary",
    "monitoring-run",
    "monitoring-run-persist",
    "monitoring-run-limited",
    "monitoring-read-runs",
    "monitoring-read-drift",
    "monitoring-read-volume",
    "monitoring-read-segments",
    "monitoring-read-backtesting",
    "monitoring-summary",
    "explainability-run",
    "explainability-run-persist",
    "explainability-run-limited",
    "explainability-read-runs",
    "explainability-read-features",
    "explainability-read-decomposition",
    "explainability-read-reasons",
    "explainability-read-model-cards",
    "explainability-summary",
    "governance-inventory-run",
    "governance-inventory-run-persist",
    "governance-inventory-run-limited",
    "governance-inventory-read-runs",
    "governance-inventory-read-lineage",
    "governance-inventory-read-artefacts",
    "governance-inventory-read-processes",
    "governance-inventory-read-models",
    "governance-inventory-read-validations",
    "governance-inventory-summary",
    "security-controls-run",
    "security-controls-run-persist",
    "security-controls-run-limited",
    "security-controls-read-runs",
    "security-controls-read-fields",
    "security-controls-read-permissions",
    "security-controls-read-secrets",
    "security-controls-read-audit-integrity",
    "security-controls-summary",
    "security-mask-preview",
    "release-readiness-run",
    "release-readiness-run-persist",
    "release-readiness-no-artefacts",
    "release-readiness-read-runs",
    "release-readiness-read-checks",
    "release-readiness-read-artefacts",
    "release-readiness-read-evidence",
    "release-readiness-read-portfolio",
    "release-readiness-summary",
    "account-risk-score",
    "account-risk-score-persist",
    "account-risk-score-limited",
    "account-risk-score-no-artefacts",
    "account-risk-read",
    "account-risk-summary",
    "cases-generate",
    "cases-generate-persist",
    "cases-generate-limited",
    "cases-generate-no-artefacts",
    "cases-read",
    "cases-summary",
    "case-risk-score",
    "case-risk-score-persist",
    "case-risk-score-limited",
    "case-risk-score-no-artefacts",
    "case-risk-read",
    "case-risk-summary",
    "case-evidence-build",
    "case-evidence-build-persist",
    "case-evidence-build-limited",
    "case-evidence-build-no-artefacts",
    "case-evidence-read",
    "case-evidence-summary",
    "case-lifecycle-events",
    "case-lifecycle-assignments",
    "case-lifecycle-summary",
    "case-lifecycle-start-review",
    "case-lifecycle-assign-sample",
    "labels-build",
    "labels-build-persist",
    "labels-build-limited",
    "labels-read-case",
    "labels-read-account",
    "labels-summary",
    "dashboard",
    "dashboard-config",
    "dashboard-health",
    "dashboard-summary",
    "dashboard-graph-summary",
    "dashboard-account-summary",
    "dashboard-model-summary",
    "dashboard-audit-summary",
    "dashboard-validation-index",
    "demo-plan",
    "demo-plan-with-reset",
    "demo-readiness",
    "demo-run-dry",
    "demo-run",
    "demo-run-with-reset",
    "demo-validate",
    "demo-artefacts",
    "test-fan-flow-fixtures",
    "test-movement-dormancy-fixtures",
    "build-graph",
    "run-rules",
    "train-model",
    "generate-cases",
    "run-dashboard",
    "clean",
    "clean-caches",
}

def makefile_text() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


def test_makefile_exists() -> None:
    assert MAKEFILE.is_file()


def test_required_targets_exist() -> None:
    text = makefile_text()

    for target in REQUIRED_TARGETS:
        assert re.search(rf"^{re.escape(target)}:", text, flags=re.MULTILINE), target


def test_phony_exists_and_includes_required_targets() -> None:
    text = makefile_text()
    phony_line = " ".join(line for line in text.splitlines() if line.startswith(".PHONY:"))

    for target in REQUIRED_TARGETS:
        assert target in phony_line


def test_docker_compose_v2_syntax_is_used() -> None:
    text = makefile_text()

    assert "docker compose" in text
    assert "docker-compose" not in text


def test_run_dashboard_references_streamlit_entrypoint() -> None:
    text = makefile_text()

    assert "app/streamlit_app.py" in text


def test_legacy_alias_targets_call_real_commands() -> None:
    text = makefile_text()

    assert re.search(r"build-graph:\n\tpython scripts/graph.py load", text)
    assert re.search(r"run-rules:\n\tpython scripts/run_aml_rules.py run", text)
    assert re.search(
        r"train-model:\n\tpython scripts/models.py isolation-forest train-score",
        text,
    )
    alias_section = text.split("build-graph:", maxsplit=1)[1].split(
        "generate-cases:",
        maxsplit=1,
    )[0]
    assert "not implemented yet" not in alias_section.lower()
    assert "reserved for a later ticket" not in alias_section.lower()


def test_model_targets_use_models_cli_and_are_scoped() -> None:
    text = makefile_text()

    assert re.search(
        r"model-isolation-forest:\n\tpython scripts/models.py isolation-forest train-score",
        text,
    )
    assert re.search(
        r"model-isolation-forest-persist:\n\tpython scripts/models.py "
        r"isolation-forest train-score --persist",
        text,
    )
    assert re.search(
        r"model-isolation-forest-limited:\n\tpython scripts/models.py "
        r"isolation-forest train-score --limit 1000",
        text,
    )
    assert re.search(
        r"model-isolation-forest-no-mlflow:\n\tpython scripts/models.py "
        r"isolation-forest train-score --no-mlflow",
        text,
    )
    assert re.search(
        r"anomaly-scores-read:\n\tpython scripts/models.py anomaly-scores read --latest",
        text,
    )
    assert re.search(
        r"anomaly-scores-summary:\n\tpython scripts/models.py anomaly-scores summary",
        text,
    )
    model_section = text.split("model-isolation-forest:", maxsplit=1)[1].split(
        "test-fan-flow-fixtures:",
        maxsplit=1,
    )[0]
    assert "db-reset" not in model_section
    assert "run_aml_rules" not in model_section
    assert "graph.py load" not in model_section
    assert "generate-cases" not in model_section
    assert "streamlit" not in model_section


def test_account_risk_targets_use_scoring_cli_and_expected_commands() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:account-risk-score|account-risk-score-persist|account-risk-score-limited|"
        r"account-risk-score-no-artefacts|account-risk-read|account-risk-summary):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/scoring.py" in command for command in target_blocks)
    assert re.search(r"account-risk-score:\n\tpython scripts/scoring.py account-risk score", text)
    assert re.search(
        r"account-risk-score-persist:\n\tpython scripts/scoring.py account-risk score --persist",
        text,
    )
    assert re.search(
        r"account-risk-score-limited:\n\tpython scripts/scoring.py account-risk score --limit 1000",
        text,
    )
    assert re.search(
        r"account-risk-score-no-artefacts:\n\tpython scripts/scoring.py account-risk "
        r"score --no-artefacts",
        text,
    )
    assert re.search(
        r"account-risk-read:\n\tpython scripts/scoring.py account-risk read --latest",
        text,
    )
    assert re.search(
        r"account-risk-summary:\n\tpython scripts/scoring.py account-risk summary",
        text,
    )
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("graph.py load" not in command for command in target_blocks)
    assert all("models.py isolation-forest train-score" not in command for command in target_blocks)
    assert all("generate-cases" not in command for command in target_blocks)


def test_case_targets_use_cases_cli_and_expected_commands() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:cases-generate|cases-generate-persist|cases-generate-limited|"
        r"cases-generate-no-artefacts|cases-read|cases-summary):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/cases.py" in command for command in target_blocks)
    assert re.search(r"cases-generate:\n\tpython scripts/cases.py generate", text)
    assert re.search(
        r"cases-generate-persist:\n\tpython scripts/cases.py generate --persist",
        text,
    )
    assert re.search(
        r"cases-generate-limited:\n\tpython scripts/cases.py generate --limit 1000",
        text,
    )
    assert re.search(
        r"cases-generate-no-artefacts:\n\tpython scripts/cases.py generate --no-artefacts",
        text,
    )
    assert re.search(r"cases-read:\n\tpython scripts/cases.py read", text)
    assert re.search(r"cases-summary:\n\tpython scripts/cases.py summary", text)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("graph.py load" not in command for command in target_blocks)
    assert all("models.py isolation-forest train-score" not in command for command in target_blocks)
    assert all("scoring.py account-risk score" not in command for command in target_blocks)


def test_case_risk_targets_use_cases_cli_and_expected_commands() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:case-risk-score|case-risk-score-persist|case-risk-score-limited|"
        r"case-risk-score-no-artefacts|case-risk-read|case-risk-summary):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/cases.py" in command for command in target_blocks)
    assert re.search(r"case-risk-score:\n\tpython scripts/cases.py risk-score", text)
    assert re.search(
        r"case-risk-score-persist:\n\tpython scripts/cases.py risk-score --persist",
        text,
    )
    assert re.search(
        r"case-risk-score-limited:\n\tpython scripts/cases.py risk-score --limit 1000",
        text,
    )
    assert re.search(
        r"case-risk-score-no-artefacts:\n\tpython scripts/cases.py risk-score --no-artefacts",
        text,
    )
    assert re.search(r"case-risk-read:\n\tpython scripts/cases.py risk-read --latest", text)
    assert re.search(r"case-risk-summary:\n\tpython scripts/cases.py risk-summary", text)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("graph.py load" not in command for command in target_blocks)
    assert all("models.py isolation-forest train-score" not in command for command in target_blocks)
    assert all("scoring.py account-risk score" not in command for command in target_blocks)
    assert all("cases.py generate" not in command for command in target_blocks)


def test_case_evidence_targets_use_cases_cli_and_expected_commands() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:case-evidence-build|case-evidence-build-persist|"
        r"case-evidence-build-limited|case-evidence-build-no-artefacts|"
        r"case-evidence-read|case-evidence-summary):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/cases.py" in command for command in target_blocks)
    assert re.search(r"case-evidence-build:\n\tpython scripts/cases.py evidence-build", text)
    assert re.search(
        r"case-evidence-build-persist:\n\tpython scripts/cases.py evidence-build --persist",
        text,
    )
    assert re.search(
        r"case-evidence-build-limited:\n\tpython scripts/cases.py evidence-build --limit 1000",
        text,
    )
    assert re.search(
        r"case-evidence-build-no-artefacts:\n\tpython scripts/cases.py "
        r"evidence-build --no-artefacts",
        text,
    )
    assert re.search(r"case-evidence-read:\n\tpython scripts/cases.py evidence-read", text)
    assert re.search(
        r"case-evidence-summary:\n\tpython scripts/cases.py evidence-summary",
        text,
    )
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("graph.py load" not in command for command in target_blocks)
    assert all("models.py isolation-forest train-score" not in command for command in target_blocks)
    assert all("scoring.py account-risk score" not in command for command in target_blocks)
    assert all("cases.py generate" not in command for command in target_blocks)
    assert all("cases.py risk-score" not in command for command in target_blocks)


def test_case_lifecycle_targets_use_cases_cli_and_expected_commands() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:case-lifecycle-events|case-lifecycle-assignments|case-lifecycle-summary|"
        r"case-lifecycle-start-review|case-lifecycle-assign-sample):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/cases.py" in command for command in target_blocks)
    assert all(" lifecycle " in command for command in target_blocks)
    assert re.search(r"case-lifecycle-events:\n\tpython scripts/cases.py lifecycle events", text)
    assert re.search(
        r"case-lifecycle-assignments:\n\tpython scripts/cases.py lifecycle assignments",
        text,
    )
    assert re.search(r"case-lifecycle-summary:\n\tpython scripts/cases.py lifecycle summary", text)
    assert "SAMPLE_CASE_ID" in text
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("graph.py load" not in command for command in target_blocks)
    assert all("models.py isolation-forest train-score" not in command for command in target_blocks)
    assert all("scoring.py account-risk score" not in command for command in target_blocks)
    assert all("cases.py generate" not in command for command in target_blocks)
    assert all("cases.py risk-score" not in command for command in target_blocks)
    assert all("evidence-build" not in command for command in target_blocks)


def test_dashboard_targets_use_dashboard_cli_and_streamlit_entrypoint() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:dashboard|dashboard-config|dashboard-health|dashboard-summary|"
        r"dashboard-graph-summary|dashboard-account-summary|dashboard-model-summary|"
        r"dashboard-audit-summary|dashboard-validation-index):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert re.search(r"dashboard:\n\tstreamlit run app/streamlit_app.py", text)
    assert re.search(r"dashboard-config:\n\tpython scripts/dashboard.py config", text)
    assert re.search(r"dashboard-health:\n\tpython scripts/dashboard.py health", text)
    assert re.search(r"dashboard-summary:\n\tpython scripts/dashboard.py summary", text)
    assert re.search(
        r"dashboard-graph-summary:\n\tpython scripts/dashboard.py graph-summary",
        text,
    )
    assert re.search(
        r"dashboard-account-summary:\n\tpython scripts/dashboard.py account-summary",
        text,
    )
    assert re.search(r"dashboard-model-summary:\n\tpython scripts/dashboard.py model-summary", text)
    assert re.search(r"dashboard-audit-summary:\n\tpython scripts/dashboard.py audit-summary", text)
    assert re.search(
        r"dashboard-validation-index:\n\tpython scripts/dashboard.py validation-index",
        text,
    )
    assert "SAMPLE_ACCOUNT_ID" in text
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("graph.py load" not in command for command in target_blocks)
    assert all("models.py isolation-forest train-score" not in command for command in target_blocks)
    assert all("scoring.py account-risk score" not in command for command in target_blocks)
    assert all("cases.py generate" not in command for command in target_blocks)
    assert all("cases.py risk-score" not in command for command in target_blocks)
    assert all("evidence-build" not in command for command in target_blocks)
    assert all("lifecycle status" not in command for command in target_blocks)


def test_run_pipeline_prints_non_destructive_sequence() -> None:
    text = makefile_text()
    match = re.search(r"run-pipeline:\n\t@echo \"([^\"]+)\"", text)

    assert match is not None
    assert "make stage-data" in match.group(1)
    assert "db-reset" not in match.group(1)


def test_synthetic_generation_targets_use_cli_script() -> None:
    text = makefile_text()

    assert "generate-data:" in text
    assert "generate-data-small:" in text
    assert "generate-data-scenarios:" in text
    assert "generate-data-scenarios-small:" in text
    assert "reference-summary-scenarios:" in text
    assert "scripts/build_gold_from_silver.py" in text


def test_load_data_targets_use_raw_ingestion_cli() -> None:
    text = makefile_text()

    assert "load-data:" in text
    assert "load-data-baseline:" in text
    assert "load-data-scenarios:" in text
    assert "scripts/ingest_raw.py" in text


def test_stage_data_targets_use_staging_cli() -> None:
    text = makefile_text()

    assert "stage-data:" in text
    assert "stage-data-no-validate:" in text
    assert "stage-data-limited:" in text
    assert "scripts/stage_data.py" in text
    assert "--no-validate" in text
    assert "--limit 1000" in text


def test_generate_data_dictionary_target_uses_cli_script() -> None:
    text = makefile_text()

    assert "generate-data-dictionary:" in text
    assert "scripts/generate_data_dictionary.py" in text


def test_generate_dataset_summary_targets_use_cli_script() -> None:
    text = makefile_text()

    assert "generate-dataset-summary:" in text
    assert "generate-dataset-summary-baseline:" in text
    assert "generate-dataset-summary-staged:" in text
    assert "scripts/generate_dataset_summary.py" in text


def test_generate_dataset_summary_targets_use_expected_commands() -> None:
    text = makefile_text()

    assert re.search(
        r"generate-dataset-summary:\n\tpython scripts/generate_dataset_summary.py latest",
        text,
    )
    assert re.search(
        r"generate-dataset-summary-baseline:\n\tpython scripts/generate_dataset_summary.py latest",
        text,
    )
    assert re.search(
        r"generate-dataset-summary-staged:\n\tpython scripts/generate_dataset_summary.py staged",
        text,
    )


def test_generate_account_feature_targets_use_cli_script() -> None:
    text = makefile_text()

    assert "generate-account-features:" in text
    assert "generate-account-features-limited:" in text
    assert "generate-account-features-extended:" in text
    assert "generate-account-features-extended-limited:" in text
    assert "scripts/generate_account_features.py" in text


def test_generate_account_feature_targets_use_staged_command_and_are_non_destructive() -> None:
    text = makefile_text()

    assert re.search(
        r"generate-account-features:\n\tpython scripts/generate_account_features.py staged",
        text,
    )
    assert re.search(
        r"generate-account-features-limited:\n\tpython scripts/generate_account_features.py "
        r"staged --limit 1000",
        text,
    )
    assert re.search(
        r"generate-account-features-extended:\n\tpython scripts/generate_account_features.py "
        r"staged --extended",
        text,
    )
    assert re.search(
        r"generate-account-features-extended-limited:\n\tpython "
        r"scripts/generate_account_features.py staged --extended --limit 1000",
        text,
    )
    feature_target_blocks = re.findall(
        r"generate-account-features(?:-extended)?(?:-limited)?:\n\t([^\n]+)",
        text,
    )
    assert feature_target_blocks
    assert all("db-reset" not in command for command in feature_target_blocks)


def test_extended_account_feature_targets_include_extended_flag() -> None:
    text = makefile_text()

    assert re.search(
        r"generate-account-features-extended:\n\tpython scripts/generate_account_features.py "
        r"staged --extended",
        text,
    )
    assert re.search(
        r"generate-account-features-extended-limited:\n\tpython "
        r"scripts/generate_account_features.py staged --extended --limit 1000",
        text,
    )


def test_feature_persistence_targets_use_cli_script_and_expected_flags() -> None:
    text = makefile_text()

    assert re.search(
        r"persist-account-features:\n\tpython scripts/generate_account_features.py "
        r"staged --extended --persist",
        text,
    )
    assert re.search(
        r"persist-account-features-no-audit:\n\tpython "
        r"scripts/generate_account_features.py staged --extended --persist --no-audit",
        text,
    )
    assert re.search(
        r"read-mart-account-features:\n\tpython scripts/generate_account_features.py "
        r"staged --read-mart",
        text,
    )


def test_feature_persistence_targets_are_non_destructive() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:persist-account-features(?:-no-audit)?|read-mart-account-features):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/generate_account_features.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("reset" not in command for command in target_blocks)


def test_alert_targets_use_alert_cli_script_and_expected_commands() -> None:
    text = makefile_text()

    assert re.search(
        r"alerts-schema-info:\n\tpython scripts/alerts.py schema-info",
        text,
    )
    assert re.search(
        r"alerts-read:\n\tpython scripts/alerts.py read",
        text,
    )


def test_alert_targets_are_non_destructive_and_do_not_run_rules() -> None:
    text = makefile_text()
    target_blocks = re.findall(r"alerts-(?:schema-info|read):\n\t([^\n]+)", text)

    assert target_blocks
    assert all("scripts/alerts.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)


def test_structuring_rule_targets_use_cli_script_and_expected_flags() -> None:
    text = makefile_text()

    assert re.search(
        r"run-structuring-rule:\n\tpython scripts/run_structuring_rule.py run",
        text,
    )
    assert re.search(
        r"run-structuring-rule-persist:\n\tpython scripts/run_structuring_rule.py "
        r"run --persist",
        text,
    )
    assert re.search(
        r"run-structuring-rule-limited:\n\tpython scripts/run_structuring_rule.py "
        r"run --limit 1000",
        text,
    )


def test_structuring_rule_targets_are_non_destructive_and_rule_scoped() -> None:
    text = makefile_text()
    target_blocks = re.findall(r"run-structuring-rule(?:-persist|-limited)?:\n\t([^\n]+)", text)

    assert target_blocks
    assert all("scripts/run_structuring_rule.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run-fan" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)


def test_structuring_fixture_target_runs_expected_fixture_tests() -> None:
    text = makefile_text()

    assert re.search(r"^test-structuring-fixtures:", text, flags=re.MULTILINE)
    for filename in (
        "tests/test_structuring_rule_fixtures_trigger.py",
        "tests/test_structuring_rule_fixtures_non_trigger.py",
        "tests/test_structuring_rule_fixtures_thresholds.py",
        "tests/test_structuring_rule_fixtures_windows.py",
        "tests/test_structuring_rule_fixtures_multi_account.py",
        "tests/test_structuring_rule_fixtures_counterparties.py",
        "tests/test_structuring_rule_fixtures_reason_evidence.py",
        "tests/test_structuring_rule_fixtures_risk_score.py",
        "tests/test_structuring_rule_scenario_alignment.py",
        "tests/test_structuring_rule_deterministic_ids.py",
        "tests/test_structuring_rule_mutation_safety.py",
        "tests/test_structuring_rule_invalid_inputs.py",
        "tests/test_structuring_fixture_helpers.py",
    ):
        assert filename in text


def test_structuring_fixture_target_is_offline_and_non_destructive() -> None:
    text = makefile_text()
    match = re.search(
        r"test-structuring-fixtures:\n((?:\t[^\n]+(?: \\\n)?)+)",
        text,
    )

    assert match is not None
    command_block = match.group(1)
    assert "docker" not in command_block
    assert "db-reset" not in command_block
    assert "reset_database" not in command_block
    assert "services-up" not in command_block


def test_fan_in_rule_targets_use_cli_script_and_expected_flags() -> None:
    text = makefile_text()

    assert re.search(
        r"run-fan-in-rule:\n\tpython scripts/run_fan_in_rule.py run",
        text,
    )
    assert re.search(
        r"run-fan-in-rule-persist:\n\tpython scripts/run_fan_in_rule.py run --persist",
        text,
    )
    assert re.search(
        r"run-fan-in-rule-limited:\n\tpython scripts/run_fan_in_rule.py run --limit 1000",
        text,
    )


def test_fan_in_rule_targets_are_non_destructive_and_rule_scoped() -> None:
    text = makefile_text()
    target_blocks = re.findall(r"run-fan-in-rule(?:-persist|-limited)?:\n\t([^\n]+)", text)

    assert target_blocks
    assert all("scripts/run_fan_in_rule.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run-structuring-rule" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)


def test_fan_out_rule_targets_use_cli_script_and_expected_flags() -> None:
    text = makefile_text()

    assert re.search(
        r"run-fan-out-rule:\n\tpython scripts/run_fan_out_rule.py run",
        text,
    )
    assert re.search(
        r"run-fan-out-rule-persist:\n\tpython scripts/run_fan_out_rule.py run --persist",
        text,
    )
    assert re.search(
        r"run-fan-out-rule-limited:\n\tpython scripts/run_fan_out_rule.py run --limit 1000",
        text,
    )


def test_fan_out_rule_targets_are_non_destructive_and_rule_scoped() -> None:
    text = makefile_text()
    target_blocks = re.findall(r"run-fan-out-rule(?:-persist|-limited)?:\n\t([^\n]+)", text)

    assert target_blocks
    assert all("scripts/run_fan_out_rule.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run-structuring-rule" not in command for command in target_blocks)
    assert all("run-fan-in-rule" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)


def test_rapid_movement_rule_targets_use_cli_script_and_expected_flags() -> None:
    text = makefile_text()

    assert re.search(
        r"run-rapid-movement-rule:\n\tpython scripts/run_rapid_movement_rule.py run",
        text,
    )
    assert re.search(
        r"run-rapid-movement-rule-persist:\n\tpython "
        r"scripts/run_rapid_movement_rule.py run --persist",
        text,
    )
    assert re.search(
        r"run-rapid-movement-rule-limited:\n\tpython "
        r"scripts/run_rapid_movement_rule.py run --limit 1000",
        text,
    )


def test_rapid_movement_rule_targets_are_non_destructive_and_rule_scoped() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"run-rapid-movement-rule(?:-persist|-limited)?:\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/run_rapid_movement_rule.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run-structuring-rule" not in command for command in target_blocks)
    assert all("run-fan-in-rule" not in command for command in target_blocks)
    assert all("run-fan-out-rule" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)


def test_dormant_reactivation_rule_targets_use_cli_script_and_expected_flags() -> None:
    text = makefile_text()

    assert re.search(
        r"run-dormant-reactivation-rule:\n\tpython "
        r"scripts/run_dormant_reactivation_rule.py run",
        text,
    )
    assert re.search(
        r"run-dormant-reactivation-rule-persist:\n\tpython "
        r"scripts/run_dormant_reactivation_rule.py run --persist",
        text,
    )
    assert re.search(
        r"run-dormant-reactivation-rule-limited:\n\tpython "
        r"scripts/run_dormant_reactivation_rule.py run --limit 1000",
        text,
    )


def test_dormant_reactivation_targets_are_non_destructive_and_rule_scoped() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"run-dormant-reactivation-rule(?:-persist|-limited)?:\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/run_dormant_reactivation_rule.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run-structuring-rule" not in command for command in target_blocks)
    assert all("run-fan-in-rule" not in command for command in target_blocks)
    assert all("run-fan-out-rule" not in command for command in target_blocks)
    assert all("run-rapid-movement-rule" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)


def test_circular_flow_targets_use_cli_script_and_expected_flags() -> None:
    text = makefile_text()

    assert re.search(
        r"detect-circular-flows:\n\tpython scripts/detect_circular_flows.py run",
        text,
    )
    assert re.search(
        r"detect-circular-flows-limited:\n\tpython "
        r"scripts/detect_circular_flows.py run --limit 1000",
        text,
    )
    assert re.search(
        r"detect-circular-flows-no-artefacts:\n\tpython "
        r"scripts/detect_circular_flows.py run --no-artefacts",
        text,
    )


def test_circular_flow_targets_are_detection_only_and_rule_scoped() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"detect-circular-flows(?:-limited|-no-artefacts)?:\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/detect_circular_flows.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("--persist" not in command for command in target_blocks)
    assert all("alerts" not in command for command in target_blocks)
    assert all("run-structuring-rule" not in command for command in target_blocks)
    assert all("run-fan-in-rule" not in command for command in target_blocks)
    assert all("run-fan-out-rule" not in command for command in target_blocks)
    assert all("run-rapid-movement-rule" not in command for command in target_blocks)
    assert all("run-dormant-reactivation-rule" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)


def test_circular_flow_rule_targets_use_cli_script_and_expected_flags() -> None:
    text = makefile_text()

    assert re.search(
        r"run-circular-flow-rule:\n\tpython scripts/run_circular_flow_rule.py run",
        text,
    )
    assert re.search(
        r"run-circular-flow-rule-persist:\n\tpython "
        r"scripts/run_circular_flow_rule.py run --persist",
        text,
    )
    assert re.search(
        r"run-circular-flow-rule-limited:\n\tpython "
        r"scripts/run_circular_flow_rule.py run --limit 1000",
        text,
    )


def test_circular_flow_rule_targets_are_non_destructive_and_rule_scoped() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"run-circular-flow-rule(?:-persist|-limited)?:\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/run_circular_flow_rule.py" in command for command in target_blocks)
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run-structuring-rule" not in command for command in target_blocks)
    assert all("run-fan-in-rule" not in command for command in target_blocks)
    assert all("run-fan-out-rule" not in command for command in target_blocks)
    assert all("run-rapid-movement-rule" not in command for command in target_blocks)
    assert all("run-dormant-reactivation-rule" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)
    assert "scripts/detect_circular_flows.py" in text


def test_unified_rule_engine_targets_use_runner_script() -> None:
    text = makefile_text()
    target_blocks = re.findall(r"(?:rules-list|run-aml-rules(?:-[\w]+)?):\n\t([^\n]+)", text)

    assert target_blocks
    assert all("scripts/run_aml_rules.py" in command for command in target_blocks)


def test_rules_list_target_uses_list_command() -> None:
    text = makefile_text()

    assert re.search(r"rules-list:\n\tpython scripts/run_aml_rules.py list", text)


def test_unified_rule_engine_run_targets_use_run_command() -> None:
    text = makefile_text()
    for target in (
        "run-aml-rules",
        "run-aml-rules-persist",
        "run-aml-rules-limited",
        "run-aml-rules-no-artefacts",
    ):
        assert re.search(rf"{target}:\n\tpython scripts/run_aml_rules.py run", text)


def test_unified_rule_engine_persist_target_includes_persist() -> None:
    text = makefile_text()

    assert re.search(
        r"run-aml-rules-persist:\n\tpython scripts/run_aml_rules.py run --persist",
        text,
    )


def test_unified_rule_engine_limited_target_includes_limit() -> None:
    text = makefile_text()

    assert re.search(
        r"run-aml-rules-limited:\n\tpython scripts/run_aml_rules.py run --limit 1000",
        text,
    )


def test_unified_rule_engine_no_artefacts_target_includes_no_artefacts() -> None:
    text = makefile_text()

    assert re.search(
        r"run-aml-rules-no-artefacts:\n\tpython scripts/run_aml_rules.py run --no-artefacts",
        text,
    )


def test_unified_rule_engine_targets_are_non_destructive() -> None:
    text = makefile_text()
    target_blocks = re.findall(r"(?:rules-list|run-aml-rules(?:-[\w]+)?):\n\t([^\n]+)", text)

    assert target_blocks
    assert all("db-reset" not in command for command in target_blocks)
    assert all("reset --yes" not in command for command in target_blocks)


def test_unified_rule_engine_targets_do_not_run_ml_or_case_generation() -> None:
    text = makefile_text()
    target_blocks = re.findall(r"(?:rules-list|run-aml-rules(?:-[\w]+)?):\n\t([^\n]+)", text)

    assert target_blocks
    assert all("train-model" not in command for command in target_blocks)
    assert all("generate-cases" not in command for command in target_blocks)


def test_rule_documentation_targets_use_documentation_cli() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:rules-docs-list|rules-docs-validate|generate-rule-docs):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/generate_rule_documentation.py" in command for command in target_blocks)


def test_rule_documentation_targets_use_expected_subcommands() -> None:
    text = makefile_text()

    assert re.search(
        r"rules-docs-list:\n\tpython scripts/generate_rule_documentation.py list",
        text,
    )
    assert re.search(
        r"rules-docs-validate:\n\tpython scripts/generate_rule_documentation.py validate",
        text,
    )
    assert re.search(
        r"generate-rule-docs:\n\tpython scripts/generate_rule_documentation.py generate",
        text,
    )


def test_rule_documentation_targets_are_offline_and_non_destructive() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:rules-docs-list|rules-docs-validate|generate-rule-docs):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("db-reset" not in command for command in target_blocks)
    assert all("db.py" not in command for command in target_blocks)
    assert all("create_database_engine" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("run_structuring_rule.py" not in command for command in target_blocks)
    assert all("train-model" not in command for command in target_blocks)
    assert all("generate-cases" not in command for command in target_blocks)


def test_graph_targets_use_graph_cli() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:graph-config|graph-health|graph-constraints-list|graph-constraints-ensure):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/graph.py" in command for command in target_blocks)


def test_graph_targets_use_expected_subcommands() -> None:
    text = makefile_text()

    assert re.search(r"graph-config:\n\tpython scripts/graph.py config", text)
    assert re.search(r"graph-health:\n\tpython scripts/graph.py health", text)
    assert re.search(
        r"graph-constraints-list:\n\tpython scripts/graph.py constraints-list",
        text,
    )
    assert re.search(
        r"graph-constraints-ensure:\n\tpython scripts/graph.py constraints-ensure",
        text,
    )


def test_graph_targets_are_offline_scoped_and_non_destructive() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:graph-config|graph-health|graph-constraints-list|graph-constraints-ensure):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("db-reset" not in command for command in target_blocks)
    assert all("scripts/db.py" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)
    assert all("train-model" not in command for command in target_blocks)
    assert all("generate-cases" not in command for command in target_blocks)


def test_graph_load_targets_use_graph_cli_and_load_command() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:graph-load|graph-load-limited|graph-load-no-alerts|"
        r"graph-load-no-reconcile):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/graph.py" in command for command in target_blocks)
    assert all(" load" in command for command in target_blocks)


def test_graph_load_targets_use_expected_flags() -> None:
    text = makefile_text()

    assert re.search(r"graph-load:\n\tpython scripts/graph.py load", text)
    assert re.search(r"graph-load-limited:\n\tpython scripts/graph.py load --limit 1000", text)
    assert re.search(r"graph-load-no-alerts:\n\tpython scripts/graph.py load --no-alerts", text)
    assert re.search(
        r"graph-load-no-reconcile:\n\tpython scripts/graph.py load --no-reconcile",
        text,
    )


def test_graph_load_targets_are_non_destructive_and_scope_limited() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:graph-load|graph-load-limited|graph-load-no-alerts|"
        r"graph-load-no-reconcile):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)
    assert all("train-model" not in command for command in target_blocks)
    assert all("generate-cases" not in command for command in target_blocks)


def test_graph_analytics_targets_use_graph_cli_and_analytics_command() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:graph-analytics|graph-analytics-no-artefacts|"
        r"graph-analytics-connected-components|graph-analytics-greedy-modularity):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/graph.py" in command for command in target_blocks)
    assert all(" analytics" in command for command in target_blocks)


def test_graph_analytics_targets_use_expected_flags() -> None:
    text = makefile_text()

    assert re.search(r"graph-analytics:\n\tpython scripts/graph.py analytics", text)
    assert re.search(
        r"graph-analytics-no-artefacts:\n\tpython scripts/graph.py analytics --no-artefacts",
        text,
    )
    assert re.search(
        r"graph-analytics-connected-components:\n\tpython scripts/graph.py analytics "
        r"--community-algorithm connected_components",
        text,
    )
    assert re.search(
        r"graph-analytics-greedy-modularity:\n\tpython scripts/graph.py analytics "
        r"--community-algorithm greedy_modularity",
        text,
    )


def test_graph_analytics_targets_are_non_destructive_and_do_not_persist_features() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:graph-analytics|graph-analytics-no-artefacts|"
        r"graph-analytics-connected-components|graph-analytics-greedy-modularity):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("db-reset" not in command for command in target_blocks)
    assert all("--persist" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)
    assert all("train-model" not in command for command in target_blocks)
    assert all("generate-cases" not in command for command in target_blocks)


def test_graph_feature_targets_use_graph_cli_and_expected_commands() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:graph-features-persist|graph-features-persist-no-artefacts|"
        r"graph-features-read|graph-features-summary):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("scripts/graph.py" in command for command in target_blocks)
    assert re.search(r"graph-features-persist:\n\tpython scripts/graph.py features-persist", text)
    assert re.search(
        r"graph-features-persist-no-artefacts:\n\tpython scripts/graph.py "
        r"features-persist --no-artefacts",
        text,
    )
    assert re.search(
        r"graph-features-read:\n\tpython scripts/graph.py features-read --latest",
        text,
    )
    assert re.search(
        r"graph-features-summary:\n\tpython scripts/graph.py features-summary",
        text,
    )


def test_graph_feature_targets_are_non_destructive_and_scope_limited() -> None:
    text = makefile_text()
    target_blocks = re.findall(
        r"(?:graph-features-persist|graph-features-persist-no-artefacts|"
        r"graph-features-read|graph-features-summary):\n\t([^\n]+)",
        text,
    )

    assert target_blocks
    assert all("db-reset" not in command for command in target_blocks)
    assert all("run_aml_rules.py" not in command for command in target_blocks)
    assert all("run-rules" not in command for command in target_blocks)
    assert all("train-model" not in command for command in target_blocks)
    assert all("generate-cases" not in command for command in target_blocks)
    assert all("dashboard" not in command for command in target_blocks)


def test_fan_flow_fixture_target_runs_expected_fixture_tests() -> None:
    text = makefile_text()

    assert re.search(r"^test-fan-flow-fixtures:", text, flags=re.MULTILINE)
    for filename in (
        "tests/test_fan_flow_fixture_helpers.py",
        "tests/test_fan_flow_joint_triggers.py",
        "tests/test_fan_flow_rule_separation.py",
        "tests/test_fan_flow_threshold_boundaries.py",
        "tests/test_fan_flow_window_boundaries.py",
        "tests/test_fan_flow_overlapping_windows.py",
        "tests/test_fan_flow_evidence_isolation.py",
        "tests/test_fan_flow_reason_codes.py",
        "tests/test_fan_flow_risk_scores.py",
        "tests/test_fan_flow_deterministic_ids.py",
        "tests/test_fan_flow_counterparty_handling.py",
        "tests/test_fan_flow_mutation_safety.py",
        "tests/test_fan_flow_invalid_inputs.py",
        "tests/test_fan_flow_scenario_alignment.py",
    ):
        assert filename in text


def test_fan_flow_fixture_target_is_offline_and_non_destructive() -> None:
    text = makefile_text()
    match = re.search(
        r"test-fan-flow-fixtures:\n((?:\t[^\n]+(?: \\\n)?)+)",
        text,
    )

    assert match is not None
    command_block = match.group(1)
    assert "docker" not in command_block
    assert "db-reset" not in command_block
    assert "reset_database" not in command_block
    assert "services-up" not in command_block
    assert "run-fan-in-rule" not in command_block
    assert "run-fan-out-rule" not in command_block


def test_movement_dormancy_fixture_target_runs_expected_fixture_tests() -> None:
    text = makefile_text()

    assert re.search(r"^test-movement-dormancy-fixtures:", text, flags=re.MULTILINE)
    for filename in (
        "tests/test_movement_dormancy_fixture_helpers.py",
        "tests/test_movement_dormancy_joint_triggers.py",
        "tests/test_movement_dormancy_rule_separation.py",
        "tests/test_movement_dormancy_rapid_thresholds.py",
        "tests/test_movement_dormancy_dormant_thresholds.py",
        "tests/test_movement_dormancy_window_boundaries.py",
        "tests/test_movement_dormancy_overlapping_windows.py",
        "tests/test_movement_dormancy_evidence_isolation.py",
        "tests/test_movement_dormancy_reason_codes.py",
        "tests/test_movement_dormancy_risk_scores.py",
        "tests/test_movement_dormancy_deterministic_ids.py",
        "tests/test_movement_dormancy_counterparty_handling.py",
        "tests/test_movement_dormancy_mutation_safety.py",
        "tests/test_movement_dormancy_invalid_inputs.py",
        "tests/test_movement_dormancy_scenario_alignment.py",
    ):
        assert filename in text


def test_movement_dormancy_fixture_target_is_offline_and_non_destructive() -> None:
    text = makefile_text()
    match = re.search(
        r"test-movement-dormancy-fixtures:\n((?:\t[^\n]+(?: \\\n)?)+)",
        text,
    )

    assert match is not None
    command_block = match.group(1)
    assert "docker" not in command_block
    assert "db-reset" not in command_block
    assert "reset_database" not in command_block
    assert "services-up" not in command_block
    assert "run-rapid-movement-rule" not in command_block
    assert "run-dormant-reactivation-rule" not in command_block
    assert "--persist" not in command_block


def test_validation_targets_write_artefacts_and_audit_target_writes_audit() -> None:
    text = makefile_text()

    assert re.search(
        r"validate-data:\n\tpython scripts/validate_data.py .*--write-artefacts",
        text,
    )
    assert re.search(r"^validate-data-audit:", text, flags=re.MULTILINE)
    assert re.search(
        r"validate-data-audit:\n\tpython scripts/validate_data.py .*--write-audit",
        text,
    )


def test_demo_targets_use_demo_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(demo-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )

    expected = {
        "demo-plan",
        "demo-plan-with-reset",
        "demo-readiness",
        "demo-run-dry",
        "demo-run",
        "demo-run-with-reset",
        "demo-validate",
        "demo-artefacts",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/demo.py" in target_blocks[target] for target in expected)
    assert " plan" in target_blocks["demo-plan"]
    assert "plan --include-reset" in target_blocks["demo-plan-with-reset"]
    assert " readiness" in target_blocks["demo-readiness"]
    assert "run --dry-run" in target_blocks["demo-run-dry"]
    assert "run --write-artefacts" in target_blocks["demo-run"]
    assert "--include-reset" not in target_blocks["demo-run"]
    assert "run --include-reset --write-artefacts" in target_blocks["demo-run-with-reset"]
    assert " validate" in target_blocks["demo-validate"]
    assert " artefacts" in target_blocks["demo-artefacts"]
    assert all("streamlit run" not in command for command in target_blocks.values())
    assert all("terraform" not in command.lower() for command in target_blocks.values())
    assert all("kubectl" not in command.lower() for command in target_blocks.values())


def test_label_targets_use_labels_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(labels-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )
    expected = {
        "labels-build",
        "labels-build-persist",
        "labels-build-limited",
        "labels-read-case",
        "labels-read-account",
        "labels-summary",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/labels.py" in command for command in target_blocks.values())
    assert target_blocks["labels-build"].endswith(" build")
    assert "--persist" in target_blocks["labels-build-persist"]
    assert "--limit" in target_blocks["labels-build-limited"]
    assert "read case-labels" in target_blocks["labels-read-case"]
    assert "read account-labels" in target_blocks["labels-read-account"]
    assert target_blocks["labels-summary"].endswith(" summary")
    forbidden = (
        "train-score",
        "case-risk-score-persist",
        "lifecycle status",
        "graph-load",
        "db-reset",
    )
    assert all(
        all(pattern not in command for pattern in forbidden) for command in target_blocks.values()
    )


def test_supervised_model_targets_use_models_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(model-supervised-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )
    expected = {
        "model-supervised-train",
        "model-supervised-train-persist",
        "model-supervised-train-limited",
        "model-supervised-read-scores",
        "model-supervised-read-runs",
        "model-supervised-summary",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/models.py" in command for command in target_blocks.values())
    assert "supervised train" in target_blocks["model-supervised-train"]
    assert "--persist" in target_blocks["model-supervised-train-persist"]
    assert "--limit" in target_blocks["model-supervised-train-limited"]
    assert "supervised read-scores" in target_blocks["model-supervised-read-scores"]
    assert "supervised read-runs" in target_blocks["model-supervised-read-runs"]
    assert "supervised summary" in target_blocks["model-supervised-summary"]
    forbidden = ("labels.py", "run-aml-rules", "graph-load", "db-reset")
    assert all(
        all(pattern not in command for pattern in forbidden) for command in target_blocks.values()
    )


def test_model_comparison_targets_use_validation_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(model-comparison-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )
    expected = {
        "model-comparison-run",
        "model-comparison-run-persist",
        "model-comparison-run-limited",
        "model-comparison-read-runs",
        "model-comparison-read-champion",
        "model-comparison-summary",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/validation.py" in command for command in target_blocks.values())
    assert "model-comparison run" in target_blocks["model-comparison-run"]
    assert "--persist" in target_blocks["model-comparison-run-persist"]
    assert "--limit" in target_blocks["model-comparison-run-limited"]
    assert "model-comparison read-runs" in target_blocks["model-comparison-read-runs"]
    assert (
        "model-comparison read-champion --champion-only"
        in target_blocks["model-comparison-read-champion"]
    )
    assert "model-comparison summary" in target_blocks["model-comparison-summary"]
    forbidden = (
        "models.py supervised train",
        "labels.py",
        "run-aml-rules",
        "graph-load",
        "db-reset",
    )
    assert all(
        all(pattern not in command for pattern in forbidden) for command in target_blocks.values()
    )


def test_monitoring_targets_use_validation_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(monitoring-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )
    expected = {
        "monitoring-run",
        "monitoring-run-persist",
        "monitoring-run-limited",
        "monitoring-read-runs",
        "monitoring-read-drift",
        "monitoring-read-volume",
        "monitoring-read-segments",
        "monitoring-read-backtesting",
        "monitoring-summary",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/validation.py" in command for command in target_blocks.values())
    assert "monitoring run" in target_blocks["monitoring-run"]
    assert "--persist" in target_blocks["monitoring-run-persist"]
    assert "--limit" in target_blocks["monitoring-run-limited"]
    assert "monitoring read-runs" in target_blocks["monitoring-read-runs"]
    assert "monitoring read-drift" in target_blocks["monitoring-read-drift"]
    assert "monitoring read-volume" in target_blocks["monitoring-read-volume"]
    assert "monitoring read-segments" in target_blocks["monitoring-read-segments"]
    assert "monitoring read-backtesting" in target_blocks["monitoring-read-backtesting"]
    assert "monitoring summary" in target_blocks["monitoring-summary"]
    forbidden = (
        "models.py supervised train",
        "labels.py",
        "run-aml-rules",
        "graph-load",
        "db-reset",
        "threshold_calibration",
    )
    assert all(
        all(pattern not in command for pattern in forbidden) for command in target_blocks.values()
    )


def test_explainability_targets_use_validation_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(explainability-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )
    expected = {
        "explainability-run",
        "explainability-run-persist",
        "explainability-run-limited",
        "explainability-read-runs",
        "explainability-read-features",
        "explainability-read-decomposition",
        "explainability-read-reasons",
        "explainability-read-model-cards",
        "explainability-summary",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/validation.py" in command for command in target_blocks.values())
    assert "explainability run" in target_blocks["explainability-run"]
    assert "--persist" in target_blocks["explainability-run-persist"]
    assert "--limit" in target_blocks["explainability-run-limited"]
    assert "explainability read-runs" in target_blocks["explainability-read-runs"]
    assert "explainability read-features" in target_blocks["explainability-read-features"]
    assert "explainability read-decomposition" in target_blocks["explainability-read-decomposition"]
    assert "explainability read-reasons" in target_blocks["explainability-read-reasons"]
    assert "explainability read-model-cards" in target_blocks["explainability-read-model-cards"]
    assert "explainability summary" in target_blocks["explainability-summary"]
    forbidden = (
        "models.py supervised train",
        "labels.py",
        "run-aml-rules",
        "graph-load",
        "db-reset",
        "threshold_calibration",
        "openai",
        "llm",
    )
    assert all(
        all(pattern not in command.lower() for pattern in forbidden)
        for command in target_blocks.values()
    )


def test_governance_inventory_targets_use_governance_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(governance-inventory-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )
    expected = {
        "governance-inventory-run",
        "governance-inventory-run-persist",
        "governance-inventory-run-limited",
        "governance-inventory-read-runs",
        "governance-inventory-read-lineage",
        "governance-inventory-read-artefacts",
        "governance-inventory-read-processes",
        "governance-inventory-read-models",
        "governance-inventory-read-validations",
        "governance-inventory-summary",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/governance.py" in command for command in target_blocks.values())
    assert "inventory run" in target_blocks["governance-inventory-run"]
    assert "--persist" in target_blocks["governance-inventory-run-persist"]
    assert "--limit" in target_blocks["governance-inventory-run-limited"]
    assert "inventory read-runs" in target_blocks["governance-inventory-read-runs"]
    assert "inventory read-lineage" in target_blocks["governance-inventory-read-lineage"]
    assert "inventory read-artefacts" in target_blocks["governance-inventory-read-artefacts"]
    assert "inventory read-processes" in target_blocks["governance-inventory-read-processes"]
    assert "inventory read-models" in target_blocks["governance-inventory-read-models"]
    assert "inventory read-validations" in target_blocks["governance-inventory-read-validations"]
    assert "inventory summary" in target_blocks["governance-inventory-summary"]
    forbidden = (
        "models.py supervised train",
        "labels.py",
        "run-aml-rules",
        "graph-load",
        "db-reset",
        "threshold_calibration",
        "openai",
        "curl",
    )
    assert all(
        all(pattern not in command.lower() for pattern in forbidden)
        for command in target_blocks.values()
    )


def test_security_targets_use_security_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(security-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )
    expected = {
        "security-controls-run",
        "security-controls-run-persist",
        "security-controls-run-limited",
        "security-controls-read-runs",
        "security-controls-read-fields",
        "security-controls-read-permissions",
        "security-controls-read-secrets",
        "security-controls-read-audit-integrity",
        "security-controls-summary",
        "security-mask-preview",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/security.py" in command for command in target_blocks.values())
    assert "controls run" in target_blocks["security-controls-run"]
    assert "--persist" in target_blocks["security-controls-run-persist"]
    assert "--limit" in target_blocks["security-controls-run-limited"]
    assert "controls read-runs" in target_blocks["security-controls-read-runs"]
    assert "controls read-fields" in target_blocks["security-controls-read-fields"]
    assert "controls read-permissions" in target_blocks["security-controls-read-permissions"]
    assert "controls read-secrets" in target_blocks["security-controls-read-secrets"]
    assert (
        "controls read-audit-integrity" in target_blocks["security-controls-read-audit-integrity"]
    )
    assert "controls summary" in target_blocks["security-controls-summary"]
    assert "mask-preview" in target_blocks["security-mask-preview"]
    forbidden = (
        "models.py supervised train",
        "labels.py",
        "run-aml-rules",
        "graph-load",
        "db-reset",
        "threshold_calibration",
        "openai",
        "curl",
    )
    assert all(
        all(pattern not in command.lower() for pattern in forbidden)
        for command in target_blocks.values()
    )


def test_release_targets_use_release_cli_and_are_scoped() -> None:
    text = makefile_text()
    target_blocks = dict(
        re.findall(
            r"^(release-readiness-[A-Za-z0-9-]+):\n\t([^\n]+)",
            text,
            flags=re.MULTILINE,
        )
    )
    expected = {
        "release-readiness-run",
        "release-readiness-run-persist",
        "release-readiness-no-artefacts",
        "release-readiness-read-runs",
        "release-readiness-read-checks",
        "release-readiness-read-artefacts",
        "release-readiness-read-evidence",
        "release-readiness-read-portfolio",
        "release-readiness-summary",
    }
    assert expected <= set(target_blocks)
    assert all("scripts/release.py" in command for command in target_blocks.values())
    assert "readiness run --local-only" in target_blocks["release-readiness-run"]
    assert "--persist" in target_blocks["release-readiness-run-persist"]
    assert "--no-artefacts" in target_blocks["release-readiness-no-artefacts"]
    assert "readiness read-runs" in target_blocks["release-readiness-read-runs"]
    assert "readiness read-checks" in target_blocks["release-readiness-read-checks"]
    assert "readiness read-artefacts" in target_blocks["release-readiness-read-artefacts"]
    assert "readiness read-evidence" in target_blocks["release-readiness-read-evidence"]
    assert "readiness read-portfolio" in target_blocks["release-readiness-read-portfolio"]
    assert "readiness summary" in target_blocks["release-readiness-summary"]
    forbidden = (
        "models.py supervised train",
        "labels.py",
        "run-aml-rules",
        "graph-load",
        "db-reset",
        "threshold_calibration",
        "openai",
        "curl",
    )
    assert all(
        all(pattern not in command.lower() for pattern in forbidden)
        for command in target_blocks.values()
    )

