"""Smoke tests for the repository scaffold."""

from pathlib import Path


def test_expected_top_level_paths_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    expected_paths = [
        "README.md",
        "pyproject.toml",
        "Makefile",
        "config",
        "data",
        "docs",
        "reports",
        "notebooks",
        "src/graph_aml",
        "app/streamlit_app.py",
        "tests",
    ]

    for relative_path in expected_paths:
        assert (root / relative_path).exists(), f"Missing scaffold path: {relative_path}"
