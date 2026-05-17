"""Tests for case lifecycle configuration."""

import pytest
import yaml

from graph_aml.cases import (
    CaseLifecycleAnalystConfig,
    CaseLifecycleConfig,
    CaseLifecycleConfigurationError,
    case_lifecycle_config_from_mapping,
    load_case_lifecycle_config,
    validate_case_lifecycle_config,
)


def test_default_lifecycle_config_is_valid() -> None:
    validate_case_lifecycle_config(CaseLifecycleConfig())


def test_invalid_lifecycle_version_raises() -> None:
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(lifecycle_version="")


def test_invalid_status_sets_raise() -> None:
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(statuses=())
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(statuses=("New", "New"))
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(terminal_statuses=("Missing",))


def test_invalid_transitions_raise() -> None:
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(allowed_transitions={"Missing": ("New",)})
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(allowed_transitions={"New": ("Missing",)})


def test_invalid_decision_types_and_analyst_defaults_raise() -> None:
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(decision_types=())
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(decision_types=("comment", "comment"))
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(analyst=CaseLifecycleAnalystConfig(default_analyst_id=""))
    with pytest.raises(CaseLifecycleConfigurationError):
        CaseLifecycleConfig(analyst=CaseLifecycleAnalystConfig(default_queue=""))


def test_config_from_mapping_and_yaml(tmp_path) -> None:
    payload = {
        "lifecycle_version": "v2",
        "statuses": ["New", "Closed suspicious"],
        "terminal_statuses": ["Closed suspicious"],
        "allowed_transitions": {"New": ["Closed suspicious"], "Closed suspicious": []},
        "decision_types": ["status_change", "close_suspicious", "comment"],
        "analyst": {
            "default_analyst_id": "analyst",
            "default_queue": "Queue",
            "require_decision_reason": True,
            "require_comment_for_closure": True,
        },
        "artefact_output_dir": "reports",
    }
    config = case_lifecycle_config_from_mapping(payload)
    assert config.lifecycle_version == "v2"

    path = tmp_path / "scoring.yaml"
    path.write_text(yaml.safe_dump({"case_lifecycle": payload}), encoding="utf-8")
    assert load_case_lifecycle_config(path).lifecycle_version == "v2"
