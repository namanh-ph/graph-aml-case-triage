"""Artefact writers for formal AML rule documentation."""

from __future__ import annotations

import json
from pathlib import Path

from graph_aml.rules.documentation import (
    RuleDocumentation,
    build_all_rule_documentation,
    render_rule_documentation_index_markdown,
    render_rule_documentation_markdown,
    render_rule_documentation_pack_markdown,
    rule_documentation_collection_to_dicts,
    validate_rule_documentation,
)
from graph_aml.rules.exceptions import RuleDocumentationError


def write_rule_documentation_json(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
    output_path: Path | str = "reports/model_validation/aml_rule_documentation.json",
) -> Path:
    """Write rule documentation metadata as deterministic JSON."""

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = rule_documentation_collection_to_dicts(tuple(docs))
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        return path
    except RuleDocumentationError:
        raise
    except Exception as exc:
        raise RuleDocumentationError(f"Could not write rule documentation JSON: {exc}") from exc


def write_rule_documentation_index_markdown(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
    output_path: Path | str = "docs/rules/index.md",
) -> Path:
    """Write the AML rule documentation index Markdown file."""

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            render_rule_documentation_index_markdown(tuple(docs)) + "\n",
            encoding="utf-8",
        )
        return path
    except RuleDocumentationError:
        raise
    except Exception as exc:
        raise RuleDocumentationError(
            f"Could not write rule documentation index Markdown: {exc}"
        ) from exc


def write_rule_documentation_pack_markdown(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
    output_path: Path | str = "docs/rules/aml_rule_documentation_pack.md",
) -> Path:
    """Write the complete AML rule documentation pack Markdown file."""

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            render_rule_documentation_pack_markdown(tuple(docs)) + "\n",
            encoding="utf-8",
        )
        return path
    except RuleDocumentationError:
        raise
    except Exception as exc:
        raise RuleDocumentationError(
            f"Could not write rule documentation pack Markdown: {exc}"
        ) from exc


def write_individual_rule_documentation_pages(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
    output_dir: Path | str = "docs/rules",
) -> dict[str, Path]:
    """Write one Markdown page per documented AML rule."""

    try:
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        pages: dict[str, Path] = {}
        for documentation in docs:
            validate_rule_documentation(documentation)
            path = directory / f"{documentation.rule_key}.md"
            path.write_text(
                render_rule_documentation_markdown(documentation) + "\n",
                encoding="utf-8",
            )
            pages[documentation.rule_key] = path
        return pages
    except RuleDocumentationError:
        raise
    except Exception as exc:
        raise RuleDocumentationError(
            f"Could not write individual rule documentation pages: {exc}"
        ) from exc


def generate_rule_documentation_artefacts(
    rule_keys: tuple[str, ...] | list[str] | None = None,
    docs_output_dir: Path | str = "docs/rules",
    reports_output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Build, validate, and write all requested AML rule documentation artefacts."""

    try:
        docs = build_all_rule_documentation(rule_keys)
        for documentation in docs:
            validate_rule_documentation(documentation)

        docs_dir = Path(docs_output_dir)
        reports_dir = Path(reports_output_dir)
        artefacts: dict[str, Path] = {
            "index_markdown": write_rule_documentation_index_markdown(
                docs,
                docs_dir / "index.md",
            ),
            "pack_markdown": write_rule_documentation_pack_markdown(
                docs,
                docs_dir / "aml_rule_documentation_pack.md",
            ),
            "json": write_rule_documentation_json(
                docs,
                reports_dir / "aml_rule_documentation.json",
            ),
        }
        for rule_key, path in write_individual_rule_documentation_pages(
            docs,
            docs_dir,
        ).items():
            artefacts[f"rule.{rule_key}"] = path
        return artefacts
    except RuleDocumentationError:
        raise
    except Exception as exc:
        raise RuleDocumentationError(
            f"Could not generate rule documentation artefacts: {exc}"
        ) from exc
