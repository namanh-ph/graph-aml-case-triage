"""Markdown renderers for generated documentation artefacts."""

from __future__ import annotations

from graph_aml.database.schemas import get_postgres_schemas, get_schema_descriptions
from graph_aml.documentation.data_dictionary import LIFECYCLE_STAGE_BY_SCHEMA, DataDictionary


def _cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _key(column_primary: bool, foreign_key: str | None) -> str:
    values: list[str] = []
    if column_primary:
        values.append("PK")
    if foreign_key is not None:
        values.append(f"FK -> {foreign_key}")
    return ", ".join(values)


def render_data_dictionary_markdown(data_dictionary: DataDictionary) -> str:
    """Render a complete data dictionary as deterministic Markdown."""

    schema_descriptions = get_schema_descriptions()
    lines = [
        "# Data Dictionary",
        "",
        "## Project Overview",
        "",
        f"- Project: {data_dictionary.project_name}",
        f"- Dictionary version: {data_dictionary.version}",
        f"- Generated at: {data_dictionary.generated_at}",
        "- Source metadata: database schema metadata, SQL table metadata, validation rules, "
        "and curated business descriptions.",
        "",
        "## Schema Overview",
        "",
        "| Schema | Lifecycle stage | Description |",
        "| --- | --- | --- |",
    ]

    for schema_name in get_postgres_schemas():
        lines.append(
            "| "
            f"{schema_name} | "
            f"{LIFECYCLE_STAGE_BY_SCHEMA[schema_name]} | "
            f"{schema_descriptions[schema_name]} |"
        )

    lines.extend(
        [
            "",
            "## Table Index",
            "",
            "| Table | Description |",
            "| --- | --- |",
        ]
    )
    for table in data_dictionary.tables:
        lines.append(f"| {table.qualified_name} | {_cell(table.description)} |")

    tables_by_schema = {
        schema_name: [table for table in data_dictionary.tables if table.schema_name == schema_name]
        for schema_name in get_postgres_schemas()
    }
    for schema_name in get_postgres_schemas():
        lines.extend(
            [
                "",
                f"## {schema_name} schema",
                "",
                schema_descriptions[schema_name],
            ]
        )
        for table in tables_by_schema[schema_name]:
            lines.extend(
                [
                    "",
                    f"### {table.qualified_name}",
                    "",
                    table.description,
                    "",
                    "| Column | Type | Nullable | Key | Description | Business meaning | "
                    "Validation rules | Example | Lineage source |",
                    "| --- | --- | ---: | --- | --- | --- | --- | --- | --- |",
                ]
            )
            for column in table.columns:
                lines.append(
                    "| "
                    f"{_cell(column.column_name)} | "
                    f"{_cell(column.data_type)} | "
                    f"{str(column.nullable)} | "
                    f"{_cell(_key(column.primary_key, column.foreign_key))} | "
                    f"{_cell(column.description)} | "
                    f"{_cell(column.business_meaning)} | "
                    f"{_cell('; '.join(column.validation_rules))} | "
                    f"{_cell(column.example_value)} | "
                    f"{_cell(column.lineage_source)} |"
                )

    lines.extend(
        [
            "",
            "## Notes and Assumptions",
            "",
            "- The dictionary is generated from static project metadata and does not inspect "
            "a live database.",
            "- Column business meanings are curated for governance and model validation review.",
            "- Staging lineage points back to raw payload fields where transformations currently "
            "source the values.",
            "- Exploratory dataset summaries are intentionally out of scope for this artefact.",
            "",
        ]
    )
    return "\n".join(lines)
