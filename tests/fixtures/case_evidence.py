"""In-memory fixtures for case evidence tests."""

import pandas as pd

from graph_aml.cases import CaseEvidenceBuildResult, build_case_evidence_packs


def evidence_inputs() -> dict[str, pd.DataFrame]:
    cases = pd.DataFrame(
        [
            {
                "case_id": "CASE_001",
                "case_version": "case_generation_v1",
                "primary_account_id": "ACC_001",
                "primary_customer_id": "CUST_001",
                "related_accounts": ["ACC_001", "ACC_002"],
                "alert_ids": ["ALERT_001", "ALERT_002"],
                "typologies": ["structuring", "circular_flow"],
                "rule_names": ["Structuring", "Circular flow"],
                "alert_count": 2,
                "severity": "high",
                "status": "New",
                "priority_score": 82.0,
            }
        ]
    )
    case_alerts = pd.DataFrame(
        [
            {"case_id": "CASE_001", "alert_id": "ALERT_001"},
            {"case_id": "CASE_001", "alert_id": "ALERT_002"},
        ]
    )
    alerts = pd.DataFrame(
        [
            {
                "alert_id": "ALERT_001",
                "account_id": "ACC_001",
                "rule_name": "Structuring",
                "typology": "structuring",
                "severity": "high",
                "risk_score_rule": 85.0,
                "reason_code": "STRUCTURING_BELOW_THRESHOLD",
                "evidence_ids": ["TXN_001", "TXN_002"],
                "created_at": "2026-01-01T10:00:00Z",
            },
            {
                "alert_id": "ALERT_002",
                "account_id": "ACC_002",
                "rule_name": "Circular flow",
                "typology": "circular_flow",
                "severity": "critical",
                "risk_score_rule": 95.0,
                "reason_code": "CIRCULAR_FLOW_CHAIN",
                "evidence_ids": ["TXN_002"],
                "created_at": "2026-01-01T11:00:00Z",
            },
        ]
    )
    transactions = pd.DataFrame(
        [
            {
                "transaction_id": "TXN_001",
                "transaction_timestamp": "2026-01-01T09:00:00Z",
                "sender_account_id": "ACC_001",
                "receiver_account_id": "ACC_002",
                "counterparty_id": "CP_001",
                "amount": 900.0,
                "currency": "USD",
                "transaction_type": "transfer",
                "channel": "online",
                "country_code": "US",
            },
            {
                "transaction_id": "TXN_002",
                "transaction_timestamp": "2026-01-01T09:05:00Z",
                "sender_account_id": "ACC_002",
                "receiver_account_id": "ACC_001",
                "counterparty_id": "CP_002",
                "amount": 1250.0,
                "currency": "USD",
                "transaction_type": "transfer",
                "channel": "online",
                "country_code": "US",
            },
        ]
    )
    account_risk_scores = pd.DataFrame(
        [
            {
                "account_id": "ACC_001",
                "account_risk_score": 88.0,
                "risk_band": "high",
                "risk_rank": 1,
            },
            {
                "account_id": "ACC_002",
                "account_risk_score": 76.0,
                "risk_band": "high",
                "risk_rank": 2,
            },
        ]
    )
    case_risk_scores = pd.DataFrame(
        [
            {
                "case_id": "CASE_001",
                "case_risk_score": 91.0,
                "risk_band": "critical",
                "alert_risk_score": 90.0,
                "account_risk_score": 82.0,
                "graph_risk_score": 76.0,
                "anomaly_risk_score": 80.0,
                "typology_diversity_score": 50.0,
                "evidence_value_score": 75.0,
            }
        ]
    )
    graph_features = pd.DataFrame(
        [
            {
                "account_id": "ACC_001",
                "pagerank_score": 0.4,
                "degree_centrality": 0.7,
                "betweenness_centrality": 0.2,
                "community_id": "COMM_001",
                "community_size": 5,
                "cycle_count": 1,
                "high_risk_alert_count": 2,
                "shortest_path_to_flagged": 1,
                "fan_in_count": 2,
                "fan_out_count": 3,
                "neighbour_account_count": 4,
            }
        ]
    )
    anomaly_scores = pd.DataFrame(
        [{"account_id": "ACC_001", "anomaly_score": 93.0, "risk_band": "high", "anomaly_rank": 1}]
    )
    return {
        "cases": cases,
        "case_alerts": case_alerts,
        "case_entities": pd.DataFrame(),
        "alerts": alerts,
        "transactions": transactions,
        "account_risk_scores": account_risk_scores,
        "case_risk_scores": case_risk_scores,
        "graph_features": graph_features,
        "anomaly_scores": anomaly_scores,
    }


def evidence_result() -> CaseEvidenceBuildResult:
    return build_case_evidence_packs(evidence_inputs())
