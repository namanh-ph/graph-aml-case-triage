"""Tests for security summaries and artefact writers."""

import json

import pandas as pd

from graph_aml.security import (
    SecurityControlResult,
    generate_security_control_artefacts,
    security_control_result_to_dict,
    summarise_audit_integrity,
    summarise_permission_matrix,
    summarise_secrets_scan,
    summarise_sensitive_fields,
    write_audit_integrity_checks_csv,
    write_permission_matrix_csv,
    write_secrets_scan_findings_csv,
    write_security_control_report_md,
    write_security_summary_json,
    write_sensitive_field_inventory_csv,
)


def _result() -> SecurityControlResult:
    fields = pd.DataFrame([{"classification": "restricted", "schema_name": "aml"}])
    matrix = pd.DataFrame([{"role": "viewer", "allowed": True}])
    secrets = pd.DataFrame([{"pattern_name": "token", "allowed": False}])
    audit = pd.DataFrame([{"status": "fail", "issue_count": 1}])
    return SecurityControlResult(
        "run",
        fields,
        matrix,
        secrets,
        audit,
        {"security_run_id": "run", "sensitive_field_count": 1},
        {},
    )


def test_security_summaries_are_json_serialisable() -> None:
    result = _result()
    assert (
        summarise_sensitive_fields(result.sensitive_fields)["classification_counts"]["restricted"]
        == 1
    )
    assert summarise_permission_matrix(result.permission_matrix)["allowed_action_count"] == 1
    assert summarise_secrets_scan(result.secrets_scan)["unallowed_finding_count"] == 1
    assert summarise_audit_integrity(result.audit_integrity)["issue_count"] == 1
    json.dumps(security_control_result_to_dict(result), default=str)


def test_security_artefact_writers(tmp_path) -> None:
    result = _result()
    assert write_sensitive_field_inventory_csv(
        result.sensitive_fields, tmp_path / "fields.csv"
    ).exists()
    assert write_permission_matrix_csv(result.permission_matrix, tmp_path / "perm.csv").exists()
    assert write_secrets_scan_findings_csv(result.secrets_scan, tmp_path / "secrets.csv").exists()
    assert write_audit_integrity_checks_csv(result.audit_integrity, tmp_path / "audit.csv").exists()
    summary = write_security_summary_json({"a": 1}, tmp_path / "summary.json")
    assert json.loads(summary.read_text(encoding="utf-8")) == {"a": 1}
    assert "# Security Control Report" in write_security_control_report_md(
        result, tmp_path / "r.md"
    ).read_text(encoding="utf-8")
    paths = generate_security_control_artefacts(result, tmp_path)
    assert all(path.exists() for path in paths.values())
