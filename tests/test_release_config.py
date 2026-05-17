"""Tests for release readiness configuration."""

import pytest

from graph_aml.release import (
    ReleaseArtefactConfig,
    ReleaseConfigurationError,
    ReleaseReadinessConfig,
    ReleaseRepositoryConfig,
    load_release_readiness_config,
    release_readiness_config_from_mapping,
    validate_release_readiness_config,
)


def test_default_release_readiness_config_is_valid() -> None:
    validate_release_readiness_config(ReleaseReadinessConfig())


def test_invalid_release_names_raise() -> None:
    with pytest.raises(ReleaseConfigurationError):
        validate_release_readiness_config(ReleaseReadinessConfig(release_name=""))
    with pytest.raises(ReleaseConfigurationError):
        validate_release_readiness_config(ReleaseReadinessConfig(release_version=""))


def test_invalid_repository_and_artefact_config_raise() -> None:
    with pytest.raises(ReleaseConfigurationError):
        validate_release_readiness_config(
            ReleaseReadinessConfig(repository=ReleaseRepositoryConfig(required_files=("",)))
        )
    with pytest.raises(ReleaseConfigurationError):
        validate_release_readiness_config(
            ReleaseReadinessConfig(artefacts=ReleaseArtefactConfig(allowed_extensions=("md",)))
        )


def test_config_can_be_built_from_mapping_and_yaml(tmp_path) -> None:
    config = release_readiness_config_from_mapping(
        {"release_readiness": {"release_version": "portfolio_release_test"}}
    )
    assert config.release_version == "portfolio_release_test"
    path = tmp_path / "release.yaml"
    path.write_text(
        "release_readiness:\n  release_name: aml_portfolio_release\n"
        "  release_version: test_v1\n",
        encoding="utf-8",
    )
    assert load_release_readiness_config(path).release_version == "test_v1"
