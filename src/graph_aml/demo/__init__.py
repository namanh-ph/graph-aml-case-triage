"""End-to-end demo orchestration helpers for Graph AML."""

from __future__ import annotations

from graph_aml.demo.artefacts import (
    build_demo_artefact_index,
    generate_demo_readiness_artefacts,
    write_demo_artefact_index_json,
    write_demo_readiness_report_json,
    write_demo_run_summary_json,
    write_demo_validation_summary_json,
)
from graph_aml.demo.config import (
    DemoCommandConfig,
    DemoConfig,
    DemoOrchestrationConfig,
    DemoSafetyConfig,
    DemoStepConfig,
    DemoValidationThresholdConfig,
    demo_orchestration_config_from_mapping,
    load_demo_orchestration_config,
    validate_demo_orchestration_config,
)
from graph_aml.demo.exceptions import (
    DemoArtefactError,
    DemoConfigurationError,
    DemoError,
    DemoStepError,
    DemoValidationError,
)
from graph_aml.demo.readiness import (
    build_demo_readiness_summary,
    check_python_package_imports,
    check_required_directories_exist,
    check_required_files_exist,
)
from graph_aml.demo.runner import (
    DemoRunResult,
    build_demo_run_id,
    demo_run_result_to_dict,
    execute_demo_step,
    run_demo_pipeline,
)
from graph_aml.demo.steps import (
    DemoStep,
    DemoStepResult,
    build_demo_steps,
    demo_step_result_to_dict,
    validate_demo_command_safety,
)
from graph_aml.demo.validation import (
    build_demo_validation_summary,
    read_demo_database_counts,
    validate_demo_artefacts,
    validate_demo_database_counts,
)

__all__ = [
    "DemoArtefactError",
    "DemoCommandConfig",
    "DemoConfig",
    "DemoConfigurationError",
    "DemoError",
    "DemoOrchestrationConfig",
    "DemoRunResult",
    "DemoSafetyConfig",
    "DemoStep",
    "DemoStepConfig",
    "DemoStepError",
    "DemoStepResult",
    "DemoValidationError",
    "DemoValidationThresholdConfig",
    "build_demo_artefact_index",
    "build_demo_readiness_summary",
    "build_demo_run_id",
    "build_demo_steps",
    "build_demo_validation_summary",
    "check_python_package_imports",
    "check_required_directories_exist",
    "check_required_files_exist",
    "demo_orchestration_config_from_mapping",
    "demo_run_result_to_dict",
    "demo_step_result_to_dict",
    "execute_demo_step",
    "generate_demo_readiness_artefacts",
    "load_demo_orchestration_config",
    "read_demo_database_counts",
    "run_demo_pipeline",
    "validate_demo_artefacts",
    "validate_demo_command_safety",
    "validate_demo_database_counts",
    "validate_demo_orchestration_config",
    "write_demo_artefact_index_json",
    "write_demo_readiness_report_json",
    "write_demo_run_summary_json",
    "write_demo_validation_summary_json",
]
