"""Tests for release documentation checks."""

import pytest

from graph_aml.release import (
    DOCUMENTATION_CHECK_COLUMNS,
    DocumentationCheckError,
    ReleaseDocumentationConfig,
    ReleaseReadinessConfig,
    check_document_sections,
    check_required_documents,
    run_documentation_checks,
)


def test_documentation_checks_find_docs_and_sections(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("# Project Overview\nLocal setup\n", encoding="utf-8")
    config = ReleaseReadinessConfig(
        documentation=ReleaseDocumentationConfig(
            required_docs=("README.md", "missing.md"),
            required_sections={"README.md": ("project overview", "dashboard")},
        )
    )

    docs = check_required_documents(config, "run")
    sections = check_document_sections(config, "run")
    all_checks = run_documentation_checks(config, "run")

    assert tuple(all_checks.columns) == DOCUMENTATION_CHECK_COLUMNS
    assert "fail" in set(docs["status"])
    assert "pass" in set(sections["status"])
    assert "warning" in set(sections["status"])


def test_documentation_checks_reject_unsafe_paths() -> None:
    with pytest.raises(DocumentationCheckError):
        check_required_documents(
            ReleaseReadinessConfig(
                documentation=ReleaseDocumentationConfig(required_docs=("../outside",))
            )
        )
