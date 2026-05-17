"""Tests for high-level alert persistence workflow."""

from __future__ import annotations

import pytest

from graph_aml.alerts import AlertPersistenceError, create_alert_record, persist_alerts


class FakeEngine:
    pass


def _alerts():
    return [
        create_alert_record(
            "AL_001",
            "ACC_001",
            "CUST_001",
            "Structuring",
            "structuring",
            "high",
            80,
            "STRUCTURING",
            ["TXN_001"],
            "2025-01-01T00:00:00Z",
            "2025-01-02T00:00:00Z",
        )
    ]


def test_persist_alerts_prepares_and_upserts_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "graph_aml.alerts.persistence.upsert_alerts",
        lambda engine, alerts: calls.append("upsert") or len(alerts),
    )
    monkeypatch.setattr(
        "graph_aml.alerts.audit.write_alert_persistence_audit_event",
        lambda *args, **kwargs: calls.append("audit"),
    )

    summary = persist_alerts(FakeEngine(), _alerts())

    assert calls == ["upsert", "audit"]
    assert summary["alerts_upserted"] == 1


def test_persist_alerts_returns_summary_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.alerts.persistence.upsert_alerts",
        lambda engine, alerts: len(alerts),
    )
    monkeypatch.setattr(
        "graph_aml.alerts.audit.write_alert_persistence_audit_event",
        lambda *args, **kwargs: None,
    )

    summary = persist_alerts(FakeEngine(), _alerts())

    assert set(summary) == {
        "alerts_upserted",
        "unique_account_count",
        "unique_rule_count",
        "unique_typology_count",
    }


def test_persist_alerts_writes_audit_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    audit_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "graph_aml.alerts.persistence.upsert_alerts",
        lambda engine, alerts: len(alerts),
    )

    def fake_audit(*args, **kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr("graph_aml.alerts.audit.write_alert_persistence_audit_event", fake_audit)

    persist_alerts(FakeEngine(), _alerts(), metadata={"source": "unit-test"})

    assert audit_calls[0]["metadata"] == {"source": "unit-test"}


def test_persist_alerts_skips_audit_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    audit_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "graph_aml.alerts.persistence.upsert_alerts",
        lambda engine, alerts: len(alerts),
    )
    monkeypatch.setattr(
        "graph_aml.alerts.audit.write_alert_persistence_audit_event",
        lambda *args, **kwargs: audit_calls.append(kwargs),
    )

    persist_alerts(FakeEngine(), _alerts(), write_audit=False)

    assert audit_calls == []


def test_persist_alerts_raises_when_preparation_fails() -> None:
    with pytest.raises(AlertPersistenceError):
        persist_alerts(FakeEngine(), [{"alert_id": ""}])


def test_persist_alerts_does_not_run_rule_detection_logic() -> None:
    import graph_aml.alerts.persistence as persistence

    assert not hasattr(persistence, "detect_structuring")
