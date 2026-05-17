"""Tests for high-level account feature persistence workflows."""

from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.features import (
    FeaturePersistenceError,
    calculate_and_persist_account_features_from_staged,
    persist_account_features,
)


class FakeEngine:
    pass


def _features() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "account_id": "ACC_A",
                "feature_date": "2025-01-01",
                "feature_version": "account_features_v1",
                "txn_count_1d": 1,
                "txn_count_7d": 1,
                "total_sent_7d": 10.0,
                "total_received_7d": 0.0,
                "avg_txn_amount_30d": 10.0,
                "max_txn_amount_30d": 10.0,
                "unique_counterparties_7d": 1,
                "in_out_ratio_7d": 999999.0,
                "retained_balance_proxy": -10.0,
                "below_threshold_count_24h": 0,
                "dormant_days_before_activity": None,
                "cross_border_ratio_30d": 0.0,
                "high_risk_country_exposure": 0.0,
                "counterparty_entropy": 0.0,
            }
        ]
    )


def _base_features() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "account_id": "ACC_A",
                "feature_date": "2025-01-01",
                "feature_version": "account_features_v1",
                "txn_count_1d": 1,
                "txn_count_7d": 1,
                "total_sent_7d": 10.0,
                "total_received_7d": 0.0,
                "avg_txn_amount_30d": 10.0,
                "max_txn_amount_30d": 10.0,
                "unique_counterparties_7d": 1,
                "in_out_ratio_7d": 999999.0,
            }
        ]
    )


def test_persist_account_features_prepares_and_upserts_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_upsert(engine, features):
        calls.append("upsert")
        return len(features)

    monkeypatch.setattr("graph_aml.features.persistence.upsert_account_features", fake_upsert)
    monkeypatch.setattr(
        "graph_aml.features.audit.write_feature_persistence_audit_event",
        lambda *args, **kwargs: calls.append("audit"),
    )

    summary = persist_account_features(FakeEngine(), _features())

    assert calls == ["upsert", "audit"]
    assert summary["feature_rows_upserted"] == 1


def test_persist_account_features_returns_summary_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.features.persistence.upsert_account_features",
        lambda engine, features: len(features),
    )
    monkeypatch.setattr(
        "graph_aml.features.audit.write_feature_persistence_audit_event",
        lambda *args, **kwargs: None,
    )

    summary = persist_account_features(FakeEngine(), _features())

    assert set(summary) == {
        "feature_rows_upserted",
        "account_count",
        "feature_date_count",
        "feature_version_count",
    }


def test_persist_account_features_writes_audit_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "graph_aml.features.persistence.upsert_account_features",
        lambda engine, features: len(features),
    )

    def fake_audit(*args, **kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(
        "graph_aml.features.audit.write_feature_persistence_audit_event",
        fake_audit,
    )

    persist_account_features(FakeEngine(), _features(), metadata={"job": "unit-test"})

    assert audit_calls[0]["metadata"] == {"job": "unit-test"}


def test_persist_account_features_skips_audit_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "graph_aml.features.persistence.upsert_account_features",
        lambda engine, features: len(features),
    )
    monkeypatch.setattr(
        "graph_aml.features.audit.write_feature_persistence_audit_event",
        lambda *args, **kwargs: audit_calls.append(kwargs),
    )

    persist_account_features(FakeEngine(), _features(), write_audit=False)

    assert audit_calls == []


def test_persist_account_features_raises_when_preparation_fails() -> None:
    with pytest.raises(FeaturePersistenceError):
        persist_account_features(FakeEngine(), _features().drop(columns=["account_id"]))


def test_calculate_and_persist_from_staged_uses_extended_features_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "graph_aml.features.staged.calculate_extended_account_features_from_staged",
        lambda engine, config=None, limit=None: calls.append("extended") or _features(),
    )
    monkeypatch.setattr(
        "graph_aml.features.persistence.persist_account_features",
        lambda engine, features, write_audit=True, run_id=None, metadata=None: {
            "feature_rows_upserted": len(features),
            "account_count": 1,
            "feature_date_count": 1,
            "feature_version_count": 1,
        },
    )

    summary = calculate_and_persist_account_features_from_staged(FakeEngine())

    assert calls == ["extended"]
    assert summary["feature_rows_upserted"] == 1


def test_calculate_and_persist_from_staged_can_use_base_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    persisted_columns: list[str] = []
    monkeypatch.setattr(
        "graph_aml.features.staged.calculate_account_features_from_staged",
        lambda engine, config=None, limit=None: calls.append("base") or _base_features(),
    )

    def fake_persist(engine, features, write_audit=True, run_id=None, metadata=None):
        persisted_columns.extend(features.columns)
        return {
            "feature_rows_upserted": len(features),
            "account_count": 1,
            "feature_date_count": 1,
            "feature_version_count": 1,
        }

    monkeypatch.setattr("graph_aml.features.persistence.persist_account_features", fake_persist)

    calculate_and_persist_account_features_from_staged(FakeEngine(), extended=False)

    assert calls == ["base"]
    assert "retained_balance_proxy" in persisted_columns
