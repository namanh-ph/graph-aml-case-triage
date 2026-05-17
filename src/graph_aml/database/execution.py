"""Utilities for executing trusted local SQL artefacts."""

from pathlib import Path

from sqlalchemy import Engine, text

from graph_aml.database.exceptions import DatabaseExecutionError


def split_sql_statements(sql: str) -> list[str]:
    """Split SQL text into statements on semicolons outside quoted strings."""

    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            current.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and next_char == "/":
                current.append(next_char)
                in_block_comment = False
                index += 2
                continue
            index += 1
            continue

        if not in_single_quote and not in_double_quote:
            if char == "-" and next_char == "-":
                current.extend((char, next_char))
                in_line_comment = True
                index += 2
                continue
            if char == "/" and next_char == "*":
                current.extend((char, next_char))
                in_block_comment = True
                index += 2
                continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        index += 1

    trailing_statement = "".join(current).strip()
    if trailing_statement:
        statements.append(trailing_statement)

    return statements


def execute_sql(engine: Engine, sql: str) -> int:
    """Execute trusted SQL text inside a single transaction."""

    statements = split_sql_statements(sql)
    try:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    except Exception as exc:
        raise DatabaseExecutionError(f"SQL execution failed: {exc}") from exc
    return len(statements)


def execute_sql_file(engine: Engine, path: Path | str) -> int:
    """Read and execute a trusted SQL file."""

    sql_path = Path(path)
    if not sql_path.is_file():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    return execute_sql(engine, sql_path.read_text(encoding="utf-8"))
