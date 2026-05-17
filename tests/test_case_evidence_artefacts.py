"""Tests for case evidence artefact writers."""

import json
from pathlib import Path

from graph_aml.cases import (
    CaseEvidencePersistenceResult,
    generate_case_evidence_artefacts,
    write_case_evidence_packs_json,
    write_case_evidence_persistence_summary_json,
    write_case_evidence_summary_json,
    write_case_explanations_json,
    write_case_explanations_markdown,
)
from tests.fixtures.case_evidence import evidence_result


def test_case_evidence_artefact_writers(tmp_path: Path) -> None:
    result = evidence_result()
    paths = [
        write_case_evidence_packs_json(result.evidence_packs, tmp_path / "nested" / "packs.json"),
        write_case_explanations_json(result.explanations, tmp_path / "explanations.json"),
        write_case_evidence_summary_json({"row_count": 1}, tmp_path / "summary.json"),
        write_case_evidence_persistence_summary_json(
            CaseEvidencePersistenceResult(), tmp_path / "persistence.json"
        ),
    ]
    markdown = write_case_explanations_markdown(result.explanations, tmp_path / "explanations.md")
    for path in paths:
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), list | dict)
    assert markdown.read_text(encoding="utf-8").startswith("# Case Explanations")


def test_high_level_case_evidence_artefact_generator(tmp_path: Path) -> None:
    paths = generate_case_evidence_artefacts(
        evidence_result(),
        CaseEvidencePersistenceResult(),
        tmp_path,
    )
    assert set(paths) == {
        "case_evidence_packs_json",
        "case_explanations_json",
        "case_explanations_markdown",
        "case_evidence_summary_json",
        "case_evidence_persistence_summary_json",
    }
    assert all(path.exists() for path in paths.values())
