"""Configuration models for security controls."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import yaml

from graph_aml.security.exceptions import SecurityConfigurationError


def _default_masking_strategies() -> dict[str, str]:
    return {
        "customer_id": "hash",
        "account_id": "hash",
        "counterparty_id": "hash",
        "transaction_id": "preserve_last_4",
        "case_id": "preserve_last_4",
        "alert_id": "preserve_last_4",
        "email": "redact",
        "phone": "redact",
        "address": "redact",
        "device_id": "hash",
        "ip_address": "redact",
    }


def _default_roles() -> dict[str, tuple[str, ...]]:
    return {
        "viewer": ("read_dashboard", "export_sanitised", "read_validation_reports"),
        "analyst": (
            "read_dashboard",
            "export_sanitised",
            "read_validation_reports",
            "case_comment",
            "case_assign",
            "case_status_change",
        ),
        "senior_analyst": (
            "read_dashboard",
            "export_sanitised",
            "export_sensitive",
            "read_validation_reports",
            "case_comment",
            "case_assign",
            "case_status_change",
            "case_close",
            "case_archive",
        ),
        "governance_reviewer": (
            "read_dashboard",
            "export_sanitised",
            "read_validation_reports",
            "read_audit_log",
            "read_governance_inventory",
        ),
        "admin": ("*",),
    }


def _default_secret_patterns() -> tuple[SecretPatternConfig, ...]:
    return (
        SecretPatternConfig(
            "generic_api_key",
            r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
        ),
        SecretPatternConfig("postgres_url", r"(?i)postgres(ql)?://[^\s]+"),
        SecretPatternConfig("neo4j_password", r"(?i)neo4j.*password\s*[:=]\s*['\"]?[^\s'\"]+"),
    )


@dataclass(frozen=True)
class SensitiveFieldConfig:
    default_classification: str = "internal"
    classifications: tuple[str, ...] = ("public", "internal", "confidential", "restricted")
    restricted_patterns: tuple[str, ...] = (
        "customer_name",
        "full_name",
        "email",
        "phone",
        "address",
        "date_of_birth",
        "national_id",
        "tax_id",
        "ip_address",
        "device_id",
        "account_number",
    )
    confidential_patterns: tuple[str, ...] = (
        "customer_id",
        "account_id",
        "counterparty_id",
        "transaction_id",
        "case_id",
        "alert_id",
    )


@dataclass(frozen=True)
class MaskingConfig:
    enabled: bool = True
    default_strategy: str = "hash"
    salt_env_var: str = "AML_MASKING_SALT"
    fallback_salt: str = "local_dev_salt"
    strategies: dict[str, str] = field(default_factory=_default_masking_strategies)
    null_token: str | None = None
    redaction_token: str = "[REDACTED]"


@dataclass(frozen=True)
class PermissionConfig:
    enabled: bool = True
    default_role: str = "analyst"
    roles: dict[str, tuple[str, ...]] = field(default_factory=_default_roles)
    protected_actions: tuple[str, ...] = (
        "case_close",
        "case_archive",
        "export_sensitive",
        "read_audit_log",
        "read_governance_inventory",
    )


@dataclass(frozen=True)
class ExportControlConfig:
    enabled: bool = True
    default_export_mode: str = "sanitised"
    allow_sensitive_exports: bool = False
    require_role_for_sensitive_export: str = "senior_analyst"
    max_export_rows: int = 10000
    blocked_columns: tuple[str, ...] = (
        "raw_payload",
        "metadata_raw",
        "secret",
        "password",
        "token",
        "api_key",
    )


@dataclass(frozen=True)
class SecretPatternConfig:
    name: str
    regex: str


@dataclass(frozen=True)
class SecretsScanConfig:
    enabled: bool = True
    root_dirs: tuple[str, ...] = ("config", "scripts", "src", "docs")
    allowed_extensions: tuple[str, ...] = (
        ".py",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".env",
        ".example",
    )
    max_file_size_mb: int = 5
    secret_patterns: tuple[SecretPatternConfig, ...] = field(
        default_factory=_default_secret_patterns
    )
    allowlist_patterns: tuple[str, ...] = (".env.example", "fallback_salt", "local_dev")


@dataclass(frozen=True)
class AuditIntegrityConfig:
    enabled: bool = True
    required_columns: tuple[str, ...] = (
        "event_type",
        "component",
        "action",
        "status",
        "created_at",
    )
    duplicate_check_columns: tuple[str, ...] = (
        "event_type",
        "component",
        "action",
        "run_id",
        "created_at",
    )
    require_success_or_failure_status: bool = True


@dataclass(frozen=True)
class SecurityPersistenceConfig:
    write_database: bool = True
    write_artefacts: bool = True
    write_audit: bool = True
    artefact_output_dir: str = "reports/model_validation"


@dataclass(frozen=True)
class SecurityControlConfig:
    security_name: str = "aml_security_controls"
    security_version: str = "security_controls_v1"
    sensitive_fields: SensitiveFieldConfig = field(default_factory=SensitiveFieldConfig)
    masking: MaskingConfig = field(default_factory=MaskingConfig)
    permissions: PermissionConfig = field(default_factory=PermissionConfig)
    export_controls: ExportControlConfig = field(default_factory=ExportControlConfig)
    secrets_scan: SecretsScanConfig = field(default_factory=SecretsScanConfig)
    audit_integrity: AuditIntegrityConfig = field(default_factory=AuditIntegrityConfig)
    persistence: SecurityPersistenceConfig = field(default_factory=SecurityPersistenceConfig)


def _bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise SecurityConfigurationError(f"{name} must be boolean")
    return value


def _int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SecurityConfigurationError(f"{name} must be an integer")
    return int(value)


def _tuple_strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise SecurityConfigurationError(f"{name} must be a list")
    values = tuple(str(item).strip() for item in value)
    if not values or any(not item for item in values):
        raise SecurityConfigurationError(f"{name} must contain non-empty strings")
    return values


def _normalise_roles(raw: object) -> dict[str, tuple[str, ...]]:
    if raw is None:
        return _default_roles()
    if not isinstance(raw, dict):
        raise SecurityConfigurationError("permissions.roles must be a mapping")
    roles: dict[str, tuple[str, ...]] = {}
    for role, payload in raw.items():
        role_name = str(role).strip()
        if not role_name:
            raise SecurityConfigurationError("role names must be non-empty")
        if isinstance(payload, dict):
            actions = payload.get("allowed_actions", ())
        else:
            actions = payload
        roles[role_name] = _tuple_strings(actions, f"permissions.roles.{role_name}")
    return roles


def _normalise_secret_patterns(raw: object) -> tuple[SecretPatternConfig, ...]:
    if raw is None:
        return _default_secret_patterns()
    if not isinstance(raw, list | tuple):
        raise SecurityConfigurationError("secret_patterns must be a list")
    patterns: list[SecretPatternConfig] = []
    for item in raw:
        if isinstance(item, SecretPatternConfig):
            pattern = item
        elif isinstance(item, dict):
            pattern = SecretPatternConfig(
                str(item.get("name", "")).strip(), str(item.get("regex", ""))
            )
        else:
            raise SecurityConfigurationError("secret pattern entries must be mappings")
        if not pattern.name or not pattern.regex:
            raise SecurityConfigurationError("secret pattern name and regex must be non-empty")
        try:
            re.compile(pattern.regex)
        except re.error as exc:
            raise SecurityConfigurationError(
                f"invalid secret pattern regex {pattern.name}"
            ) from exc
        patterns.append(pattern)
    return tuple(patterns)


def validate_security_control_config(config: SecurityControlConfig) -> None:
    """Validate security control configuration without service access."""

    if not config.security_name.strip():
        raise SecurityConfigurationError("security_name must be non-empty")
    if not config.security_version.strip():
        raise SecurityConfigurationError("security_version must be non-empty")
    classifications = config.sensitive_fields.classifications
    if len(classifications) != len(set(classifications)) or any(
        not item for item in classifications
    ):
        raise SecurityConfigurationError("classifications must be unique non-empty strings")
    if config.sensitive_fields.default_classification not in classifications:
        raise SecurityConfigurationError("default classification must be configured")
    for name, values in (
        ("restricted_patterns", config.sensitive_fields.restricted_patterns),
        ("confidential_patterns", config.sensitive_fields.confidential_patterns),
    ):
        _tuple_strings(values, f"sensitive_fields.{name}")
    allowed_strategies = {"hash", "redact", "preserve_last_4", "none"}
    if config.masking.default_strategy not in allowed_strategies:
        raise SecurityConfigurationError("default masking strategy is invalid")
    if not config.masking.salt_env_var.strip() or not config.masking.fallback_salt.strip():
        raise SecurityConfigurationError("masking salts must be non-empty")
    for column, strategy in config.masking.strategies.items():
        if not str(column).strip() or strategy not in allowed_strategies:
            raise SecurityConfigurationError("masking strategies must use supported strategy names")
    if not config.permissions.roles:
        raise SecurityConfigurationError("permission roles must be configured")
    if config.permissions.default_role not in config.permissions.roles:
        raise SecurityConfigurationError("default role must be defined")
    _tuple_strings(config.permissions.protected_actions, "permissions.protected_actions")
    for role, actions in config.permissions.roles.items():
        if not str(role).strip():
            raise SecurityConfigurationError("role names must be non-empty")
        _tuple_strings(actions, f"permissions.roles.{role}")
    if config.export_controls.default_export_mode not in {"sanitised", "sensitive"}:
        raise SecurityConfigurationError("default export mode must be sanitised or sensitive")
    if config.export_controls.max_export_rows <= 0:
        raise SecurityConfigurationError("max_export_rows must be positive")
    _tuple_strings(config.export_controls.blocked_columns, "export_controls.blocked_columns")
    _tuple_strings(config.secrets_scan.root_dirs, "secrets_scan.root_dirs")
    extensions = config.secrets_scan.allowed_extensions
    if len(extensions) != len(set(extensions)) or any(
        not ext.startswith(".") for ext in extensions
    ):
        raise SecurityConfigurationError("allowed extensions must start with '.' and be unique")
    if config.secrets_scan.max_file_size_mb <= 0:
        raise SecurityConfigurationError("max_file_size_mb must be positive")
    _normalise_secret_patterns(config.secrets_scan.secret_patterns)
    _tuple_strings(config.audit_integrity.required_columns, "audit_integrity.required_columns")
    _tuple_strings(
        config.audit_integrity.duplicate_check_columns, "audit_integrity.duplicate_check_columns"
    )
    for obj_name, obj in (
        ("masking", config.masking),
        ("permissions", config.permissions),
        ("export_controls", config.export_controls),
        ("secrets_scan", config.secrets_scan),
        ("audit_integrity", config.audit_integrity),
        ("persistence", config.persistence),
    ):
        for field_name, value in vars(obj).items():
            if field_name.startswith("include_") or field_name in {
                "enabled",
                "allow_sensitive_exports",
                "require_success_or_failure_status",
                "write_database",
                "write_artefacts",
                "write_audit",
            }:
                _bool(value, f"{obj_name}.{field_name}")
    if not config.persistence.artefact_output_dir.strip():
        raise SecurityConfigurationError("artefact_output_dir must be non-empty")


def security_control_config_from_mapping(
    payload: dict[str, object] | None,
) -> SecurityControlConfig:
    """Build security control configuration from a mapping."""

    data = payload or {}
    if "security_controls" in data and isinstance(data["security_controls"], dict):
        data = cast("dict[str, object]", data["security_controls"])
    default = SecurityControlConfig()
    sensitive_raw = cast("dict[str, object]", data.get("sensitive_fields", {}) or {})
    masking_raw = cast("dict[str, object]", data.get("masking", {}) or {})
    permission_raw = cast("dict[str, object]", data.get("permissions", {}) or {})
    export_raw = cast("dict[str, object]", data.get("export_controls", {}) or {})
    scan_raw = cast("dict[str, object]", data.get("secrets_scan", {}) or {})
    audit_raw = cast("dict[str, object]", data.get("audit_integrity", {}) or {})
    persistence_raw = cast("dict[str, object]", data.get("persistence", {}) or {})
    config = SecurityControlConfig(
        security_name=str(data.get("security_name", default.security_name)),
        security_version=str(data.get("security_version", default.security_version)),
        sensitive_fields=SensitiveFieldConfig(
            default_classification=str(
                sensitive_raw.get(
                    "default_classification",
                    default.sensitive_fields.default_classification,
                )
            ),
            classifications=_tuple_strings(
                sensitive_raw.get("classifications", default.sensitive_fields.classifications),
                "sensitive_fields.classifications",
            ),
            restricted_patterns=_tuple_strings(
                sensitive_raw.get(
                    "restricted_patterns", default.sensitive_fields.restricted_patterns
                ),
                "sensitive_fields.restricted_patterns",
            ),
            confidential_patterns=_tuple_strings(
                sensitive_raw.get(
                    "confidential_patterns",
                    default.sensitive_fields.confidential_patterns,
                ),
                "sensitive_fields.confidential_patterns",
            ),
        ),
        masking=MaskingConfig(
            enabled=_bool(masking_raw.get("enabled", default.masking.enabled), "masking.enabled"),
            default_strategy=str(
                masking_raw.get("default_strategy", default.masking.default_strategy)
            ),
            salt_env_var=str(masking_raw.get("salt_env_var", default.masking.salt_env_var)),
            fallback_salt=str(masking_raw.get("fallback_salt", default.masking.fallback_salt)),
            strategies={
                str(key): str(value)
                for key, value in cast(
                    dict[str, object],
                    masking_raw.get("strategies", default.masking.strategies),
                ).items()
            },
            null_token=(
                None
                if masking_raw.get("null_token", default.masking.null_token) is None
                else str(masking_raw.get("null_token"))
            ),
            redaction_token=str(
                masking_raw.get("redaction_token", default.masking.redaction_token)
            ),
        ),
        permissions=PermissionConfig(
            enabled=_bool(
                permission_raw.get("enabled", default.permissions.enabled), "permissions.enabled"
            ),
            default_role=str(permission_raw.get("default_role", default.permissions.default_role)),
            roles=_normalise_roles(permission_raw.get("roles", default.permissions.roles)),
            protected_actions=_tuple_strings(
                permission_raw.get("protected_actions", default.permissions.protected_actions),
                "permissions.protected_actions",
            ),
        ),
        export_controls=ExportControlConfig(
            enabled=_bool(
                export_raw.get("enabled", default.export_controls.enabled),
                "export_controls.enabled",
            ),
            default_export_mode=str(
                export_raw.get("default_export_mode", default.export_controls.default_export_mode)
            ),
            allow_sensitive_exports=_bool(
                export_raw.get(
                    "allow_sensitive_exports",
                    default.export_controls.allow_sensitive_exports,
                ),
                "export_controls.allow_sensitive_exports",
            ),
            require_role_for_sensitive_export=str(
                export_raw.get(
                    "require_role_for_sensitive_export",
                    default.export_controls.require_role_for_sensitive_export,
                )
            ),
            max_export_rows=_int(
                export_raw.get("max_export_rows", default.export_controls.max_export_rows),
                "export_controls.max_export_rows",
            ),
            blocked_columns=_tuple_strings(
                export_raw.get("blocked_columns", default.export_controls.blocked_columns),
                "export_controls.blocked_columns",
            ),
        ),
        secrets_scan=SecretsScanConfig(
            enabled=_bool(
                scan_raw.get("enabled", default.secrets_scan.enabled), "secrets_scan.enabled"
            ),
            root_dirs=_tuple_strings(
                scan_raw.get("root_dirs", default.secrets_scan.root_dirs),
                "secrets_scan.root_dirs",
            ),
            allowed_extensions=_tuple_strings(
                scan_raw.get("allowed_extensions", default.secrets_scan.allowed_extensions),
                "secrets_scan.allowed_extensions",
            ),
            max_file_size_mb=_int(
                scan_raw.get("max_file_size_mb", default.secrets_scan.max_file_size_mb),
                "secrets_scan.max_file_size_mb",
            ),
            secret_patterns=_normalise_secret_patterns(
                scan_raw.get("secret_patterns", default.secrets_scan.secret_patterns)
            ),
            allowlist_patterns=_tuple_strings(
                scan_raw.get("allowlist_patterns", default.secrets_scan.allowlist_patterns),
                "secrets_scan.allowlist_patterns",
            ),
        ),
        audit_integrity=AuditIntegrityConfig(
            enabled=_bool(
                audit_raw.get("enabled", default.audit_integrity.enabled),
                "audit_integrity.enabled",
            ),
            required_columns=_tuple_strings(
                audit_raw.get("required_columns", default.audit_integrity.required_columns),
                "audit_integrity.required_columns",
            ),
            duplicate_check_columns=_tuple_strings(
                audit_raw.get(
                    "duplicate_check_columns",
                    default.audit_integrity.duplicate_check_columns,
                ),
                "audit_integrity.duplicate_check_columns",
            ),
            require_success_or_failure_status=_bool(
                audit_raw.get(
                    "require_success_or_failure_status",
                    default.audit_integrity.require_success_or_failure_status,
                ),
                "audit_integrity.require_success_or_failure_status",
            ),
        ),
        persistence=SecurityPersistenceConfig(
            write_database=_bool(
                persistence_raw.get("write_database", default.persistence.write_database),
                "persistence.write_database",
            ),
            write_artefacts=_bool(
                persistence_raw.get("write_artefacts", default.persistence.write_artefacts),
                "persistence.write_artefacts",
            ),
            write_audit=_bool(
                persistence_raw.get("write_audit", default.persistence.write_audit),
                "persistence.write_audit",
            ),
            artefact_output_dir=str(
                persistence_raw.get("artefact_output_dir", default.persistence.artefact_output_dir)
            ),
        ),
    )
    validate_security_control_config(config)
    return config


def load_security_control_config(
    config_path: Path | str = "config/security.yaml",
) -> SecurityControlConfig:
    """Load security control configuration from YAML."""

    path = Path(config_path)
    if not path.exists():
        return SecurityControlConfig()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise SecurityConfigurationError("security config YAML must be a mapping")
    return security_control_config_from_mapping(cast("dict[str, object]", payload))
