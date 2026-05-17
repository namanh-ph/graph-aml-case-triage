"""Tests for extended account feature summaries and artefacts."""

import json
from pathlib import Path

import pandas as pd

from graph_aml.features import (
    EXTENDED_ACCOUNT_FEATURE_COLUMNS,
    calculate_extended_account_features,
    generate_extended_account_feature_artefacts,
    summarise_account_features,
)


def _accounts() -> pd.DataFrame:
    return pd.DataFrame([{"account_id": "ACC_A"}, {"account_id": "ACC_B"}])


def _countries() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"country_code": "US", "is_high_risk": False, "risk_score": 10.0},
            {"country_code": "PA", "is_high_risk": True, "risk_score": 80.0},
        ]
    )


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": "TXN_001",
                "sender_account_id": "ACC_A",
                "receiver_account_id": "ACC_B",
                "counterparty_id": None,
                "transaction_timestamp": "2025-01-01T10:00:00Z",
                "amount": 9600.0,
                "origin_country": "US",
                "destination_country": "PA",
                "is_cross_border": True,
            }
        ]
    )


def _features() -> pd.DataFrame:
    return calculate_extended_account_features(_accounts(), _transactions(), _countries())


def test_summarise_account_features_includes_extended_summary_keys() -> None:
    summary = summarise_account_features(_features())

    assert "mean_retained_balance_proxy" in summary
    assert "mean_cross_border_ratio_30d" in summary
    assert "mean_counterparty_entropy" in summary


def test_extended_summary_is_json_serialisable() -> None:
    json.dumps(summarise_account_features(_features()), sort_keys=True)


def test_generate_extended_account_feature_artefacts_writes_feature_csv(
    tmp_path: Path,
) -> None:
    paths = generate_extended_account_feature_artefacts(
        _accounts(),
        _transactions(),
        _countries(),
        output_dir=tmp_path,
    )

    assert paths["features_csv"].is_file()


def test_generate_extended_account_feature_artefacts_writes_summary_json(
    tmp_path: Path,
) -> None:
    paths = generate_extended_account_feature_artefacts(
        _accounts(),
        _transactions(),
        _countries(),
        output_dir=tmp_path,
    )

    assert paths["summary_json"].is_file()


def test_written_feature_csv_includes_extended_columns(tmp_path: Path) -> None:
    paths = generate_extended_account_feature_artefacts(
        _accounts(),
        _transactions(),
        _countries(),
        output_dir=tmp_path,
    )

    assert tuple(pd.read_csv(paths["features_csv"]).columns) == EXTENDED_ACCOUNT_FEATURE_COLUMNS


def test_written_summary_json_includes_extended_summary_keys(tmp_path: Path) -> None:
    paths = generate_extended_account_feature_artefacts(
        _accounts(),
        _transactions(),
        _countries(),
        output_dir=tmp_path,
    )

    payload = json.loads(paths["summary_json"].read_text(encoding="utf-8"))
    assert "mean_high_risk_country_exposure" in payload


def test_artefact_generation_validates_extended_features_before_writing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[str] = []

    def fake_validate(features):
        calls.append("validate")

    monkeypatch.setattr(
        "graph_aml.features.artefacts.validate_extended_account_features",
        fake_validate,
    )

    generate_extended_account_feature_artefacts(
        _accounts(),
        _transactions(),
        _countries(),
        output_dir=tmp_path,
    )

    assert calls == ["validate"]
