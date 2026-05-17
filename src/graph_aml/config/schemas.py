"""Typed Pydantic schemas for YAML configuration files."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

REQUIRED_SEVERITIES = {"low", "medium", "high", "critical"}
REQUIRED_DASHBOARD_PAGES = {
    "Overview",
    "Alert Queue",
    "Case Detail",
    "Graph View",
    "Account Profile",
    "Model Metrics",
    "Audit Log",
    "Validation Report",
}


class StrictBaseModel(BaseModel):
    """Base model that rejects unrecognised configuration keys."""

    model_config = ConfigDict(extra="forbid")


class ProjectMetadataConfig(StrictBaseModel):
    name: str
    package_name: str
    version: str
    description: str
    environment: str
    random_seed: int
    timezone: str


class RuntimeConfig(StrictBaseModel):
    python_version: str
    execution_mode: str
    local_first: StrictBool


class GovernanceConfig(StrictBaseModel):
    audit_enabled: StrictBool
    model_tracking_enabled: StrictBool
    validation_reports_enabled: StrictBool
    analyst_feedback_enabled: StrictBool


class ProjectFileConfig(StrictBaseModel):
    project: ProjectMetadataConfig
    runtime: RuntimeConfig
    governance: GovernanceConfig


class PathsConfig(StrictBaseModel):
    root: str
    config_dir: str
    data_dir: str
    dataset_dir: str
    external_data_dir: str
    docs_dir: str
    reports_dir: str
    model_validation_dir: str
    notebooks_dir: str
    app_dir: str
    streamlit_pages_dir: str
    source_dir: str
    package_dir: str
    tests_dir: str
    logs_dir: str
    mlruns_dir: str


class FilesConfig(StrictBaseModel):
    env_example: str
    readme: str
    pyproject: str
    streamlit_entrypoint: str


class PathsFileConfig(StrictBaseModel):
    paths: PathsConfig
    files: FilesConfig


class PostgresDefaultsConfig(StrictBaseModel):
    host: str
    port: int = Field(gt=0, le=65535)
    database: str
    user: str


class PostgresPoolConfig(StrictBaseModel):
    pool_size: int = Field(gt=0)
    max_overflow: int = Field(ge=0)
    pool_timeout_seconds: int = Field(gt=0)
    pool_recycle_seconds: int = Field(gt=0)


class PostgresConfig(StrictBaseModel):
    enabled: StrictBool
    driver: str
    host_env: str
    port_env: str
    database_env: str
    user_env: str
    password_env: str
    defaults: PostgresDefaultsConfig
    pool: PostgresPoolConfig


class DatabaseSchemasConfig(StrictBaseModel):
    raw: str
    staging: str
    mart: str
    aml: str
    governance: str


class RawTablesConfig(StrictBaseModel):
    transactions: str
    customers: str
    accounts: str
    counterparties: str
    countries: str
    devices: str


class StagingTablesConfig(StrictBaseModel):
    transactions: str
    customers: str
    accounts: str
    counterparties: str
    countries: str
    devices: str


class MartTablesConfig(StrictBaseModel):
    features_account_daily: str
    graph_features: str
    account_anomaly_scores: str
    account_risk_scores: str


class AmlTablesConfig(StrictBaseModel):
    alerts: str
    cases: str
    case_alerts: str
    case_entities: str
    case_risk_scores: str
    case_evidence_packs: str
    case_explanations: str
    case_lifecycle_events: str
    case_assignments: str


class GovernanceTablesConfig(StrictBaseModel):
    audit_events: str
    model_runs: str
    validation_reports: str


class DatabaseTablesConfig(StrictBaseModel):
    raw: RawTablesConfig
    staging: StagingTablesConfig
    mart: MartTablesConfig
    aml: AmlTablesConfig
    governance: GovernanceTablesConfig


class DatabaseFileConfig(StrictBaseModel):
    postgres: PostgresConfig
    schemas: DatabaseSchemasConfig
    tables: DatabaseTablesConfig


class Neo4jDefaultsConfig(StrictBaseModel):
    uri: str
    user: str
    database: str


class Neo4jConnectionConfig(StrictBaseModel):
    max_connection_lifetime_seconds: int = Field(gt=0)
    max_connection_pool_size: int = Field(gt=0)
    connection_timeout_seconds: int = Field(gt=0)


class Neo4jConfig(StrictBaseModel):
    enabled: StrictBool
    uri_env: str
    user_env: str
    password_env: str
    defaults: Neo4jDefaultsConfig
    connection: Neo4jConnectionConfig


class GraphNodeLabelsConfig(StrictBaseModel):
    customer: str
    account: str
    transaction: str
    counterparty: str
    device: str
    country: str
    alert: str
    case: str


class GraphRelationshipTypesConfig(StrictBaseModel):
    owns: str
    sent: str
    received: str
    paid_to: str
    used_device: str
    located_in: str
    shares_identifier: str
    triggers: str
    included_in: str
    related_to: str


class GraphBuildConfig(StrictBaseModel):
    batch_size: int = Field(gt=0)
    reset_before_load: StrictBool
    create_constraints: StrictBool
    create_indexes: StrictBool


class GraphAnalyticsConfig(StrictBaseModel):
    calculate_degree: StrictBool
    calculate_pagerank: StrictBool
    calculate_betweenness: StrictBool
    detect_communities: StrictBool
    detect_cycles: StrictBool
    max_cycle_hops: int = Field(ge=2)


class GraphConfig(StrictBaseModel):
    node_labels: GraphNodeLabelsConfig
    relationship_types: GraphRelationshipTypesConfig
    build: GraphBuildConfig
    analytics: GraphAnalyticsConfig


class Neo4jFileConfig(StrictBaseModel):
    neo4j: Neo4jConfig
    graph: GraphConfig


class SeverityBandConfig(StrictBaseModel):
    min_score: int = Field(ge=0, le=100)
    max_score: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_range(self) -> "SeverityBandConfig":
        if self.min_score > self.max_score:
            raise ValueError("min_score must be less than or equal to max_score")
        return self


def validate_required_severity_bands(
    bands: dict[str, SeverityBandConfig],
) -> dict[str, SeverityBandConfig]:
    missing = REQUIRED_SEVERITIES - set(bands)
    if missing:
        missing_values = ", ".join(sorted(missing))
        raise ValueError(f"Missing severity bands: {missing_values}")
    return bands


class StructuringRuleConfig(StrictBaseModel):
    enabled: StrictBool
    rule_name: str
    typology: str
    reporting_threshold: float = Field(gt=0)
    below_threshold_margin: float = Field(gt=0, lt=1)
    min_transaction_count: int = Field(ge=2)
    window_hours: int = Field(gt=0)
    severity: str
    base_risk_score: float = Field(ge=0, le=100)
    high_count_risk_score: float = Field(ge=0, le=100)
    high_count_multiplier: float = Field(ge=1.0)
    transaction_types: list[str] = Field(min_length=1)
    include_counterparty_payments: StrictBool


class FanInRuleConfig(StrictBaseModel):
    enabled: StrictBool
    rule_name: str
    typology: str
    min_unique_senders: int = Field(ge=2)
    window_days: int = Field(gt=0)
    severity: str
    base_risk_score: float = Field(ge=0, le=100)
    high_sender_risk_score: float = Field(ge=0, le=100)
    high_sender_multiplier: float = Field(ge=1.0)
    min_total_amount: float = Field(ge=0)
    transaction_types: list[str] = Field(min_length=1)
    include_internal_account_receipts: StrictBool


class FanOutRuleConfig(StrictBaseModel):
    enabled: StrictBool
    rule_name: str
    typology: str
    min_unique_recipients: int = Field(ge=2)
    window_days: int = Field(gt=0)
    severity: str
    base_risk_score: float = Field(ge=0, le=100)
    high_recipient_risk_score: float = Field(ge=0, le=100)
    high_recipient_multiplier: float = Field(ge=1.0)
    min_total_amount: float = Field(ge=0)
    transaction_types: list[str] = Field(min_length=1)
    include_counterparties: StrictBool
    include_internal_accounts: StrictBool

    @model_validator(mode="after")
    def validate_recipient_sources(self) -> "FanOutRuleConfig":
        if not self.include_counterparties and not self.include_internal_accounts:
            raise ValueError("at least one fan-out recipient source must be enabled")
        return self


class RapidMovementRuleConfig(StrictBaseModel):
    enabled: StrictBool
    rule_name: str
    typology: str
    outflow_window_hours: int = Field(gt=0)
    min_total_received: float = Field(ge=0)
    min_outflow_ratio: float = Field(gt=0, le=1)
    max_retained_ratio: float = Field(ge=0, lt=1)
    min_outgoing_transaction_count: int = Field(ge=1)
    severity: str
    base_risk_score: float = Field(ge=0, le=100)
    high_ratio_risk_score: float = Field(ge=0, le=100)
    high_ratio_threshold: float = Field(gt=0, le=1)
    inbound_transaction_types: list[str] = Field(min_length=1)
    outbound_transaction_types: list[str] = Field(min_length=1)
    include_counterparty_outflows: StrictBool
    include_internal_account_outflows: StrictBool

    @model_validator(mode="after")
    def validate_rapid_movement_thresholds(self) -> "RapidMovementRuleConfig":
        if self.high_ratio_threshold < self.min_outflow_ratio:
            raise ValueError("high_ratio_threshold must be at least min_outflow_ratio")
        if not self.include_counterparty_outflows and not self.include_internal_account_outflows:
            raise ValueError("at least one rapid movement outflow source must be enabled")
        return self


class CircularFlowDetectionSettingsConfig(StrictBaseModel):
    max_cycle_hops: int = Field(ge=2)
    min_cycle_hops: int = Field(ge=2)
    min_total_amount: float = Field(ge=0)
    max_time_span_hours: int | None = Field(default=None, gt=0)
    transaction_types: list[str] = Field(min_length=1)
    include_counterparty_edges: StrictBool
    include_self_loops: StrictBool
    max_cycles_per_account: int = Field(gt=0)
    max_total_cycles: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_circular_flow_hops(self) -> "CircularFlowDetectionSettingsConfig":
        if self.max_cycle_hops < self.min_cycle_hops:
            raise ValueError("max_cycle_hops must be greater than or equal to min_cycle_hops")
        return self


class CircularFlowAlertSettingsConfig(StrictBaseModel):
    severity: str
    base_risk_score: float = Field(ge=0, le=100)
    high_amount_risk_score: float = Field(ge=0, le=100)
    high_amount_threshold: float = Field(ge=0)
    long_cycle_risk_score: float = Field(ge=0, le=100)
    long_cycle_hop_threshold: int = Field(ge=2)


class CircularFlowRuleConfig(StrictBaseModel):
    enabled: StrictBool
    rule_name: str
    typology: str
    detection: CircularFlowDetectionSettingsConfig | None = None
    alert: CircularFlowAlertSettingsConfig | None = None
    max_cycle_hops: int | None = Field(default=None, ge=2)
    min_cycle_hops: int | None = Field(default=None, ge=2)
    min_total_amount: float | None = Field(default=None, ge=0)
    max_time_span_hours: int | None = Field(default=None, gt=0)
    transaction_types: list[str] | None = None
    include_counterparty_edges: StrictBool | None = None
    include_self_loops: StrictBool | None = None
    max_cycles_per_account: int | None = Field(default=None, gt=0)
    max_total_cycles: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_circular_flow_settings(self) -> "CircularFlowRuleConfig":
        if self.detection is None:
            missing = [
                name
                for name in (
                    "max_cycle_hops",
                    "min_cycle_hops",
                    "min_total_amount",
                    "transaction_types",
                    "include_counterparty_edges",
                    "include_self_loops",
                    "max_cycles_per_account",
                    "max_total_cycles",
                )
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"missing circular flow detection settings: {missing}")
            assert self.max_cycle_hops is not None
            assert self.min_cycle_hops is not None
            assert self.min_total_amount is not None
            assert self.max_cycles_per_account is not None
            assert self.max_total_cycles is not None
            self.detection = CircularFlowDetectionSettingsConfig(
                max_cycle_hops=self.max_cycle_hops,
                min_cycle_hops=self.min_cycle_hops,
                min_total_amount=self.min_total_amount,
                max_time_span_hours=self.max_time_span_hours,
                transaction_types=self.transaction_types or [],
                include_counterparty_edges=bool(self.include_counterparty_edges),
                include_self_loops=bool(self.include_self_loops),
                max_cycles_per_account=self.max_cycles_per_account,
                max_total_cycles=self.max_total_cycles,
            )
        if self.alert is None:
            self.alert = CircularFlowAlertSettingsConfig(
                severity="high",
                base_risk_score=85.0,
                high_amount_risk_score=90.0,
                high_amount_threshold=50000.0,
                long_cycle_risk_score=90.0,
                long_cycle_hop_threshold=4,
            )
        return self


class DormantReactivationRuleConfig(StrictBaseModel):
    enabled: StrictBool
    rule_name: str
    typology: str
    dormant_days_threshold: int = Field(gt=0)
    reactivation_window_days: int = Field(gt=0)
    min_outbound_amount: float = Field(ge=0)
    min_total_outbound_amount: float = Field(ge=0)
    min_outbound_transaction_count: int = Field(ge=1)
    severity: str
    base_risk_score: float = Field(ge=0, le=100)
    high_value_risk_score: float = Field(ge=0, le=100)
    high_value_multiplier: float = Field(ge=1.0)
    outbound_transaction_types: list[str] = Field(min_length=1)
    include_counterparty_outflows: StrictBool
    include_internal_account_outflows: StrictBool

    @model_validator(mode="after")
    def validate_dormant_reactivation_sources(self) -> "DormantReactivationRuleConfig":
        if not self.include_counterparty_outflows and not self.include_internal_account_outflows:
            raise ValueError("at least one dormant reactivation outflow source must be enabled")
        return self


class RulesConfig(StrictBaseModel):
    enabled: StrictBool
    default_currency: str
    default_timezone: str
    severity_bands: dict[str, SeverityBandConfig]
    structuring: StructuringRuleConfig
    fan_in: FanInRuleConfig
    fan_out: FanOutRuleConfig
    rapid_movement: RapidMovementRuleConfig
    circular_flow: CircularFlowRuleConfig
    dormant_reactivation: DormantReactivationRuleConfig

    @field_validator("severity_bands")
    @classmethod
    def validate_severity_bands(
        cls,
        bands: dict[str, SeverityBandConfig],
    ) -> dict[str, SeverityBandConfig]:
        return validate_required_severity_bands(bands)


class RulesFileConfig(StrictBaseModel):
    rules: RulesConfig


class ScoringConfig(StrictBaseModel):
    enabled: StrictBool
    score_min: int = Field(ge=0, le=100)
    score_max: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_score_range(self) -> "ScoringConfig":
        if self.score_min > self.score_max:
            raise ValueError("score_min must be less than or equal to score_max")
        return self


class WeightedScoreConfig(StrictBaseModel):
    weights: dict[str, float]

    @model_validator(mode="after")
    def validate_weights_sum_to_one(self) -> "WeightedScoreConfig":
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"weights must sum to 1.0, got {total}")
        return self


class AccountRiskJurisdictionConfig(StrictBaseModel):
    high_risk_country_score: float = Field(ge=0, le=100)
    standard_country_score: float = Field(ge=0, le=100)
    unknown_country_score: float = Field(ge=0, le=100)


class AccountRiskCompositeConfig(StrictBaseModel):
    enabled: StrictBool
    score_name: str
    score_version: str
    weights: dict[str, float]
    severity_scores: dict[str, float]
    risk_bands: dict[str, float]
    graph_component_weights: dict[str, float]
    customer_risk_scores: dict[str, float]
    jurisdiction: AccountRiskJurisdictionConfig
    feature_date: str | None = None
    alert_lookback_days: int | None = Field(default=None, gt=0)
    graph_feature_version: str | None = None
    graph_build_id: str | None = None
    anomaly_model_version: str | None = None
    anomaly_model_run_id: str | None = None
    include_inactive_accounts: StrictBool
    min_component_coverage: float = Field(ge=0, le=1)
    artefact_output_dir: str


class CaseGroupingFileConfig(StrictBaseModel):
    group_by_account: StrictBool
    group_by_customer: StrictBool
    group_by_graph_community: StrictBool
    group_by_circular_flow: StrictBool
    group_by_common_counterparty: StrictBool
    group_by_shared_identifier: StrictBool


class CaseGenerationThresholdFileConfig(StrictBaseModel):
    min_alerts_per_case: int = Field(gt=0)
    max_alerts_per_case: int = Field(gt=0)
    max_cases_per_account: int = Field(gt=0)
    max_cases_total: int = Field(gt=0)
    lookback_days: int | None = Field(default=None, gt=0)
    min_account_risk_score: float = Field(ge=0, le=100)
    include_low_risk_accounts: StrictBool


class CaseGenerationPriorityFileConfig(StrictBaseModel):
    use_account_risk_score: StrictBool
    use_max_alert_score: StrictBool
    use_alert_count_uplift: StrictBool
    alert_count_uplift_per_alert: float = Field(ge=0)
    max_alert_count_uplift: float = Field(ge=0)


class CaseGenerationFileConfig(StrictBaseModel):
    enabled: StrictBool
    case_version: str
    default_status: str
    grouping: CaseGroupingFileConfig
    thresholds: CaseGenerationThresholdFileConfig
    severity_mapping: dict[str, str]
    priority: CaseGenerationPriorityFileConfig
    artefact_output_dir: str

    @field_validator("severity_mapping")
    @classmethod
    def validate_case_severity_mapping(cls, mapping: dict[str, str]) -> dict[str, str]:
        missing = {"low", "medium", "high", "critical"}.difference(mapping)
        if missing:
            missing_values = ", ".join(sorted(missing))
            raise ValueError(f"Missing case severity mapping: {missing_values}")
        return mapping


class CaseRiskAlertFileConfig(StrictBaseModel):
    use_max_alert_score: StrictBool
    use_mean_alert_score: StrictBool
    max_alert_weight: float = Field(ge=0)
    mean_alert_weight: float = Field(ge=0)
    severity_scores: dict[str, float]


class CaseRiskGraphFileConfig(StrictBaseModel):
    pagerank_weight: float = Field(ge=0)
    degree_weight: float = Field(ge=0)
    cycle_weight: float = Field(ge=0)
    community_size_weight: float = Field(ge=0)
    alert_proximity_weight: float = Field(ge=0)


class CaseRiskAnomalyFileConfig(StrictBaseModel):
    use_max_anomaly_score: StrictBool
    use_mean_anomaly_score: StrictBool
    max_anomaly_weight: float = Field(ge=0)
    mean_anomaly_weight: float = Field(ge=0)


class CaseRiskEvidenceFileConfig(StrictBaseModel):
    transaction_value_percentile_weight: float = Field(ge=0)
    evidence_count_percentile_weight: float = Field(ge=0)
    related_account_count_percentile_weight: float = Field(ge=0)


class CaseRiskThresholdFileConfig(StrictBaseModel):
    min_case_priority_score: float = Field(ge=0, le=100)
    min_component_coverage: float = Field(ge=0, le=1)
    max_cases_total: int = Field(gt=0)


class CaseRiskFileConfig(StrictBaseModel):
    enabled: StrictBool
    score_name: str
    score_version: str
    weights: dict[str, float]
    risk_bands: dict[str, float]
    alert: CaseRiskAlertFileConfig
    graph: CaseRiskGraphFileConfig
    anomaly: CaseRiskAnomalyFileConfig
    evidence: CaseRiskEvidenceFileConfig
    thresholds: CaseRiskThresholdFileConfig
    case_version: str | None = None
    account_risk_score_version: str | None = None
    graph_feature_version: str | None = None
    graph_build_id: str | None = None
    anomaly_model_version: str | None = None
    anomaly_model_run_id: str | None = None
    artefact_output_dir: str


class CaseEvidenceIncludeFileConfig(StrictBaseModel):
    alerts: StrictBool
    transactions: StrictBool
    risk_drivers: StrictBool
    graph_context: StrictBool
    account_context: StrictBool
    typology_context: StrictBool
    chronology: StrictBool


class CaseEvidenceLimitFileConfig(StrictBaseModel):
    max_transactions_per_case: int = Field(gt=0)
    max_alerts_per_case: int = Field(gt=0)
    max_related_accounts: int = Field(gt=0)
    max_graph_paths: int = Field(gt=0)
    max_reason_codes: int = Field(gt=0)
    max_explanation_bullets: int = Field(gt=0)


class CaseEvidenceTransactionSortingFileConfig(StrictBaseModel):
    primary: str
    secondary: str
    descending_amount: StrictBool


class CaseEvidenceRiskDriverThresholdFileConfig(StrictBaseModel):
    high_component_score: float = Field(ge=0, le=100)
    critical_component_score: float = Field(ge=0, le=100)
    high_transaction_value_percentile: float = Field(ge=0, le=100)
    high_alert_count: int = Field(gt=0)
    high_typology_count: int = Field(gt=0)


class CaseExplanationFileConfig(StrictBaseModel):
    include_case_summary: StrictBool
    include_typology_summary: StrictBool
    include_risk_driver_summary: StrictBool
    include_transaction_summary: StrictBool
    include_graph_summary: StrictBool
    include_recommended_review_focus: StrictBool


class CaseEvidenceFileConfig(StrictBaseModel):
    enabled: StrictBool
    evidence_version: str
    explanation_version: str
    include: CaseEvidenceIncludeFileConfig
    limits: CaseEvidenceLimitFileConfig
    transaction_sorting: CaseEvidenceTransactionSortingFileConfig
    risk_driver_thresholds: CaseEvidenceRiskDriverThresholdFileConfig
    explanation: CaseExplanationFileConfig
    artefact_output_dir: str


class CaseLifecycleAnalystFileConfig(StrictBaseModel):
    default_analyst_id: str
    default_queue: str
    require_decision_reason: StrictBool
    require_comment_for_closure: StrictBool


class CaseLifecycleFileConfig(StrictBaseModel):
    enabled: StrictBool
    lifecycle_version: str
    statuses: tuple[str, ...]
    terminal_statuses: tuple[str, ...]
    allowed_transitions: dict[str, tuple[str, ...]]
    decision_types: tuple[str, ...]
    analyst: CaseLifecycleAnalystFileConfig
    artefact_output_dir: str


class NormalisationConfig(StrictBaseModel):
    method: str
    clip_scores: StrictBool
    fill_missing_component_score: int = Field(ge=0, le=100)


class ScoringFileConfig(StrictBaseModel):
    scoring: ScoringConfig
    account_risk: AccountRiskCompositeConfig
    case_generation: CaseGenerationFileConfig
    case_risk: CaseRiskFileConfig
    case_evidence: CaseEvidenceFileConfig
    case_lifecycle: CaseLifecycleFileConfig
    account_risk_score: WeightedScoreConfig
    case_risk_score: WeightedScoreConfig
    severity_mapping: dict[str, SeverityBandConfig]
    normalisation: NormalisationConfig
    analyst_labels: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity_mapping")
    @classmethod
    def validate_severity_mapping(
        cls,
        bands: dict[str, SeverityBandConfig],
    ) -> dict[str, SeverityBandConfig]:
        return validate_required_severity_bands(bands)


class ModelConfig(StrictBaseModel):
    enabled: StrictBool
    random_seed: int
    model_registry_name: str
    experiment_name: str


class MlflowConfig(StrictBaseModel):
    tracking_uri_env: str
    default_tracking_uri: str


class FeaturesConfig(StrictBaseModel):
    account_features: list[str] = Field(min_length=1)
    graph_features: list[str] = Field(min_length=1)


class IsolationForestConfig(StrictBaseModel):
    enabled: StrictBool
    model_name: str
    model_version: str
    random_state: int
    n_estimators: int = Field(gt=0)
    contamination: float | str
    max_samples: str | int | float
    max_features: int | float
    bootstrap: StrictBool
    n_jobs: int
    score_percentile_high: float = Field(ge=0, le=100)
    score_percentile_medium: float = Field(ge=0, le=100)
    feature_date: str | None = None
    account_feature_version: str | None = None
    graph_feature_version: str | None = None
    graph_build_id: str | None = None
    use_graph_features: StrictBool
    use_behavioural_features: StrictBool
    use_jurisdiction_features: StrictBool
    imputation_strategy: str
    scaling_strategy: str
    min_training_rows: int = Field(gt=0)
    mlflow_enabled: StrictBool
    mlflow_experiment_name: str
    artefact_output_dir: str

    @model_validator(mode="after")
    def validate_isolation_forest_settings(self) -> "IsolationForestConfig":
        if self.contamination != "auto":
            contamination = float(self.contamination)
            if contamination <= 0 or contamination >= 1:
                raise ValueError("contamination must be 'auto' or between 0 and 1")
        if self.score_percentile_medium >= self.score_percentile_high:
            raise ValueError("score_percentile_medium must be less than score_percentile_high")
        if not (
            self.use_graph_features
            or self.use_behavioural_features
            or self.use_jurisdiction_features
        ):
            raise ValueError("at least one feature group must be enabled")
        if self.imputation_strategy not in {"median", "mean", "zero"}:
            raise ValueError("imputation_strategy must be median, mean, or zero")
        if self.scaling_strategy not in {"standard", "robust", "none"}:
            raise ValueError("scaling_strategy must be standard, robust, or none")
        return self


class LogisticRegressionConfig(StrictBaseModel):
    enabled: StrictBool
    class_weight: str
    max_iter: int = Field(gt=0)


class RandomForestConfig(StrictBaseModel):
    enabled: StrictBool
    n_estimators: int = Field(gt=0)
    max_depth: int = Field(gt=0)
    class_weight: str
    random_state: int


class SupervisedBaselinesConfig(StrictBaseModel):
    logistic_regression: LogisticRegressionConfig
    random_forest: RandomForestConfig


class TrainValidationSplitConfig(StrictBaseModel):
    method: str
    validation_fraction: float = Field(gt=0, lt=1)


class EvaluationConfig(StrictBaseModel):
    primary_metric: str
    k_values: list[int] = Field(min_length=1)
    secondary_metrics: list[str] = Field(min_length=1)
    train_validation_split: TrainValidationSplitConfig

    @field_validator("k_values")
    @classmethod
    def validate_k_values(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("k_values must contain only positive integers")
        return values


class ModelFileConfig(StrictBaseModel):
    model: ModelConfig
    mlflow: MlflowConfig
    features: FeaturesConfig
    isolation_forest: IsolationForestConfig
    supervised_baselines: SupervisedBaselinesConfig
    evaluation: EvaluationConfig
    supervised: dict[str, Any] = Field(default_factory=dict)
    model_comparison: dict[str, Any] = Field(default_factory=dict)
    explainability: dict[str, Any] = Field(default_factory=dict)
    monitoring: dict[str, Any] = Field(default_factory=dict)


class DashboardConfig(StrictBaseModel):
    enabled: StrictBool
    app_title: str
    title: str | None = None
    page_icon: str
    layout: str
    initial_sidebar_state: str
    default_page_size: int | None = Field(default=None, gt=0)
    max_page_size: int | None = Field(default=None, gt=0)
    default_case_statuses: list[str] | None = None
    default_risk_bands: list[str] | None = None
    default_alert_severities: list[str] | None = None
    show_debug_panels: StrictBool | None = None
    enable_lifecycle_actions: StrictBool | None = None
    enable_case_evidence_preview: StrictBool | None = None
    enable_download_buttons: StrictBool | None = None
    refresh_button: StrictBool | None = None


class DashboardPageConfig(StrictBaseModel):
    enabled: StrictBool
    title: str
    route: str


class DashboardTablesConfig(StrictBaseModel):
    default_page_size: int = Field(gt=0)
    max_page_size: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_page_sizes(self) -> "DashboardTablesConfig":
        if self.max_page_size < self.default_page_size:
            raise ValueError("max_page_size must be greater than or equal to default_page_size")
        return self


class DashboardChartsConfig(StrictBaseModel):
    risk_score_bins: int = Field(gt=0)
    default_time_granularity: str
    graph_max_nodes: int = Field(gt=0)
    graph_max_edges: int = Field(gt=0)


class DashboardFiltersConfig(StrictBaseModel):
    severity: list[str] = Field(min_length=1)
    case_status: list[str] = Field(min_length=1)


class DashboardFileConfig(StrictBaseModel):
    dashboard: DashboardConfig
    pages: dict[str, DashboardPageConfig]
    tables: DashboardTablesConfig
    charts: DashboardChartsConfig
    filters: DashboardFiltersConfig
    triage: dict[str, Any] = Field(default_factory=dict)
    formatting: dict[str, Any] = Field(default_factory=dict)
    graph_view: dict[str, Any] = Field(default_factory=dict)
    account_profile: dict[str, Any] = Field(default_factory=dict)
    model_metrics: dict[str, Any] = Field(default_factory=dict)
    audit_log: dict[str, Any] = Field(default_factory=dict)
    validation_report: dict[str, Any] = Field(default_factory=dict)

    @field_validator("pages")
    @classmethod
    def validate_required_pages(
        cls,
        pages: dict[str, DashboardPageConfig],
    ) -> dict[str, DashboardPageConfig]:
        page_titles = {page.title for page in pages.values()}
        missing = REQUIRED_DASHBOARD_PAGES - page_titles
        if missing:
            missing_values = ", ".join(sorted(missing))
            raise ValueError(f"Missing dashboard pages: {missing_values}")
        return pages


class AppConfig(StrictBaseModel):
    project: ProjectFileConfig
    paths: PathsFileConfig
    database: DatabaseFileConfig
    neo4j: Neo4jFileConfig
    rules: RulesFileConfig
    scoring: ScoringFileConfig
    model: ModelFileConfig
    dashboard: DashboardFileConfig

    @model_validator(mode="after")
    def validate_project_package_name(self) -> "AppConfig":
        if self.project.project.package_name != "graph_aml":
            raise ValueError("project package_name must be graph_aml")
        return self


def app_config_from_mapping(config: dict[str, Any]) -> AppConfig:
    """Build an AppConfig from a plain mapping."""

    return AppConfig.model_validate(config)
