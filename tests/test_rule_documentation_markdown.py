"""Tests for AML rule documentation Markdown rendering."""

from graph_aml.rules import (
    build_all_rule_documentation,
    get_rule_documentation,
    render_rule_documentation_index_markdown,
    render_rule_documentation_markdown,
    render_rule_documentation_pack_markdown,
)

INDIVIDUAL_SECTIONS = (
    "## Purpose",
    "## Detection Logic",
    "## Inputs",
    "## Thresholds",
    "## Alert Output",
    "## Evidence",
    "## Reason Code",
    "## Risk Scoring",
    "## Example Scenario",
    "## Example Alert",
    "## Limitations",
    "## Validation Tests",
    "## Operational Notes",
)


def test_individual_markdown_contains_required_sections() -> None:
    doc = get_rule_documentation("structuring")
    markdown = render_rule_documentation_markdown(doc)

    assert markdown.startswith("# Structuring Rule")
    for section in INDIVIDUAL_SECTIONS:
        assert section in markdown


def test_index_markdown_includes_registered_rules() -> None:
    markdown = render_rule_documentation_index_markdown(build_all_rule_documentation())

    assert "# AML Rule Documentation Index" in markdown
    assert "## Registered Rules" in markdown
    assert "`structuring`" in markdown
    assert "`circular_flow`" in markdown


def test_pack_markdown_includes_all_six_rule_names() -> None:
    markdown = render_rule_documentation_pack_markdown(build_all_rule_documentation())

    for rule_name in (
        "Structuring",
        "Fan-in",
        "Fan-out",
        "Rapid movement",
        "Dormant reactivation",
        "Circular flow",
    ):
        assert rule_name in markdown


def test_markdown_rendering_is_deterministic() -> None:
    docs = build_all_rule_documentation()

    assert render_rule_documentation_pack_markdown(docs) == render_rule_documentation_pack_markdown(
        docs
    )
    assert render_rule_documentation_index_markdown(
        docs
    ) == render_rule_documentation_index_markdown(docs)
