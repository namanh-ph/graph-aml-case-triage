"""Configuration for AML case lifecycle actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import yaml

from graph_aml.cases.exceptions import CaseLifecycleConfigurationError


@dataclass(frozen=True)
class CaseLifecycleAnalystConfig:
    default_analyst_id: str = "local_analyst"
    default_queue: str = "AML Review"
    require_decision_reason: bool = True
    require_comment_for_closure: bool = True


@dataclass(frozen=True)
class CaseLifecycleConfig:
    lifecycle_version: str = "case_lifecycle_v1"
    statuses: tuple[str, ...] = (
        "New",
        "In review",
        "Escalated",
        "Information requested",
        "Closed false positive",
        "Closed suspicious",
        "Archived",
    )
    terminal_statuses: tuple[str, ...] = (
        "Closed false positive",
        "Closed suspicious",
        "Archived",
    )
    allowed_transitions: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "New": (
                "In review",
                "Escalated",
                "Information requested",
                "Closed false positive",
                "Closed suspicious",
                "Archived",
            ),
            "In review": (
                "Escalated",
                "Information requested",
                "Closed false positive",
                "Closed suspicious",
                "Archived",
            ),
            "Escalated": (
                "In review",
                "Information requested",
                "Closed false positive",
                "Closed suspicious",
                "Archived",
            ),
            "Information requested": (
                "In review",
                "Escalated",
                "Closed false positive",
                "Closed suspicious",
                "Archived",
            ),
            "Closed false positive": ("Archived",),
            "Closed suspicious": ("Archived",),
            "Archived": (),
        }
    )
    decision_types: tuple[str, ...] = (
        "assign",
        "status_change",
        "comment",
        "escalate",
        "request_information",
        "close_false_positive",
        "close_suspicious",
        "archive",
        "reopen",
    )
    analyst: CaseLifecycleAnalystConfig = field(default_factory=CaseLifecycleAnalystConfig)
    artefact_output_dir: str = "reports/model_validation"

    def __post_init__(self) -> None:
        validate_case_lifecycle_config(self)


def _as_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def _as_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise CaseLifecycleConfigurationError("analyst requirement flags must be boolean")


def validate_case_lifecycle_config(config: CaseLifecycleConfig) -> None:
    if not isinstance(config, CaseLifecycleConfig):
        raise CaseLifecycleConfigurationError("config must be CaseLifecycleConfig")
    if not config.lifecycle_version.strip():
        raise CaseLifecycleConfigurationError("lifecycle_version must be non-empty")
    if not config.statuses:
        raise CaseLifecycleConfigurationError("statuses must be non-empty")
    if len(set(config.statuses)) != len(config.statuses):
        raise CaseLifecycleConfigurationError("statuses must be unique")
    status_set = set(config.statuses)
    if not set(config.terminal_statuses).issubset(status_set):
        raise CaseLifecycleConfigurationError("terminal_statuses must be valid statuses")
    for source, targets in config.allowed_transitions.items():
        if source not in status_set:
            raise CaseLifecycleConfigurationError("allowed transition source is invalid")
        invalid_targets = [target for target in targets if target not in status_set]
        if invalid_targets:
            raise CaseLifecycleConfigurationError("allowed transition target is invalid")
    if not config.decision_types:
        raise CaseLifecycleConfigurationError("decision_types must be non-empty")
    if len(set(config.decision_types)) != len(config.decision_types):
        raise CaseLifecycleConfigurationError("decision_types must be unique")
    if not config.analyst.default_analyst_id.strip():
        raise CaseLifecycleConfigurationError("default_analyst_id must be non-empty")
    if not config.analyst.default_queue.strip():
        raise CaseLifecycleConfigurationError("default_queue must be non-empty")
    if not isinstance(config.analyst.require_decision_reason, bool):
        raise CaseLifecycleConfigurationError("require_decision_reason must be boolean")
    if not isinstance(config.analyst.require_comment_for_closure, bool):
        raise CaseLifecycleConfigurationError("require_comment_for_closure must be boolean")


def case_lifecycle_config_from_mapping(payload: dict[str, object] | None) -> CaseLifecycleConfig:
    if payload is None:
        return CaseLifecycleConfig()
    try:
        analyst_payload = cast(dict[str, object], payload.get("analyst") or {})
        analyst = CaseLifecycleAnalystConfig(
            default_analyst_id=str(analyst_payload.get("default_analyst_id", "local_analyst")),
            default_queue=str(analyst_payload.get("default_queue", "AML Review")),
            require_decision_reason=_as_bool(analyst_payload.get("require_decision_reason"), True),
            require_comment_for_closure=_as_bool(
                analyst_payload.get("require_comment_for_closure"), True
            ),
        )
        transitions_payload = cast(dict[str, object], payload.get("allowed_transitions") or {})
        transitions = {
            str(source): _as_tuple(targets) for source, targets in transitions_payload.items()
        }
        return CaseLifecycleConfig(
            lifecycle_version=str(payload.get("lifecycle_version", "case_lifecycle_v1")),
            statuses=_as_tuple(payload.get("statuses")) or CaseLifecycleConfig.statuses,
            terminal_statuses=_as_tuple(payload.get("terminal_statuses"))
            or CaseLifecycleConfig.terminal_statuses,
            allowed_transitions=transitions or CaseLifecycleConfig().allowed_transitions,
            decision_types=_as_tuple(payload.get("decision_types"))
            or CaseLifecycleConfig.decision_types,
            analyst=analyst,
            artefact_output_dir=str(payload.get("artefact_output_dir", "reports/model_validation")),
        )
    except CaseLifecycleConfigurationError:
        raise
    except Exception as exc:
        raise CaseLifecycleConfigurationError(
            f"Invalid case lifecycle configuration: {exc}"
        ) from exc


def load_case_lifecycle_config(
    config_path: Path | str = "config/scoring.yaml",
) -> CaseLifecycleConfig:
    path = Path(config_path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return case_lifecycle_config_from_mapping(payload.get("case_lifecycle"))
    except CaseLifecycleConfigurationError:
        raise
    except Exception as exc:
        raise CaseLifecycleConfigurationError(
            f"Failed to load case lifecycle config: {exc}"
        ) from exc
