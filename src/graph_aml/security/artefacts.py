"""Local artefact writers for security control outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.security.exceptions import SecurityPersistenceError
from graph_aml.security.summary import security_control_result_to_dict
from graph_aml.security.validation import SecurityControlResult


def _ensure_parent(output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(frame: pd.DataFrame, output_path: Path | str) -> Path:
    try:
        path = _ensure_parent(output_path)
        frame.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise SecurityPersistenceError(f"failed to write CSV artefact: {exc}") from exc


def write_sensitive_field_inventory_csv(
    fields: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/sensitive_field_inventory.csv",
) -> Path:
    return _write_csv(fields, output_path)


def write_permission_matrix_csv(
    matrix: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/security_permission_matrix.csv",
) -> Path:
    return _write_csv(matrix, output_path)


def write_secrets_scan_findings_csv(
    findings: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/secrets_scan_findings.csv",
) -> Path:
    return _write_csv(findings, output_path)


def write_audit_integrity_checks_csv(
    checks: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/audit_integrity_checks.csv",
) -> Path:
    return _write_csv(checks, output_path)


def write_security_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/security_control_summary.json",
) -> Path:
    try:
        path = _ensure_parent(output_path)
        path.write_text(
            json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        return path
    except Exception as exc:
        raise SecurityPersistenceError(f"failed to write summary artefact: {exc}") from exc


def write_security_control_report_md(
    result: SecurityControlResult,
    output_path: Path | str = "reports/model_validation/security_control_report.md",
) -> Path:
    try:
        path = _ensure_parent(output_path)
        report = [
            "# Security Control Report",
            "",
            f"- Security run: `{result.security_run_id}`",
            (
                "- Sensitive fields: "
                f"{result.summary.get('sensitive_field_count', len(result.sensitive_fields))}"
            ),
            f"- Restricted fields: {result.summary.get('restricted_field_count', 0)}",
            f"- Confidential fields: {result.summary.get('confidential_field_count', 0)}",
            (
                "- Unallowed secret findings: "
                f"{result.summary.get('unallowed_secret_finding_count', 0)}"
            ),
            f"- Audit integrity issues: {result.summary.get('audit_integrity_issue_count', 0)}",
            "",
            "## Controls",
            "",
            (
                "The security layer classifies sensitive columns, recommends deterministic "
                "masking strategies, applies role-based permissions, blocks sensitive exports "
                "by default, scans local project files for secret-like strings with redacted "
                "previews, and checks audit event integrity."
            ),
            "",
            "## Local Limitations",
            "",
            (
                "This local-first implementation does not provide production authentication, "
                "database encryption, external identity-provider integration, or cloud secrets "
                "management."
            ),
            "",
            "## Production Hardening Notes",
            "",
            (
                "Use managed identity, secrets management, encryption at rest, network "
                "controls, row-level permissions, and independent audit log retention before "
                "production deployment."
            ),
        ]
        path.write_text("\n".join(report), encoding="utf-8")
        return path
    except Exception as exc:
        raise SecurityPersistenceError(f"failed to write Markdown artefact: {exc}") from exc


def generate_security_control_artefacts(
    result: SecurityControlResult,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write all security control artefacts."""

    root = Path(output_dir)
    payload = security_control_result_to_dict(result)
    return {
        "sensitive_fields": write_sensitive_field_inventory_csv(
            result.sensitive_fields,
            root / "sensitive_field_inventory.csv",
        ),
        "permission_matrix": write_permission_matrix_csv(
            result.permission_matrix,
            root / "security_permission_matrix.csv",
        ),
        "secrets_scan": write_secrets_scan_findings_csv(
            result.secrets_scan,
            root / "secrets_scan_findings.csv",
        ),
        "audit_integrity": write_audit_integrity_checks_csv(
            result.audit_integrity,
            root / "audit_integrity_checks.csv",
        ),
        "summary": write_security_summary_json(payload, root / "security_control_summary.json"),
        "report": write_security_control_report_md(result, root / "security_control_report.md"),
    }
