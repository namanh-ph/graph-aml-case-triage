"""Configuration models for release readiness checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import yaml

from graph_aml.release.exceptions import ReleaseConfigurationError


@dataclass(frozen=True)
class ReleaseRepositoryConfig:
    required_files: tuple[str, ...] = (
        "README.md",
        "pyproject.toml",
        "Makefile",
        "docker-compose.yml",
        ".env.example",
        "config/database.yaml",
        "config/graph.yaml",
        "config/model.yaml",
        "config/scoring.yaml",
        "config/dashboard.yaml",
        "config/demo.yaml",
        "config/governance.yaml",
        "config/security.yaml",
    )
    required_directories: tuple[str, ...] = (
        "app",
        "app/pages",
        "config",
        "docs",
        "reports/model_validation",
        "scripts",
        "src/graph_aml",
        "tests",
    )
    forbidden_paths: tuple[str, ...] = (
        ".env",
        "data/raw/real",
        "data/private",
        "secrets",
    )
    required_make_targets: tuple[str, ...] = (
        "test",
        "check",
        "services-up",
        "services-down",
        "demo-readiness",
        "demo-run-dry",
        "demo-run",
        "dashboard",
        "labels-build-persist",
        "model-supervised-train-persist",
        "model-comparison-run-persist",
        "monitoring-run-persist",
        "explainability-run-persist",
        "governance-inventory-run-persist",
        "security-controls-run-persist",
    )


@dataclass(frozen=True)
class ReleaseDocumentationConfig:
    required_docs: tuple[str, ...] = (
        "README.md",
        "docs/developer_workflow.md",
        "docs/governance_framework.md",
        "docs/model_validation.md",
        "docs/portfolio_walkthrough.md",
        "docs/graph_model.md",
        "docs/aml_typologies.md",
        "docs/rule_engine.md",
    )
    required_sections: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class ReleaseArtefactConfig:
    report_dir: str = "reports/model_validation"
    required_files: tuple[str, ...] = (
        "dataset_summary.md",
        "feature_dictionary.md",
        "validation_methodology.md",
        "model_card.md",
        "consolidated_model_card.md",
        "model_comparison_report.md",
        "drift_monitoring_report.md",
        "governance_inventory_report.md",
        "security_control_report.md",
    )
    optional_files: tuple[str, ...] = (
        "supervised_model_card.md",
        "graph_analytics_report.md",
        "threshold_recommendations.csv",
        "champion_challenger_results.csv",
        "monitoring_summary.json",
        "explainability_summary.json",
        "governance_inventory_summary.json",
        "security_control_summary.json",
    )
    allowed_extensions: tuple[str, ...] = (".md", ".json", ".csv", ".txt", ".yaml", ".yml")
    max_file_size_mb: int = 25


@dataclass(frozen=True)
class ReleaseEvidencePackConfig:
    output_dir: str = "reports/model_validation/release_pack"
    include_command_transcript_template: bool = True
    include_dashboard_walkthrough: bool = True
    include_portfolio_summary: bool = True
    include_architecture_summary: bool = True
    include_validation_index: bool = True
    include_known_limitations: bool = True
    include_next_steps: bool = True


@dataclass(frozen=True)
class ReleasePersistenceConfig:
    write_database: bool = True
    write_artefacts: bool = True
    write_audit: bool = True
    artefact_output_dir: str = "reports/model_validation"


@dataclass(frozen=True)
class ReleaseReadinessConfig:
    release_name: str = "aml_portfolio_release"
    release_version: str = "portfolio_release_v1"
    repository: ReleaseRepositoryConfig = field(default_factory=ReleaseRepositoryConfig)
    documentation: ReleaseDocumentationConfig = field(default_factory=ReleaseDocumentationConfig)
    artefacts: ReleaseArtefactConfig = field(default_factory=ReleaseArtefactConfig)
    evidence_pack: ReleaseEvidencePackConfig = field(default_factory=ReleaseEvidencePackConfig)
    persistence: ReleasePersistenceConfig = field(default_factory=ReleasePersistenceConfig)


def _bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ReleaseConfigurationError(f"{name} must be boolean")
    return value


def _int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReleaseConfigurationError(f"{name} must be an integer")
    return int(value)


def _tuple_strings(value: object, name: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise ReleaseConfigurationError(f"{name} must be a list")
    values = tuple(str(item).strip() for item in value)
    if (not allow_empty and not values) or any(not item for item in values):
        raise ReleaseConfigurationError(f"{name} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ReleaseConfigurationError(f"{name} must contain unique strings")
    return values


def _section_mapping(raw: object) -> dict[str, tuple[str, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ReleaseConfigurationError("documentation.required_sections must be a mapping")
    sections: dict[str, tuple[str, ...]] = {}
    for doc_path, values in raw.items():
        key = str(doc_path).strip()
        if not key:
            raise ReleaseConfigurationError("required section document paths must be non-empty")
        sections[key] = _tuple_strings(values, f"required_sections.{key}")
    return sections


def validate_release_readiness_config(config: ReleaseReadinessConfig) -> None:
    """Validate release configuration without touching external services."""

    if not config.release_name.strip():
        raise ReleaseConfigurationError("release_name must be non-empty")
    if not config.release_version.strip():
        raise ReleaseConfigurationError("release_version must be non-empty")
    _tuple_strings(config.repository.required_files, "repository.required_files")
    _tuple_strings(config.repository.required_directories, "repository.required_directories")
    _tuple_strings(config.repository.forbidden_paths, "repository.forbidden_paths")
    _tuple_strings(config.repository.required_make_targets, "repository.required_make_targets")
    _tuple_strings(config.documentation.required_docs, "documentation.required_docs")
    _section_mapping(config.documentation.required_sections)
    if not config.artefacts.report_dir.strip():
        raise ReleaseConfigurationError("artefact report_dir must be non-empty")
    _tuple_strings(config.artefacts.required_files, "artefacts.required_files")
    _tuple_strings(config.artefacts.optional_files, "artefacts.optional_files", allow_empty=True)
    extensions = _tuple_strings(config.artefacts.allowed_extensions, "artefacts.allowed_extensions")
    if any(not value.startswith(".") for value in extensions):
        raise ReleaseConfigurationError("allowed extensions must start with '.'")
    if config.artefacts.max_file_size_mb <= 0:
        raise ReleaseConfigurationError("max_file_size_mb must be positive")
    if not config.evidence_pack.output_dir.strip():
        raise ReleaseConfigurationError("evidence output_dir must be non-empty")
    for field_name, value in vars(config.evidence_pack).items():
        if field_name.startswith("include_"):
            _bool(value, f"evidence_pack.{field_name}")
    for field_name, value in vars(config.persistence).items():
        if field_name.startswith("write_"):
            _bool(value, f"persistence.{field_name}")
    if not config.persistence.artefact_output_dir.strip():
        raise ReleaseConfigurationError("persistence artefact_output_dir must be non-empty")


def release_readiness_config_from_mapping(
    payload: dict[str, object] | None,
) -> ReleaseReadinessConfig:
    """Build release readiness configuration from a mapping."""

    data = payload or {}
    if "release_readiness" in data and isinstance(data["release_readiness"], dict):
        data = cast("dict[str, object]", data["release_readiness"])
    default = ReleaseReadinessConfig()
    repo_raw = cast("dict[str, object]", data.get("repository", {}) or {})
    docs_raw = cast("dict[str, object]", data.get("documentation", {}) or {})
    artefacts_raw = cast("dict[str, object]", data.get("artefacts", {}) or {})
    evidence_raw = cast("dict[str, object]", data.get("evidence_pack", {}) or {})
    persistence_raw = cast("dict[str, object]", data.get("persistence", {}) or {})
    config = ReleaseReadinessConfig(
        release_name=str(data.get("release_name", default.release_name)),
        release_version=str(data.get("release_version", default.release_version)),
        repository=ReleaseRepositoryConfig(
            required_files=_tuple_strings(
                repo_raw.get("required_files", default.repository.required_files),
                "repository.required_files",
            ),
            required_directories=_tuple_strings(
                repo_raw.get("required_directories", default.repository.required_directories),
                "repository.required_directories",
            ),
            forbidden_paths=_tuple_strings(
                repo_raw.get("forbidden_paths", default.repository.forbidden_paths),
                "repository.forbidden_paths",
            ),
            required_make_targets=_tuple_strings(
                repo_raw.get(
                    "required_make_targets",
                    default.repository.required_make_targets,
                ),
                "repository.required_make_targets",
            ),
        ),
        documentation=ReleaseDocumentationConfig(
            required_docs=_tuple_strings(
                docs_raw.get("required_docs", default.documentation.required_docs),
                "documentation.required_docs",
            ),
            required_sections=_section_mapping(
                docs_raw.get("required_sections", default.documentation.required_sections)
            ),
        ),
        artefacts=ReleaseArtefactConfig(
            report_dir=str(artefacts_raw.get("report_dir", default.artefacts.report_dir)),
            required_files=_tuple_strings(
                artefacts_raw.get("required_files", default.artefacts.required_files),
                "artefacts.required_files",
            ),
            optional_files=_tuple_strings(
                artefacts_raw.get("optional_files", default.artefacts.optional_files),
                "artefacts.optional_files",
                allow_empty=True,
            ),
            allowed_extensions=_tuple_strings(
                artefacts_raw.get("allowed_extensions", default.artefacts.allowed_extensions),
                "artefacts.allowed_extensions",
            ),
            max_file_size_mb=_int(
                artefacts_raw.get("max_file_size_mb", default.artefacts.max_file_size_mb),
                "artefacts.max_file_size_mb",
            ),
        ),
        evidence_pack=ReleaseEvidencePackConfig(
            output_dir=str(evidence_raw.get("output_dir", default.evidence_pack.output_dir)),
            include_command_transcript_template=_bool(
                evidence_raw.get(
                    "include_command_transcript_template",
                    default.evidence_pack.include_command_transcript_template,
                ),
                "evidence_pack.include_command_transcript_template",
            ),
            include_dashboard_walkthrough=_bool(
                evidence_raw.get(
                    "include_dashboard_walkthrough",
                    default.evidence_pack.include_dashboard_walkthrough,
                ),
                "evidence_pack.include_dashboard_walkthrough",
            ),
            include_portfolio_summary=_bool(
                evidence_raw.get(
                    "include_portfolio_summary",
                    default.evidence_pack.include_portfolio_summary,
                ),
                "evidence_pack.include_portfolio_summary",
            ),
            include_architecture_summary=_bool(
                evidence_raw.get(
                    "include_architecture_summary",
                    default.evidence_pack.include_architecture_summary,
                ),
                "evidence_pack.include_architecture_summary",
            ),
            include_validation_index=_bool(
                evidence_raw.get(
                    "include_validation_index",
                    default.evidence_pack.include_validation_index,
                ),
                "evidence_pack.include_validation_index",
            ),
            include_known_limitations=_bool(
                evidence_raw.get(
                    "include_known_limitations",
                    default.evidence_pack.include_known_limitations,
                ),
                "evidence_pack.include_known_limitations",
            ),
            include_next_steps=_bool(
                evidence_raw.get(
                    "include_next_steps",
                    default.evidence_pack.include_next_steps,
                ),
                "evidence_pack.include_next_steps",
            ),
        ),
        persistence=ReleasePersistenceConfig(
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
                persistence_raw.get(
                    "artefact_output_dir",
                    default.persistence.artefact_output_dir,
                )
            ),
        ),
    )
    validate_release_readiness_config(config)
    return config


def load_release_readiness_config(
    config_path: Path | str = "config/release.yaml",
) -> ReleaseReadinessConfig:
    """Load release readiness configuration from YAML."""

    path = Path(config_path)
    if not path.exists():
        return ReleaseReadinessConfig()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ReleaseConfigurationError("release config YAML must be a mapping")
    return release_readiness_config_from_mapping(cast("dict[str, object]", payload))
