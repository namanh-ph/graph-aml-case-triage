"""Tests for data dictionary Markdown rendering."""

from graph_aml.documentation import build_data_dictionary, render_data_dictionary_markdown


def _markdown() -> str:
    return render_data_dictionary_markdown(build_data_dictionary())


def test_markdown_starts_with_data_dictionary_heading() -> None:
    assert _markdown().startswith("# Data Dictionary")


def test_markdown_includes_project_overview() -> None:
    assert "## Project Overview" in _markdown()


def test_markdown_includes_schema_overview() -> None:
    assert "## Schema Overview" in _markdown()


def test_markdown_includes_all_schema_sections() -> None:
    markdown = _markdown()

    for schema_name in ("raw", "staging", "mart", "aml", "governance"):
        assert f"## {schema_name} schema" in markdown


def test_markdown_includes_all_qualified_table_names() -> None:
    dictionary = build_data_dictionary()
    markdown = render_data_dictionary_markdown(dictionary)

    for table in dictionary.tables:
        assert table.qualified_name in markdown


def test_markdown_includes_column_tables() -> None:
    assert "| Column | Type | Nullable | Key | Description |" in _markdown()


def test_markdown_includes_notes_and_assumptions() -> None:
    assert "## Notes and Assumptions" in _markdown()


def test_markdown_includes_staging_transactions() -> None:
    assert "staging.transactions" in _markdown()


def test_markdown_includes_aml_alerts() -> None:
    assert "aml.alerts" in _markdown()


def test_markdown_includes_governance_audit_events() -> None:
    assert "governance.audit_events" in _markdown()
