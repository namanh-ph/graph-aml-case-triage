"""Tests for case generation artefacts."""

import json

import pandas as pd

from graph_aml.cases import (
    CaseGenerationResult,
    CasePersistenceResult,
    generate_case_generation_artefacts,
    write_case_generation_summary_json,
    write_case_links_json,
    write_case_persistence_summary_json,
    write_generated_cases_csv,
    write_generated_cases_json,
)


def result() -> CaseGenerationResult:
    return CaseGenerationResult(
        cases=pd.DataFrame({"case_id": ["CASE1"], "priority_score": [80]}),
        case_alerts=pd.DataFrame({"case_id": ["CASE1"], "alert_id": ["AL1"]}),
        case_entities=pd.DataFrame(
            {
                "case_id": ["CASE1"],
                "entity_type": ["account"],
                "entity_id": ["A1"],
                "relationship": ["primary"],
            }
        ),
        groups=pd.DataFrame(),
        summary={"case_count": 1},
    )


def test_case_artefact_writers_write_parseable_files(tmp_path) -> None:  # noqa: ANN001
    csv_path = write_generated_cases_csv(result().cases, tmp_path / "nested" / "cases.csv")
    json_path = write_generated_cases_json(result().cases, tmp_path / "cases.json")
    links_path = write_case_links_json(
        result().case_alerts, result().case_entities, tmp_path / "links.json"
    )
    summary_path = write_case_generation_summary_json({"case_count": 1}, tmp_path / "summary.json")
    persistence_path = write_case_persistence_summary_json(
        CasePersistenceResult(), tmp_path / "persist.json"
    )
    assert csv_path.exists()
    for path in (json_path, links_path, summary_path, persistence_path):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), list | dict)


def test_high_level_case_artefact_generator_returns_paths(tmp_path) -> None:  # noqa: ANN001
    paths = generate_case_generation_artefacts(result(), CasePersistenceResult(), tmp_path)
    assert set(paths) == {
        "generated_cases_csv",
        "generated_cases_json",
        "case_links_json",
        "case_generation_summary_json",
        "case_persistence_summary_json",
    }
    assert all(path.exists() for path in paths.values())


def test_empty_case_frames_still_write_valid_artefacts(tmp_path) -> None:  # noqa: ANN001
    empty = CaseGenerationResult(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    paths = generate_case_generation_artefacts(empty, None, tmp_path)
    assert all(path.exists() for path in paths.values())
