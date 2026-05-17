"""Tests for AML rule documentation artefact writers."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from graph_aml.rules import (
    RuleDocumentationError,
    build_all_rule_documentation,
    generate_rule_documentation_artefacts,
    get_rule_documentation,
    write_individual_rule_documentation_pages,
    write_rule_documentation_index_markdown,
    write_rule_documentation_json,
    write_rule_documentation_pack_markdown,
)


def test_json_writer_writes_parseable_json_with_all_rules(tmp_path: Path) -> None:
    path = write_rule_documentation_json(
        build_all_rule_documentation(),
        tmp_path / "nested" / "aml_rule_documentation.json",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload) == 6
    assert {item["rule_key"] for item in payload} == {
        "structuring",
        "fan_in",
        "fan_out",
        "rapid_movement",
        "dormant_reactivation",
        "circular_flow",
    }


def test_index_and_pack_markdown_writers_write_files(tmp_path: Path) -> None:
    docs = build_all_rule_documentation()

    index_path = write_rule_documentation_index_markdown(docs, tmp_path / "docs" / "index.md")
    pack_path = write_rule_documentation_pack_markdown(docs, tmp_path / "docs" / "pack.md")

    assert index_path.is_file()
    assert pack_path.is_file()
    assert "# AML Rule Documentation Index" in index_path.read_text(encoding="utf-8")
    assert "# AML Rule Documentation Pack" in pack_path.read_text(encoding="utf-8")


def test_individual_page_writer_writes_one_page_per_rule(tmp_path: Path) -> None:
    pages = write_individual_rule_documentation_pages(build_all_rule_documentation(), tmp_path)

    assert set(pages) == {
        "structuring",
        "fan_in",
        "fan_out",
        "rapid_movement",
        "dormant_reactivation",
        "circular_flow",
    }
    assert all(path.is_file() for path in pages.values())


def test_high_level_artefact_generator_writes_expected_artefacts(tmp_path: Path) -> None:
    artefacts = generate_rule_documentation_artefacts(
        docs_output_dir=tmp_path / "docs",
        reports_output_dir=tmp_path / "reports",
    )

    assert {
        "index_markdown",
        "pack_markdown",
        "json",
        "rule.structuring",
        "rule.fan_in",
        "rule.fan_out",
        "rule.rapid_movement",
        "rule.dormant_reactivation",
        "rule.circular_flow",
    }.issubset(artefacts)
    assert all(isinstance(path, Path) for path in artefacts.values())
    assert all(path.is_file() for path in artefacts.values())


def test_artefact_generation_supports_subset_rule_keys(tmp_path: Path) -> None:
    artefacts = generate_rule_documentation_artefacts(
        rule_keys=("structuring", "circular-flow"),
        docs_output_dir=tmp_path / "docs",
        reports_output_dir=tmp_path / "reports",
    )

    assert set(artefacts) == {
        "index_markdown",
        "pack_markdown",
        "json",
        "rule.structuring",
        "rule.circular_flow",
    }
    payload = json.loads(artefacts["json"].read_text(encoding="utf-8"))
    assert [item["rule_key"] for item in payload] == ["structuring", "circular_flow"]


def test_artefact_generation_validates_documentation_before_writing(tmp_path: Path) -> None:
    invalid_doc = replace(get_rule_documentation("structuring"), business_purpose="")

    with pytest.raises(RuleDocumentationError):
        write_rule_documentation_json((invalid_doc,), tmp_path / "invalid.json")
