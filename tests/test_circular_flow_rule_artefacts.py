"""Tests for circular flow rule artefact writers."""

import json

import pandas as pd

from graph_aml.rules import (
    build_circular_flow_alerts,
    detect_circular_flows,
    generate_circular_flow_rule_artefacts,
    write_circular_flow_alerts_json,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_accounts_fixture,
    build_circular_flow_non_trigger_transactions_fixture,
    build_circular_flow_three_hop_transactions_fixture,
)


def test_write_circular_flow_alerts_json_writes_parseable_json(tmp_path) -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())
    alerts = build_circular_flow_alerts(detections, build_circular_flow_accounts_fixture())

    path = write_circular_flow_alerts_json(alerts, tmp_path / "alerts.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload[0]["alert_id"]
    assert payload[0]["evidence_ids"]


def test_generate_circular_flow_rule_artefacts_writes_all_expected_files(tmp_path) -> None:
    paths = generate_circular_flow_rule_artefacts(
        build_circular_flow_three_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
        tmp_path / "nested" / "artefacts",
    )

    assert set(paths) == {"detections_json", "detections_csv", "summary_json", "alerts_json"}
    assert all(path.is_file() for path in paths.values())
    assert (tmp_path / "nested" / "artefacts").is_dir()


def test_empty_detections_and_alerts_write_valid_artefacts(tmp_path) -> None:
    paths = generate_circular_flow_rule_artefacts(
        build_circular_flow_non_trigger_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
        tmp_path,
    )

    assert json.loads(paths["detections_json"].read_text(encoding="utf-8")) == []
    assert json.loads(paths["alerts_json"].read_text(encoding="utf-8")) == []
    assert "cycle_count" in json.loads(paths["summary_json"].read_text(encoding="utf-8"))
    assert pd.read_csv(paths["detections_csv"]).empty
