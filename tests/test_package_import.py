"""Smoke tests for package importability."""

import graph_aml


def test_package_imports() -> None:
    assert graph_aml.__version__ == "0.1.0"
