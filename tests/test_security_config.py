"""Tests for security control configuration."""

import pytest

from graph_aml.security import (
    ExportControlConfig,
    MaskingConfig,
    PermissionConfig,
    SecretPatternConfig,
    SecretsScanConfig,
    SecurityConfigurationError,
    SecurityControlConfig,
    SensitiveFieldConfig,
    load_security_control_config,
    security_control_config_from_mapping,
    validate_security_control_config,
)


def test_default_security_control_config_is_valid() -> None:
    validate_security_control_config(SecurityControlConfig())


def test_invalid_security_names_raise() -> None:
    with pytest.raises(SecurityConfigurationError):
        validate_security_control_config(SecurityControlConfig(security_name=""))
    with pytest.raises(SecurityConfigurationError):
        validate_security_control_config(SecurityControlConfig(security_version=""))


def test_invalid_classifications_raise() -> None:
    with pytest.raises(SecurityConfigurationError):
        validate_security_control_config(
            SecurityControlConfig(
                sensitive_fields=SensitiveFieldConfig(
                    default_classification="missing",
                    classifications=("public",),
                )
            )
        )


def test_invalid_masking_and_permissions_raise() -> None:
    with pytest.raises(SecurityConfigurationError):
        validate_security_control_config(
            SecurityControlConfig(masking=MaskingConfig(default_strategy="bad"))
        )
    with pytest.raises(SecurityConfigurationError):
        validate_security_control_config(
            SecurityControlConfig(permissions=PermissionConfig(default_role="missing"))
        )


def test_invalid_export_and_scan_config_raise() -> None:
    with pytest.raises(SecurityConfigurationError):
        validate_security_control_config(
            SecurityControlConfig(export_controls=ExportControlConfig(max_export_rows=0))
        )
    with pytest.raises(SecurityConfigurationError):
        validate_security_control_config(
            SecurityControlConfig(
                secrets_scan=SecretsScanConfig(secret_patterns=(SecretPatternConfig("bad", "["),))
            )
        )


def test_config_can_be_built_from_mapping_and_yaml(tmp_path) -> None:
    config = security_control_config_from_mapping(
        {"security_controls": {"security_version": "security_controls_test"}}
    )
    assert config.security_version == "security_controls_test"
    path = tmp_path / "security.yaml"
    path.write_text(
        "security_controls:\n  security_name: aml_security_controls\n  security_version: test_v1\n",
        encoding="utf-8",
    )
    assert load_security_control_config(path).security_version == "test_v1"
