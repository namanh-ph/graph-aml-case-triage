"""Formal documentation metadata for deterministic AML rules."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, cast

from graph_aml.alerts.schema import ALERT_COLUMNS
from graph_aml.rules.circular_flow import CircularFlowDetectionConfig, CircularFlowRuleConfig
from graph_aml.rules.dormant_reactivation import DormantReactivationRuleConfig
from graph_aml.rules.exceptions import RuleDocumentationError, RuleRegistryError
from graph_aml.rules.fan_in import FanInRuleConfig
from graph_aml.rules.fan_out import FanOutRuleConfig
from graph_aml.rules.rapid_movement import RapidMovementRuleConfig
from graph_aml.rules.registry import (
    DEFAULT_RULE_ORDER,
    RULE_CIRCULAR_FLOW,
    RULE_DORMANT_REACTIVATION,
    RULE_FAN_IN,
    RULE_FAN_OUT,
    RULE_RAPID_MOVEMENT,
    RULE_STRUCTURING,
    normalise_rule_key,
    validate_rule_keys,
)
from graph_aml.rules.structuring import StructuringRuleConfig


@dataclass(frozen=True)
class RuleThresholdDoc:
    name: str
    default_value: object
    description: str
    rationale: str
    tuning_guidance: str
    config_path: str


@dataclass(frozen=True)
class RuleEvidenceDoc:
    evidence_type: str
    description: str
    example: str
    source_columns: tuple[str, ...]


@dataclass(frozen=True)
class RuleLimitationDoc:
    limitation: str
    mitigation: str


@dataclass(frozen=True)
class RuleDocumentation:
    rule_key: str
    rule_name: str
    typology: str
    business_purpose: str
    detection_logic: str
    input_tables: tuple[str, ...]
    required_columns: tuple[str, ...]
    thresholds: tuple[RuleThresholdDoc, ...]
    alert_fields: tuple[str, ...]
    reason_code_format: str
    evidence: tuple[RuleEvidenceDoc, ...]
    scoring_logic: str
    example_scenario: str
    example_alert: dict[str, object]
    limitations: tuple[RuleLimitationDoc, ...]
    validation_tests: tuple[str, ...]
    operational_notes: tuple[str, ...] = field(default_factory=tuple)


REQUIRED_RULE_DOCUMENTATION_SECTIONS = (
    "business_purpose",
    "detection_logic",
    "input_tables",
    "required_columns",
    "thresholds",
    "alert_fields",
    "reason_code_format",
    "evidence",
    "scoring_logic",
    "example_scenario",
    "example_alert",
    "limitations",
    "validation_tests",
)

EXAMPLE_ALERT_REQUIRED_FIELDS = (
    "alert_id",
    "account_id",
    "customer_id",
    "rule_name",
    "typology",
    "severity",
    "risk_score_rule",
    "reason_code",
    "evidence_ids",
    "detection_window_start",
    "detection_window_end",
)


def build_structuring_rule_documentation() -> RuleDocumentation:
    config = StructuringRuleConfig()
    return RuleDocumentation(
        rule_key=RULE_STRUCTURING,
        rule_name=config.rule_name,
        typology=config.typology,
        business_purpose=(
            "Identify repeated below-threshold outbound transfers designed to avoid "
            "currency transaction reporting thresholds."
        ),
        detection_logic=(
            "Multiple outbound transfers below the reporting threshold are grouped by account "
            "inside a rolling 24-hour window by default. Candidate evidence is retained when "
            "the count threshold is met."
        ),
        input_tables=("staging.transactions", "staging.accounts"),
        required_columns=(
            "transaction_id",
            "sender_account_id",
            "counterparty_id",
            "transaction_timestamp",
            "amount",
            "transaction_type",
        ),
        thresholds=_thresholds(
            RULE_STRUCTURING,
            (
                _threshold(
                    "reporting_threshold", config.reporting_threshold, "Upper reporting amount."
                ),
                _threshold(
                    "below_threshold_margin", config.below_threshold_margin, "Below-threshold band."
                ),
                _threshold(
                    "min_transaction_count", config.min_transaction_count, "Minimum transfers."
                ),
                _threshold("window_hours", config.window_hours, "Rolling detection window."),
                _threshold(
                    "transaction_types", config.transaction_types, "Eligible transaction types."
                ),
                _threshold(
                    "include_counterparty_payments",
                    config.include_counterparty_payments,
                    "Whether counterparty payments are candidates.",
                ),
                _threshold("base_risk_score", config.base_risk_score, "Standard alert score."),
                _threshold(
                    "high_count_risk_score", config.high_count_risk_score, "Elevated count score."
                ),
                _threshold(
                    "high_count_multiplier", config.high_count_multiplier, "High-count multiplier."
                ),
            ),
        ),
        alert_fields=tuple(ALERT_COLUMNS),
        reason_code_format="8 transfers below threshold within 24 hours",
        evidence=(
            RuleEvidenceDoc(
                "transaction_ids",
                "Transaction IDs for below-threshold transfers inside the detection window.",
                "TXN_STR_001, TXN_STR_002, TXN_STR_003",
                ("transaction_id", "sender_account_id", "transaction_timestamp", "amount"),
            ),
        ),
        scoring_logic=(
            "Use the base rule score unless the transfer count reaches the configured high-count "
            "multiplier, then use the high-count score."
        ),
        example_scenario=(
            "An account sends eight 9,500 USD transfers to external counterparties within 24 hours."
        ),
        example_alert=_example_alert(
            "ALERT_STRUCTURING_EXAMPLE",
            "ACC_STRUCTURING_001",
            config.rule_name,
            config.typology,
            config.severity,
            config.base_risk_score,
            "8 transfers below threshold within 24 hours",
        ),
        limitations=(
            RuleLimitationDoc(
                "Threshold calibration depends on jurisdiction.",
                "Tune thresholds by market, product, and local reporting obligation.",
            ),
            RuleLimitationDoc(
                "Cash deposits and transfers may need different thresholds in a real system.",
                "Split typology variants or add channel-specific parameters later.",
            ),
            RuleLimitationDoc(
                "Reference data may produce cleaner patterns than production banking data.",
                "Validate against noisy production-like backtests before deployment.",
            ),
        ),
        validation_tests=(
            "tests/test_structuring_rule.py",
            "tests/test_structuring_rule_fixtures_thresholds.py",
            "tests/test_structuring_rule_scenario_alignment.py",
        ),
        operational_notes=(
            "Review account type and expected cash activity before analyst escalation.",
            "Repeated false positives should feed jurisdiction-specific threshold tuning.",
        ),
    )


def build_fan_in_rule_documentation() -> RuleDocumentation:
    config = FanInRuleConfig()
    return RuleDocumentation(
        rule_key=RULE_FAN_IN,
        rule_name=config.rule_name,
        typology=config.typology,
        business_purpose="Identify collection accounts receiving funds from many unique senders.",
        detection_logic=(
            "Many unique sender accounts transfer into one receiving account within a rolling "
            "seven-day window by default."
        ),
        input_tables=("staging.transactions", "staging.accounts"),
        required_columns=(
            "transaction_id",
            "sender_account_id",
            "receiver_account_id",
            "transaction_timestamp",
            "amount",
            "transaction_type",
        ),
        thresholds=_thresholds(
            RULE_FAN_IN,
            (
                _threshold(
                    "min_unique_senders", config.min_unique_senders, "Minimum unique senders."
                ),
                _threshold("window_days", config.window_days, "Rolling detection window."),
                _threshold(
                    "min_total_amount", config.min_total_amount, "Minimum total received value."
                ),
                _threshold(
                    "transaction_types", config.transaction_types, "Eligible transaction types."
                ),
                _threshold(
                    "include_internal_account_receipts",
                    config.include_internal_account_receipts,
                    "Whether internal account receipts qualify.",
                ),
                _threshold("base_risk_score", config.base_risk_score, "Standard alert score."),
                _threshold(
                    "high_sender_risk_score",
                    config.high_sender_risk_score,
                    "Elevated sender score.",
                ),
                _threshold(
                    "high_sender_multiplier",
                    config.high_sender_multiplier,
                    "High-sender multiplier.",
                ),
            ),
        ),
        alert_fields=tuple(ALERT_COLUMNS),
        reason_code_format="15 unique senders within 7 days",
        evidence=(
            RuleEvidenceDoc(
                "transaction_ids",
                "Transaction IDs from sender accounts into the receiving account.",
                "TXN_FI_001, TXN_FI_002",
                ("transaction_id", "sender_account_id", "receiver_account_id"),
            ),
            RuleEvidenceDoc(
                "sender_ids",
                "Unique sending account IDs used to support the sender-count threshold.",
                "ACC_SRC_001, ACC_SRC_002",
                ("sender_account_id",),
            ),
        ),
        scoring_logic=(
            "Use the base score unless unique sender count reaches the configured multiplier, "
            "then use the high-sender score."
        ),
        example_scenario=(
            "A receiving account collects transfers from 15 unrelated senders in 7 days."
        ),
        example_alert=_example_alert(
            "ALERT_FAN_IN_EXAMPLE",
            "ACC_COLLECTION_001",
            config.rule_name,
            config.typology,
            config.severity,
            config.base_risk_score,
            "15 unique senders within 7 days",
        ),
        limitations=(
            RuleLimitationDoc(
                "High-volume merchant accounts may produce benign fan-in patterns.",
                "Incorporate merchant, charity, and platform-account segment context.",
            ),
            RuleLimitationDoc(
                "Customer segment and account type should be incorporated in later tuning.",
                "Use profile and feature tables for segment-aware suppression.",
            ),
            RuleLimitationDoc(
                "Duplicate senders should not inflate unique sender counts.",
                "Continue using canonical sender account IDs and identity resolution.",
            ),
        ),
        validation_tests=(
            "tests/test_fan_in_rule.py",
            "tests/test_fan_in_rule_fixtures.py",
            "tests/test_fan_flow_rule_separation.py",
        ),
        operational_notes=(
            "Compare sender geographies and customer relationships during review.",
            "Monitor merchant-account false positives separately from personal accounts.",
        ),
    )


def build_fan_out_rule_documentation() -> RuleDocumentation:
    config = FanOutRuleConfig()
    return RuleDocumentation(
        rule_key=RULE_FAN_OUT,
        rule_name=config.rule_name,
        typology=config.typology,
        business_purpose="Identify dispersion accounts sending funds to many unique recipients.",
        detection_logic=(
            "One sending account transfers to many unique recipients within a rolling seven-day "
            "window by default."
        ),
        input_tables=("staging.transactions", "staging.accounts"),
        required_columns=(
            "transaction_id",
            "sender_account_id",
            "receiver_account_id",
            "counterparty_id",
            "transaction_timestamp",
            "amount",
            "transaction_type",
        ),
        thresholds=_thresholds(
            RULE_FAN_OUT,
            (
                _threshold(
                    "min_unique_recipients", config.min_unique_recipients, "Minimum recipients."
                ),
                _threshold("window_days", config.window_days, "Rolling detection window."),
                _threshold(
                    "min_total_amount", config.min_total_amount, "Minimum total sent value."
                ),
                _threshold(
                    "transaction_types", config.transaction_types, "Eligible transaction types."
                ),
                _threshold(
                    "include_counterparties",
                    config.include_counterparties,
                    "Include external recipients.",
                ),
                _threshold(
                    "include_internal_accounts",
                    config.include_internal_accounts,
                    "Include internal recipients.",
                ),
                _threshold("base_risk_score", config.base_risk_score, "Standard alert score."),
                _threshold(
                    "high_recipient_risk_score",
                    config.high_recipient_risk_score,
                    "Elevated recipient score.",
                ),
                _threshold(
                    "high_recipient_multiplier",
                    config.high_recipient_multiplier,
                    "High-recipient multiplier.",
                ),
            ),
        ),
        alert_fields=tuple(ALERT_COLUMNS),
        reason_code_format="20 unique recipients within 7 days",
        evidence=(
            RuleEvidenceDoc(
                "transaction_ids",
                (
                    "Transaction IDs from sending account to distinct recipient accounts or "
                    "counterparties."
                ),
                "TXN_FO_001, TXN_FO_002",
                ("transaction_id", "sender_account_id", "receiver_account_id", "counterparty_id"),
            ),
            RuleEvidenceDoc(
                "recipient_ids",
                "Recipient keys derived from receiver account IDs or counterparty IDs.",
                "ACC_RECIPIENT_001, CP_EXT_001",
                ("receiver_account_id", "counterparty_id"),
            ),
        ),
        scoring_logic=(
            "Use the base score unless unique recipient count reaches the configured multiplier, "
            "then use the high-recipient score."
        ),
        example_scenario="A sending account distributes funds to 20 recipients over one week.",
        example_alert=_example_alert(
            "ALERT_FAN_OUT_EXAMPLE",
            "ACC_DISPERSION_001",
            config.rule_name,
            config.typology,
            config.severity,
            config.base_risk_score,
            "20 unique recipients within 7 days",
        ),
        limitations=(
            RuleLimitationDoc(
                "Payroll or marketplace payout accounts may produce benign fan-out patterns.",
                "Use account purpose and customer segment controls in later tuning.",
            ),
            RuleLimitationDoc(
                "Counterparty quality and customer segment should be reviewed in later versions.",
                "Join risk-rated counterparty and customer profile features when available.",
            ),
            RuleLimitationDoc(
                "Recipient identity resolution may affect unique recipient counts.",
                "Improve recipient entity resolution before production deployment.",
            ),
        ),
        validation_tests=(
            "tests/test_fan_out_rule.py",
            "tests/test_fan_out_rule_fixtures.py",
            "tests/test_fan_flow_counterparty_handling.py",
        ),
        operational_notes=(
            "Validate whether the account has expected payout or payroll activity.",
            "Review recipient clustering and repeated recipient names where available.",
        ),
    )


def build_rapid_movement_rule_documentation() -> RuleDocumentation:
    config = RapidMovementRuleConfig()
    return RuleDocumentation(
        rule_key=RULE_RAPID_MOVEMENT,
        rule_name=config.rule_name,
        typology=config.typology,
        business_purpose=(
            "Identify pass-through accounts where incoming funds quickly leave the account."
        ),
        detection_logic=(
            "Aggregate inbound value and outbound value inside a configurable outflow window, "
            "then flag high outflow ratio and low retained value."
        ),
        input_tables=("staging.transactions", "staging.accounts"),
        required_columns=(
            "transaction_id",
            "sender_account_id",
            "receiver_account_id",
            "counterparty_id",
            "transaction_timestamp",
            "amount",
            "transaction_type",
        ),
        thresholds=_thresholds(
            RULE_RAPID_MOVEMENT,
            (
                _threshold(
                    "outflow_window_hours", config.outflow_window_hours, "Pass-through window."
                ),
                _threshold(
                    "min_total_received", config.min_total_received, "Minimum inbound value."
                ),
                _threshold(
                    "min_outflow_ratio", config.min_outflow_ratio, "Minimum outbound ratio."
                ),
                _threshold(
                    "max_retained_ratio", config.max_retained_ratio, "Maximum retained ratio."
                ),
                _threshold(
                    "min_outgoing_transaction_count",
                    config.min_outgoing_transaction_count,
                    "Minimum outgoing transaction count.",
                ),
                _threshold(
                    "inbound_transaction_types", config.inbound_transaction_types, "Inbound types."
                ),
                _threshold(
                    "outbound_transaction_types",
                    config.outbound_transaction_types,
                    "Outbound types.",
                ),
                _threshold(
                    "include_counterparty_outflows",
                    config.include_counterparty_outflows,
                    "Include external counterparty outflows.",
                ),
                _threshold(
                    "include_internal_account_outflows",
                    config.include_internal_account_outflows,
                    "Include internal account outflows.",
                ),
                _threshold("base_risk_score", config.base_risk_score, "Standard alert score."),
                _threshold(
                    "high_ratio_risk_score", config.high_ratio_risk_score, "Elevated ratio score."
                ),
                _threshold(
                    "high_ratio_threshold", config.high_ratio_threshold, "High-ratio threshold."
                ),
            ),
        ),
        alert_fields=tuple(ALERT_COLUMNS),
        reason_code_format="90 percent of received value sent out within 48 hours",
        evidence=(
            RuleEvidenceDoc(
                "inbound_transaction_ids",
                "Inbound transaction IDs inside the pass-through detection window.",
                "TXN_RM_IN_001",
                ("transaction_id", "receiver_account_id", "amount"),
            ),
            RuleEvidenceDoc(
                "outbound_transaction_ids",
                "Outbound transaction IDs following the inbound activity inside the same window.",
                "TXN_RM_OUT_001",
                ("transaction_id", "sender_account_id", "receiver_account_id", "counterparty_id"),
            ),
        ),
        scoring_logic=(
            "Use the base score for standard detections and the high-ratio score when the "
            "outflow ratio reaches the configured high-ratio threshold."
        ),
        example_scenario="An account receives 10,000 USD and sends out 9,200 USD within 48 hours.",
        example_alert=_example_alert(
            "ALERT_RAPID_MOVEMENT_EXAMPLE",
            "ACC_PASS_THROUGH_001",
            config.rule_name,
            config.typology,
            config.severity,
            config.base_risk_score,
            "90 percent of received value sent out within 48 hours",
        ),
        limitations=(
            RuleLimitationDoc(
                "Legitimate settlement accounts can have high pass-through ratios.",
                "Add product, account purpose, and customer segment context.",
            ),
            RuleLimitationDoc(
                "Balance data would improve retained-value interpretation.",
                "Incorporate balance snapshots or available-balance features later.",
            ),
            RuleLimitationDoc(
                "Time-zone and business-day handling should be reviewed before production use.",
                "Align timestamp handling to operational calendars and branch jurisdictions.",
            ),
        ),
        validation_tests=(
            "tests/test_rapid_movement_rule.py",
            "tests/test_rapid_movement_window_detection.py",
            "tests/test_movement_dormancy_rapid_thresholds.py",
        ),
        operational_notes=(
            "Review inbound source and outbound destination relationship before escalation.",
            "Segment settlement-like accounts separately during threshold tuning.",
        ),
    )


def build_dormant_reactivation_rule_documentation() -> RuleDocumentation:
    config = DormantReactivationRuleConfig()
    return RuleDocumentation(
        rule_key=RULE_DORMANT_REACTIVATION,
        rule_name=config.rule_name,
        typology=config.typology,
        business_purpose=(
            "Identify long-inactive accounts that suddenly resume high-value outbound activity."
        ),
        detection_logic=(
            "Find prior account activity, measure dormant days, then aggregate qualifying outbound "
            "reactivation transactions inside the reactivation window."
        ),
        input_tables=("staging.transactions", "staging.accounts"),
        required_columns=(
            "transaction_id",
            "sender_account_id",
            "receiver_account_id",
            "counterparty_id",
            "transaction_timestamp",
            "amount",
            "transaction_type",
        ),
        thresholds=_thresholds(
            RULE_DORMANT_REACTIVATION,
            (
                _threshold(
                    "dormant_days_threshold", config.dormant_days_threshold, "Dormancy period."
                ),
                _threshold(
                    "reactivation_window_days",
                    config.reactivation_window_days,
                    "Reactivation window.",
                ),
                _threshold(
                    "min_outbound_amount", config.min_outbound_amount, "Minimum outbound amount."
                ),
                _threshold(
                    "min_total_outbound_amount",
                    config.min_total_outbound_amount,
                    "Minimum total outbound amount.",
                ),
                _threshold(
                    "min_outbound_transaction_count",
                    config.min_outbound_transaction_count,
                    "Minimum outbound count.",
                ),
                _threshold(
                    "outbound_transaction_types",
                    config.outbound_transaction_types,
                    "Outbound types.",
                ),
                _threshold(
                    "include_counterparty_outflows",
                    config.include_counterparty_outflows,
                    "Include external counterparty outflows.",
                ),
                _threshold(
                    "include_internal_account_outflows",
                    config.include_internal_account_outflows,
                    "Include internal account outflows.",
                ),
                _threshold("base_risk_score", config.base_risk_score, "Standard alert score."),
                _threshold(
                    "high_value_risk_score", config.high_value_risk_score, "High-value score."
                ),
                _threshold(
                    "high_value_multiplier", config.high_value_multiplier, "High-value multiplier."
                ),
            ),
        ),
        alert_fields=tuple(ALERT_COLUMNS),
        reason_code_format="120 inactive days followed by 10000.00 outbound value within 7 days",
        evidence=(
            RuleEvidenceDoc(
                "prior_activity_transaction_id",
                "Prior activity transaction ID establishing observable account history.",
                "TXN_DR_PRIOR_001",
                ("transaction_id", "sender_account_id", "receiver_account_id"),
            ),
            RuleEvidenceDoc(
                "reactivation_outbound_transaction_ids",
                "Outbound reactivation transaction IDs inside the reactivation window.",
                "TXN_DR_REACT_001",
                ("transaction_id", "sender_account_id", "amount"),
            ),
        ),
        scoring_logic=(
            "Use the base score unless total outbound amount reaches the configured high-value "
            "multiplier, then use the high-value score."
        ),
        example_scenario=(
            "An account has no activity for 120 days, then sends 10,000 USD outbound within 7 days."
        ),
        example_alert=_example_alert(
            "ALERT_DORMANT_REACTIVATION_EXAMPLE",
            "ACC_DORMANT_001",
            config.rule_name,
            config.typology,
            config.severity,
            config.base_risk_score,
            "120 inactive days followed by 10000.00 outbound value within 7 days",
        ),
        limitations=(
            RuleLimitationDoc(
                (
                    "New accounts without observable history should not be treated as dormant "
                    "by default."
                ),
                "Require prior activity evidence before triggering.",
            ),
            RuleLimitationDoc(
                "Seasonal accounts can reactivate legitimately.",
                "Add customer profile, seasonality, and account-purpose review.",
            ),
            RuleLimitationDoc(
                "Account status and customer profile context should be added later.",
                "Join staged account status and future customer risk features.",
            ),
        ),
        validation_tests=(
            "tests/test_dormant_reactivation_rule.py",
            "tests/test_dormant_reactivation_window_detection.py",
            "tests/test_movement_dormancy_dormant_thresholds.py",
        ),
        operational_notes=(
            "Analysts should verify whether the account was closed, dormant, or simply seasonal.",
            "Review account takeover signals when rapid outbound activity appears after dormancy.",
        ),
    )


def build_circular_flow_rule_documentation() -> RuleDocumentation:
    detection = CircularFlowDetectionConfig()
    alert = CircularFlowRuleConfig(detection_config=detection)
    return RuleDocumentation(
        rule_key=RULE_CIRCULAR_FLOW,
        rule_name=alert.rule_name,
        typology=alert.typology,
        business_purpose=(
            "Identify funds returning near the origin through directed transaction cycles."
        ),
        detection_logic=(
            "Construct a directed account transaction graph, detect simple cycles within a "
            "configurable hop limit, select transaction evidence, then convert detections into "
            "AlertRecord outputs."
        ),
        input_tables=("staging.transactions", "staging.accounts"),
        required_columns=(
            "transaction_id",
            "sender_account_id",
            "receiver_account_id",
            "counterparty_id",
            "transaction_timestamp",
            "amount",
            "transaction_type",
        ),
        thresholds=_thresholds(
            RULE_CIRCULAR_FLOW,
            (
                _threshold("max_cycle_hops", detection.max_cycle_hops, "Maximum cycle length."),
                _threshold("min_cycle_hops", detection.min_cycle_hops, "Minimum cycle length."),
                _threshold("min_total_amount", detection.min_total_amount, "Minimum cycle value."),
                _threshold(
                    "max_time_span_hours", detection.max_time_span_hours, "Maximum cycle time span."
                ),
                _threshold(
                    "transaction_types", detection.transaction_types, "Eligible transaction types."
                ),
                _threshold(
                    "include_counterparty_edges",
                    detection.include_counterparty_edges,
                    "Include counterparty edges.",
                ),
                _threshold(
                    "include_self_loops", detection.include_self_loops, "Include self-loop edges."
                ),
                _threshold(
                    "max_cycles_per_account",
                    detection.max_cycles_per_account,
                    "Per-account cycle cap.",
                ),
                _threshold("max_total_cycles", detection.max_total_cycles, "Total cycle cap."),
                _threshold("severity", alert.severity, "Alert severity.", section="alert"),
                _threshold(
                    "base_risk_score",
                    alert.base_risk_score,
                    "Standard alert score.",
                    section="alert",
                ),
                _threshold(
                    "high_amount_risk_score",
                    alert.high_amount_risk_score,
                    "High-amount alert score.",
                    section="alert",
                ),
                _threshold(
                    "high_amount_threshold",
                    alert.high_amount_threshold,
                    "High-amount score threshold.",
                    section="alert",
                ),
                _threshold(
                    "long_cycle_risk_score",
                    alert.long_cycle_risk_score,
                    "Long-cycle alert score.",
                    section="alert",
                ),
                _threshold(
                    "long_cycle_hop_threshold",
                    alert.long_cycle_hop_threshold,
                    "Long-cycle hop threshold.",
                    section="alert",
                ),
            ),
        ),
        alert_fields=tuple(ALERT_COLUMNS),
        reason_code_format="4-account circular flow with 25000.00 total value over 36.0 hours",
        evidence=(
            RuleEvidenceDoc(
                "cycle_transaction_ids",
                "Transaction IDs along the directed cycle path.",
                "TXN_CF_001, TXN_CF_002, TXN_CF_003, TXN_CF_004",
                ("transaction_id", "sender_account_id", "receiver_account_id"),
            ),
            RuleEvidenceDoc(
                "cycle_path",
                "Canonical directed account path used for analyst review.",
                "ACC_A -> ACC_B -> ACC_C -> ACC_A",
                ("sender_account_id", "receiver_account_id"),
            ),
        ),
        scoring_logic=(
            "Use the base score by default, the high-amount score when total cycle value reaches "
            "the high-amount threshold, and the long-cycle score when cycle length reaches the "
            "long-cycle hop threshold. If multiple elevated conditions apply, use the maximum "
            "score."
        ),
        example_scenario=(
            "Four accounts transfer value around a directed loop and return funds near the origin "
            "within 36 hours."
        ),
        example_alert=_example_alert(
            "ALERT_CIRCULAR_FLOW_EXAMPLE",
            "ACC_CF_A",
            alert.rule_name,
            alert.typology,
            alert.severity,
            alert.base_risk_score,
            "4-account circular flow with 25000.00 total value over 36.0 hours",
        ),
        limitations=(
            RuleLimitationDoc(
                "Cycle detection over reference data may be cleaner than production flow networks.",
                "Backtest against noisy transaction networks before production deployment.",
            ),
            RuleLimitationDoc(
                "Multi-edge transaction evidence may require additional analyst summarisation.",
                "Add graph evidence summaries and rollups in later documentation artefacts.",
            ),
            RuleLimitationDoc(
                "Neo4j graph evidence and community context will be added later.",
                "Integrate graph database paths and community metrics in future tickets.",
            ),
        ),
        validation_tests=(
            "tests/test_circular_flow_detection.py",
            "tests/test_circular_flow_alerts.py",
            "tests/test_circular_flow_rule.py",
        ),
        operational_notes=(
            "Review whether cycle participants share customers, devices, or counterparties.",
            "Use detection artefacts to explain cycle path and transaction evidence.",
        ),
    )


def get_rule_documentation_registry() -> dict[str, RuleDocumentation]:
    docs = (
        build_structuring_rule_documentation(),
        build_fan_in_rule_documentation(),
        build_fan_out_rule_documentation(),
        build_rapid_movement_rule_documentation(),
        build_dormant_reactivation_rule_documentation(),
        build_circular_flow_rule_documentation(),
    )
    return {doc.rule_key: doc for doc in docs}


def get_rule_documentation(rule_key: str) -> RuleDocumentation:
    try:
        normalised = normalise_rule_key(rule_key)
    except RuleRegistryError:
        raise
    registry = get_rule_documentation_registry()
    try:
        return registry[normalised]
    except KeyError as exc:
        raise RuleDocumentationError(f"Rule documentation not found: {rule_key}") from exc


def build_all_rule_documentation(
    rule_keys: tuple[str, ...] | list[str] | None = None,
) -> tuple[RuleDocumentation, ...]:
    selected = validate_rule_keys(rule_keys) if rule_keys is not None else DEFAULT_RULE_ORDER
    return tuple(get_rule_documentation(rule_key) for rule_key in selected)


def validate_rule_documentation(documentation: RuleDocumentation) -> None:
    missing = _missing_sections(documentation)
    if missing:
        raise RuleDocumentationError(
            f"{documentation.rule_key} is missing documentation sections: {missing}"
        )
    for field_name in (
        "business_purpose",
        "detection_logic",
        "reason_code_format",
        "scoring_logic",
        "example_scenario",
    ):
        if not str(getattr(documentation, field_name)).strip():
            raise RuleDocumentationError(f"{documentation.rule_key}.{field_name} is required")
    if not documentation.validation_tests:
        raise RuleDocumentationError(f"{documentation.rule_key} validation_tests are required")
    if not documentation.thresholds:
        raise RuleDocumentationError(f"{documentation.rule_key} threshold docs are required")
    for threshold in documentation.thresholds:
        if threshold.default_value is None:
            raise RuleDocumentationError(
                f"{documentation.rule_key}.{threshold.name} threshold default value is required"
            )
        if not all(
            str(value).strip()
            for value in (
                threshold.name,
                threshold.description,
                threshold.rationale,
                threshold.tuning_guidance,
                threshold.config_path,
            )
        ):
            raise RuleDocumentationError(
                f"{documentation.rule_key}.{threshold.name} threshold documentation is incomplete"
            )
    if not documentation.evidence:
        raise RuleDocumentationError(f"{documentation.rule_key} evidence docs are required")
    for evidence in documentation.evidence:
        if (
            not all(
                str(value).strip()
                for value in (
                    evidence.evidence_type,
                    evidence.description,
                    evidence.example,
                )
            )
            or not evidence.source_columns
        ):
            raise RuleDocumentationError(
                f"{documentation.rule_key}.{evidence.evidence_type} evidence documentation is "
                "incomplete"
            )
    if not documentation.limitations:
        raise RuleDocumentationError(f"{documentation.rule_key} limitations are required")
    for limitation in documentation.limitations:
        if not str(limitation.limitation).strip() or not str(limitation.mitigation).strip():
            raise RuleDocumentationError(
                f"{documentation.rule_key} limitation documentation is incomplete"
            )
    missing_alert_fields = [
        field_name
        for field_name in EXAMPLE_ALERT_REQUIRED_FIELDS
        if field_name not in documentation.example_alert
    ]
    if missing_alert_fields:
        raise RuleDocumentationError(
            f"{documentation.rule_key} example alert is missing fields: {missing_alert_fields}"
        )


def validate_all_rule_documentation(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
) -> None:
    for documentation in docs:
        validate_rule_documentation(documentation)
    missing_rules = [
        rule_key
        for rule_key in DEFAULT_RULE_ORDER
        if rule_key not in {doc.rule_key for doc in docs}
    ]
    if missing_rules:
        raise RuleDocumentationError(f"Missing rule documentation: {missing_rules}")


def check_rule_documentation_coverage(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
) -> dict[str, object]:
    for documentation in docs:
        validate_rule_documentation(documentation)
    documented = tuple(doc.rule_key for doc in docs)
    missing_sections = {doc.rule_key: _missing_sections(doc) for doc in docs}
    missing_sections = {
        rule_key: sections for rule_key, sections in missing_sections.items() if sections
    }
    return {
        "rule_count": len(docs),
        "rules_documented": list(documented),
        "missing_rules": [
            rule_key for rule_key in DEFAULT_RULE_ORDER if rule_key not in documented
        ],
        "missing_sections": missing_sections,
        "threshold_count": sum(len(doc.thresholds) for doc in docs),
        "evidence_doc_count": sum(len(doc.evidence) for doc in docs),
        "limitation_count": sum(len(doc.limitations) for doc in docs),
    }


def rule_documentation_to_dict(documentation: RuleDocumentation) -> dict[str, object]:
    validate_rule_documentation(documentation)
    return cast(dict[str, object], _json_ready(asdict(documentation)))


def rule_documentation_from_dict(payload: dict[str, object]) -> RuleDocumentation:
    try:
        thresholds = tuple(
            RuleThresholdDoc(
                name=str(cast(dict[str, object], item)["name"]),
                default_value=_tuple_ready(cast(dict[str, object], item)["default_value"]),
                description=str(cast(dict[str, object], item)["description"]),
                rationale=str(cast(dict[str, object], item)["rationale"]),
                tuning_guidance=str(cast(dict[str, object], item)["tuning_guidance"]),
                config_path=str(cast(dict[str, object], item)["config_path"]),
            )
            for item in cast(list[object], payload["thresholds"])
        )
        evidence = tuple(
            RuleEvidenceDoc(
                evidence_type=str(cast(dict[str, object], item)["evidence_type"]),
                description=str(cast(dict[str, object], item)["description"]),
                example=str(cast(dict[str, object], item)["example"]),
                source_columns=tuple(
                    str(value)
                    for value in cast(
                        list[object],
                        cast(dict[str, object], item)["source_columns"],
                    )
                ),
            )
            for item in cast(list[object], payload["evidence"])
        )
        limitations = tuple(
            RuleLimitationDoc(
                limitation=str(cast(dict[str, object], item)["limitation"]),
                mitigation=str(cast(dict[str, object], item)["mitigation"]),
            )
            for item in cast(list[object], payload["limitations"])
        )
        documentation = RuleDocumentation(
            rule_key=str(payload["rule_key"]),
            rule_name=str(payload["rule_name"]),
            typology=str(payload["typology"]),
            business_purpose=str(payload["business_purpose"]),
            detection_logic=str(payload["detection_logic"]),
            input_tables=tuple(str(value) for value in cast(list[object], payload["input_tables"])),
            required_columns=tuple(
                str(value) for value in cast(list[object], payload["required_columns"])
            ),
            thresholds=thresholds,
            alert_fields=tuple(str(value) for value in cast(list[object], payload["alert_fields"])),
            reason_code_format=str(payload["reason_code_format"]),
            evidence=evidence,
            scoring_logic=str(payload["scoring_logic"]),
            example_scenario=str(payload["example_scenario"]),
            example_alert=cast(dict[str, object], payload["example_alert"]),
            limitations=limitations,
            validation_tests=tuple(
                str(value) for value in cast(list[object], payload["validation_tests"])
            ),
            operational_notes=tuple(
                str(value) for value in cast(list[object], payload.get("operational_notes", []))
            ),
        )
        validate_rule_documentation(documentation)
        return documentation
    except (KeyError, TypeError, ValueError, RuleDocumentationError) as exc:
        raise RuleDocumentationError(f"Invalid rule documentation payload: {exc}") from exc


def rule_documentation_collection_to_dicts(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
) -> list[dict[str, object]]:
    for documentation in docs:
        validate_rule_documentation(documentation)
    return [rule_documentation_to_dict(documentation) for documentation in docs]


def render_rule_documentation_markdown(documentation: RuleDocumentation) -> str:
    validate_rule_documentation(documentation)
    lines = [
        f"# {documentation.rule_name} Rule",
        "",
        "## Purpose",
        documentation.business_purpose,
        "",
        "## Detection Logic",
        documentation.detection_logic,
        "",
        "## Inputs",
        *_bullets(
            ("Input tables", documentation.input_tables),
            ("Required columns", documentation.required_columns),
        ),
        "",
        "## Thresholds",
        *_threshold_table(documentation.thresholds),
        "",
        "## Alert Output",
        *_bullets(("Alert fields", documentation.alert_fields)),
        "",
        "## Evidence",
        *_evidence_lines(documentation.evidence),
        "",
        "## Reason Code",
        documentation.reason_code_format,
        "",
        "## Risk Scoring",
        documentation.scoring_logic,
        "",
        "## Example Scenario",
        documentation.example_scenario,
        "",
        "## Example Alert",
        "```json",
        json.dumps(_json_ready(documentation.example_alert), indent=2, sort_keys=True),
        "```",
        "",
        "## Limitations",
        *_limitation_lines(documentation.limitations),
        "",
        "## Validation Tests",
        *_simple_bullets(documentation.validation_tests),
        "",
        "## Operational Notes",
        *_simple_bullets(documentation.operational_notes),
        "",
    ]
    return "\n".join(lines)


def render_rule_documentation_index_markdown(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
) -> str:
    for documentation in docs:
        validate_rule_documentation(documentation)
    coverage = check_rule_documentation_coverage(tuple(docs))
    lines = [
        "# AML Rule Documentation Index",
        "",
        "## Registered Rules",
        "| Rule key | Rule name | Typology | Thresholds | Evidence docs |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for doc in docs:
        lines.append(
            f"| `{doc.rule_key}` | {doc.rule_name} | `{doc.typology}` | "
            f"{len(doc.thresholds)} | {len(doc.evidence)} |"
        )
    lines.extend(
        [
            "",
            "## Rule Coverage Summary",
            f"- Rules documented: {coverage['rule_count']}",
            f"- Missing rules: {coverage['missing_rules']}",
            f"- Threshold docs: {coverage['threshold_count']}",
            f"- Evidence docs: {coverage['evidence_doc_count']}",
            f"- Limitations: {coverage['limitation_count']}",
            "",
            "## Typology Matrix",
            *_simple_bullets(tuple(f"{doc.rule_name}: `{doc.typology}`" for doc in docs)),
            "",
            "## Alert Output Contract",
            (
                "All documented rules emit the common `AlertRecord` fields and include an "
                "example alert."
            ),
            "",
            "## Documentation Artefacts",
            "- `docs/rules/aml_rule_documentation_pack.md`",
            "- `docs/rules/<rule_key>.md`",
            "- `reports/model_validation/aml_rule_documentation.json`",
            "",
        ]
    )
    return "\n".join(lines)


def render_rule_documentation_pack_markdown(
    docs: tuple[RuleDocumentation, ...] | list[RuleDocumentation],
) -> str:
    for documentation in docs:
        validate_rule_documentation(documentation)
    lines = [
        "# AML Rule Documentation Pack",
        "",
        "## Overview",
        "This pack documents the deterministic AML rules registered in the unified rule engine.",
        "",
        "## Registered Rule Matrix",
        "| Rule key | Rule name | Typology |",
        "| --- | --- | --- |",
    ]
    for doc in docs:
        lines.append(f"| `{doc.rule_key}` | {doc.rule_name} | `{doc.typology}` |")
    lines.extend(
        [
            "",
            "## Common Alert Contract",
            ", ".join(f"`{field_name}`" for field_name in ALERT_COLUMNS),
            "",
            "## Individual Rule Documentation",
            "",
        ]
    )
    for doc in docs:
        lines.append(render_rule_documentation_markdown(doc))
    return "\n".join(lines)


def _threshold(
    name: str,
    default_value: object,
    description: str,
    section: str | None = None,
) -> RuleThresholdDoc:
    section_path = f".{section}" if section else ""
    if section is None and name in {
        "max_cycle_hops",
        "min_cycle_hops",
        "min_total_amount",
        "max_time_span_hours",
        "transaction_types",
        "include_counterparty_edges",
        "include_self_loops",
        "max_cycles_per_account",
        "max_total_cycles",
    }:
        section_path = ".detection"
    return RuleThresholdDoc(
        name=name,
        default_value=default_value,
        description=description,
        rationale=f"{description} controls deterministic candidate selection or scoring.",
        tuning_guidance=(
            "Tune using historical alert review, scenario fixtures, and false-positive analysis."
        ),
        config_path=f"rules.<rule_key>{section_path}.{name}",
    )


def _thresholds(
    rule_key: str,
    thresholds: tuple[RuleThresholdDoc, ...],
) -> tuple[RuleThresholdDoc, ...]:
    return tuple(
        RuleThresholdDoc(
            name=threshold.name,
            default_value=threshold.default_value,
            description=threshold.description,
            rationale=threshold.rationale,
            tuning_guidance=threshold.tuning_guidance,
            config_path=threshold.config_path.replace("<rule_key>", rule_key),
        )
        for threshold in thresholds
    )


def _example_alert(
    alert_id: str,
    account_id: str,
    rule_name: str,
    typology: str,
    severity: str,
    risk_score: float,
    reason_code: str,
) -> dict[str, object]:
    return {
        "alert_id": alert_id,
        "account_id": account_id,
        "customer_id": f"CUST_{account_id}",
        "rule_name": rule_name,
        "typology": typology,
        "severity": severity,
        "risk_score_rule": risk_score,
        "reason_code": reason_code,
        "evidence_ids": ["TXN_EXAMPLE_001", "TXN_EXAMPLE_002"],
        "detection_window_start": "2025-01-01T00:00:00+00:00",
        "detection_window_end": "2025-01-01T23:59:59+00:00",
        "model_run_id": None,
        "alert_status": "New",
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }


def _missing_sections(documentation: RuleDocumentation) -> list[str]:
    missing: list[str] = []
    for section in REQUIRED_RULE_DOCUMENTATION_SECTIONS:
        value = getattr(documentation, section)
        if value in (None, "", (), {}, []):
            missing.append(section)
    return missing


def _json_ready(value: object) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    return value


def _tuple_ready(value: object) -> object:
    if isinstance(value, list):
        return tuple(_tuple_ready(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _tuple_ready(item) for key, item in value.items()}
    return value


def _bullets(*items: tuple[str, tuple[str, ...]]) -> list[str]:
    lines: list[str] = []
    for label, values in items:
        lines.append(f"- {label}: " + ", ".join(f"`{value}`" for value in values))
    return lines


def _simple_bullets(values: tuple[str, ...]) -> list[str]:
    return [f"- {value}" for value in values] or ["- None documented."]


def _threshold_table(thresholds: tuple[RuleThresholdDoc, ...]) -> list[str]:
    lines = [
        "| Name | Default | Description | Rationale | Tuning guidance | Config path |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for threshold in thresholds:
        lines.append(
            f"| `{threshold.name}` | `{threshold.default_value}` | {threshold.description} | "
            f"{threshold.rationale} | {threshold.tuning_guidance} | "
            f"`{threshold.config_path}` |"
        )
    return lines


def _evidence_lines(evidence: tuple[RuleEvidenceDoc, ...]) -> list[str]:
    lines: list[str] = []
    for item in evidence:
        lines.extend(
            [
                f"### {item.evidence_type}",
                item.description,
                f"- Example: `{item.example}`",
                "- Source columns: " + ", ".join(f"`{value}`" for value in item.source_columns),
                "",
            ]
        )
    return lines


def _limitation_lines(limitations: tuple[RuleLimitationDoc, ...]) -> list[str]:
    lines: list[str] = []
    for item in limitations:
        lines.append(f"- {item.limitation} Mitigation: {item.mitigation}")
    return lines
