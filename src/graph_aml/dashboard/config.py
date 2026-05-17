"""Configuration loading and validation for the local Streamlit dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from graph_aml.dashboard.exceptions import DashboardConfigurationError


@dataclass(frozen=True)
class DashboardTriageConfig:
    case_queue_default_sort: str = "risk_rank"
    alert_queue_default_sort: str = "risk_score_rule"
    case_detail_max_alerts: int = 100
    case_detail_max_transactions: int = 100
    case_detail_max_lifecycle_events: int = 100
    case_detail_max_evidence_bullets: int = 20


@dataclass(frozen=True)
class DashboardFormattingConfig:
    currency: str = "AUD"
    score_decimals: int = 2
    amount_decimals: int = 2
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class DashboardGraphViewConfig:
    enabled: bool = True
    default_layout: str = "spring"
    max_nodes: int = 150
    max_edges: int = 300
    max_hops: int = 2
    include_transactions: bool = True
    include_alerts: bool = True
    include_cases: bool = True
    include_counterparties: bool = True
    include_communities: bool = True
    render_engine: str = "pyvis"
    risk_node_size_min: int = 12
    risk_node_size_max: int = 42
    show_legend: bool = True


@dataclass(frozen=True)
class DashboardAccountProfileConfig:
    enabled: bool = True
    max_transactions: int = 250
    max_alerts: int = 100
    max_cases: int = 50
    max_counterparties: int = 50
    transaction_lookback_days: int | None = None
    show_feature_tables: bool = True
    show_linked_cases: bool = True
    show_graph_features: bool = True
    show_anomaly_scores: bool = True
    show_account_risk_scores: bool = True


@dataclass(frozen=True)
class DashboardModelMetricsConfig:
    enabled: bool = True
    default_model_metric_limit: int = 500
    default_score_limit: int = 1000
    default_top_k_values: tuple[int, ...] = (10, 25, 50, 100)
    show_mlflow_metadata: bool = True
    show_account_anomaly_scores: bool = True
    show_account_risk_scores: bool = True
    show_case_risk_scores: bool = True
    show_score_distributions: bool = True
    show_top_ranked_tables: bool = True
    show_precision_at_k_placeholder: bool = True


@dataclass(frozen=True)
class DashboardAuditLogConfig:
    enabled: bool = True
    default_limit: int = 500
    max_limit: int = 5000
    default_components: tuple[str, ...] = (
        "ingestion",
        "validation",
        "rules",
        "graph",
        "models",
        "scoring",
        "cases",
        "dashboard",
    )
    searchable_fields: tuple[str, ...] = (
        "event_type",
        "component",
        "action",
        "status",
        "run_id",
    )


@dataclass(frozen=True)
class DashboardValidationReportConfig:
    enabled: bool = True
    report_dir: str = "reports/model_validation"
    max_preview_chars: int = 12000
    allowed_extensions: tuple[str, ...] = (".md", ".json", ".csv", ".txt")
    show_file_metadata: bool = True
    show_downloads: bool = True


@dataclass(frozen=True)
class DashboardConfig:
    title: str = "Graph-Based AML Case Triage"
    page_icon: str = "🕵️"
    layout: str = "wide"
    default_page_size: int = 50
    max_page_size: int = 500
    default_case_statuses: tuple[str, ...] = (
        "New",
        "In review",
        "Escalated",
        "Information requested",
    )
    default_risk_bands: tuple[str, ...] = ("high", "critical")
    default_alert_severities: tuple[str, ...] = ("high", "critical")
    show_debug_panels: bool = False
    enable_lifecycle_actions: bool = True
    enable_case_evidence_preview: bool = True
    enable_download_buttons: bool = True
    refresh_button: bool = True
    triage: DashboardTriageConfig = field(default_factory=DashboardTriageConfig)
    formatting: DashboardFormattingConfig = field(default_factory=DashboardFormattingConfig)
    graph_view: DashboardGraphViewConfig = field(default_factory=DashboardGraphViewConfig)
    account_profile: DashboardAccountProfileConfig = field(
        default_factory=DashboardAccountProfileConfig
    )
    model_metrics: DashboardModelMetricsConfig = field(
        default_factory=DashboardModelMetricsConfig
    )
    audit_log: DashboardAuditLogConfig = field(default_factory=DashboardAuditLogConfig)
    validation_report: DashboardValidationReportConfig = field(
        default_factory=DashboardValidationReportConfig
    )

    def __post_init__(self) -> None:
        validate_dashboard_config(self)


def _as_tuple(values: object) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        return (values,)
    if isinstance(values, list | tuple | set):
        return tuple(str(value) for value in values)
    raise DashboardConfigurationError("default filter values must be strings or sequences")


def _validate_unique_strings(values: tuple[str, ...], label: str) -> None:
    clean = tuple(value.strip() for value in values)
    if not clean or any(not value for value in clean):
        raise DashboardConfigurationError(f"{label} must contain non-empty strings")
    if len(set(clean)) != len(clean):
        raise DashboardConfigurationError(f"{label} must be unique")


def validate_dashboard_config(config: DashboardConfig) -> None:
    """Validate dashboard configuration without opening external resources."""

    if not isinstance(config, DashboardConfig):
        raise DashboardConfigurationError("config must be DashboardConfig")
    if not config.title.strip():
        raise DashboardConfigurationError("title must be non-empty")
    if config.layout not in {"wide", "centered"}:
        raise DashboardConfigurationError("layout must be wide or centered")
    if config.default_page_size <= 0 or config.max_page_size <= 0:
        raise DashboardConfigurationError("page sizes must be positive")
    if config.default_page_size > config.max_page_size:
        raise DashboardConfigurationError("default_page_size must be <= max_page_size")
    _validate_unique_strings(config.default_case_statuses, "default_case_statuses")
    _validate_unique_strings(config.default_risk_bands, "default_risk_bands")
    _validate_unique_strings(config.default_alert_severities, "default_alert_severities")
    for field_name in (
        "show_debug_panels",
        "enable_lifecycle_actions",
        "enable_case_evidence_preview",
        "enable_download_buttons",
        "refresh_button",
    ):
        if not isinstance(getattr(config, field_name), bool):
            raise DashboardConfigurationError(f"{field_name} must be boolean")
    triage = config.triage
    for field_name in (
        "case_detail_max_alerts",
        "case_detail_max_transactions",
        "case_detail_max_lifecycle_events",
        "case_detail_max_evidence_bullets",
    ):
        if getattr(triage, field_name) <= 0:
            raise DashboardConfigurationError(f"triage.{field_name} must be positive")
    formatting = config.formatting
    if formatting.score_decimals < 0 or formatting.amount_decimals < 0:
        raise DashboardConfigurationError("formatting decimals must be non-negative")
    if not formatting.currency.strip():
        raise DashboardConfigurationError("currency must be non-empty")
    graph = config.graph_view
    if not isinstance(graph.enabled, bool):
        raise DashboardConfigurationError("graph_view.enabled must be boolean")
    if graph.default_layout not in {"spring", "kamada_kawai", "circular", "shell"}:
        raise DashboardConfigurationError("graph_view.default_layout is invalid")
    if graph.render_engine not in {"pyvis", "plotly"}:
        raise DashboardConfigurationError("graph_view.render_engine is invalid")
    for field_name in (
        "max_nodes",
        "max_edges",
        "max_hops",
        "risk_node_size_min",
        "risk_node_size_max",
    ):
        if getattr(graph, field_name) <= 0:
            raise DashboardConfigurationError(f"graph_view.{field_name} must be positive")
    if graph.risk_node_size_min > graph.risk_node_size_max:
        raise DashboardConfigurationError("graph_view node size bounds are invalid")
    for field_name in (
        "include_transactions",
        "include_alerts",
        "include_cases",
        "include_counterparties",
        "include_communities",
        "show_legend",
    ):
        if not isinstance(getattr(graph, field_name), bool):
            raise DashboardConfigurationError(f"graph_view.{field_name} must be boolean")
    account = config.account_profile
    if not isinstance(account.enabled, bool):
        raise DashboardConfigurationError("account_profile.enabled must be boolean")
    for field_name in ("max_transactions", "max_alerts", "max_cases", "max_counterparties"):
        if getattr(account, field_name) <= 0:
            raise DashboardConfigurationError(f"account_profile.{field_name} must be positive")
    if account.transaction_lookback_days is not None and account.transaction_lookback_days <= 0:
        raise DashboardConfigurationError(
            "account_profile.transaction_lookback_days must be positive"
        )
    for field_name in (
        "show_feature_tables",
        "show_linked_cases",
        "show_graph_features",
        "show_anomaly_scores",
        "show_account_risk_scores",
    ):
        if not isinstance(getattr(account, field_name), bool):
            raise DashboardConfigurationError(f"account_profile.{field_name} must be boolean")
    model = config.model_metrics
    if not isinstance(model.enabled, bool):
        raise DashboardConfigurationError("model_metrics.enabled must be boolean")
    if model.default_model_metric_limit <= 0 or model.default_score_limit <= 0:
        raise DashboardConfigurationError("model_metrics limits must be positive")
    if (
        not model.default_top_k_values
        or any(not isinstance(value, int) or value <= 0 for value in model.default_top_k_values)
        or len(set(model.default_top_k_values)) != len(model.default_top_k_values)
    ):
        raise DashboardConfigurationError("model_metrics.default_top_k_values is invalid")
    for field_name in (
        "show_mlflow_metadata",
        "show_account_anomaly_scores",
        "show_account_risk_scores",
        "show_case_risk_scores",
        "show_score_distributions",
        "show_top_ranked_tables",
        "show_precision_at_k_placeholder",
    ):
        if not isinstance(getattr(model, field_name), bool):
            raise DashboardConfigurationError(f"model_metrics.{field_name} must be boolean")
    audit = config.audit_log
    if not isinstance(audit.enabled, bool):
        raise DashboardConfigurationError("audit_log.enabled must be boolean")
    if audit.default_limit <= 0 or audit.max_limit <= 0 or audit.default_limit > audit.max_limit:
        raise DashboardConfigurationError("audit_log limits are invalid")
    _validate_unique_strings(tuple(audit.default_components), "audit_log.default_components")
    _validate_unique_strings(tuple(audit.searchable_fields), "audit_log.searchable_fields")
    report = config.validation_report
    if not isinstance(report.enabled, bool):
        raise DashboardConfigurationError("validation_report.enabled must be boolean")
    if not report.report_dir.strip():
        raise DashboardConfigurationError("validation_report.report_dir must be non-empty")
    if report.max_preview_chars <= 0:
        raise DashboardConfigurationError("validation_report.max_preview_chars must be positive")
    extensions = tuple(value.strip() for value in report.allowed_extensions)
    if (
        not extensions
        or any(not value.startswith(".") for value in extensions)
        or len(set(extensions)) != len(extensions)
    ):
        raise DashboardConfigurationError("validation_report.allowed_extensions is invalid")
    for field_name in ("show_file_metadata", "show_downloads"):
        if not isinstance(getattr(report, field_name), bool):
            raise DashboardConfigurationError(f"validation_report.{field_name} must be boolean")


def dashboard_config_from_mapping(payload: dict[str, object] | None) -> DashboardConfig:
    """Build dashboard config from a mapping."""

    if payload is None:
        return DashboardConfig()
    try:
        data = dict(payload)
        triage_payload = data.pop("triage", {})
        formatting_payload = data.pop("formatting", {})
        graph_view_payload = data.pop("graph_view", {})
        account_profile_payload = data.pop("account_profile", {})
        model_metrics_payload = data.pop("model_metrics", {})
        audit_log_payload = data.pop("audit_log", {})
        validation_report_payload = data.pop("validation_report", {})
        if isinstance(triage_payload, dict):
            data["triage"] = DashboardTriageConfig(**triage_payload)
        elif triage_payload:
            raise DashboardConfigurationError("triage config must be a mapping")
        if isinstance(formatting_payload, dict):
            data["formatting"] = DashboardFormattingConfig(**formatting_payload)
        elif formatting_payload:
            raise DashboardConfigurationError("formatting config must be a mapping")
        if isinstance(graph_view_payload, dict):
            data["graph_view"] = DashboardGraphViewConfig(**graph_view_payload)
        elif graph_view_payload:
            raise DashboardConfigurationError("graph_view config must be a mapping")
        if isinstance(account_profile_payload, dict):
            data["account_profile"] = DashboardAccountProfileConfig(**account_profile_payload)
        elif account_profile_payload:
            raise DashboardConfigurationError("account_profile config must be a mapping")
        if isinstance(model_metrics_payload, dict):
            if "default_top_k_values" in model_metrics_payload:
                model_metrics_payload = dict(model_metrics_payload)
                model_metrics_payload["default_top_k_values"] = tuple(
                    int(value) for value in model_metrics_payload["default_top_k_values"]
                )
            data["model_metrics"] = DashboardModelMetricsConfig(**model_metrics_payload)
        elif model_metrics_payload:
            raise DashboardConfigurationError("model_metrics config must be a mapping")
        if isinstance(audit_log_payload, dict):
            audit_log_payload = dict(audit_log_payload)
            for key in ("default_components", "searchable_fields"):
                if key in audit_log_payload:
                    audit_log_payload[key] = _as_tuple(audit_log_payload[key])
            data["audit_log"] = DashboardAuditLogConfig(**audit_log_payload)
        elif audit_log_payload:
            raise DashboardConfigurationError("audit_log config must be a mapping")
        if isinstance(validation_report_payload, dict):
            validation_report_payload = dict(validation_report_payload)
            if "allowed_extensions" in validation_report_payload:
                validation_report_payload["allowed_extensions"] = _as_tuple(
                    validation_report_payload["allowed_extensions"]
                )
            data["validation_report"] = DashboardValidationReportConfig(
                **validation_report_payload
            )
        elif validation_report_payload:
            raise DashboardConfigurationError("validation_report config must be a mapping")
        for key in ("default_case_statuses", "default_risk_bands", "default_alert_severities"):
            if key in data:
                data[key] = _as_tuple(data[key])
        allowed = set(DashboardConfig.__dataclass_fields__)
        values = {key: value for key, value in data.items() if key in allowed}
        return DashboardConfig(**values)  # type: ignore[arg-type]
    except DashboardConfigurationError:
        raise
    except Exception as exc:
        raise DashboardConfigurationError(f"invalid dashboard config: {exc}") from exc


def load_dashboard_config(config_path: Path | str = "config/dashboard.yaml") -> DashboardConfig:
    """Load dashboard config from YAML without connecting to PostgreSQL."""

    path = Path(config_path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise DashboardConfigurationError(f"Failed to load dashboard config: {exc}") from exc
    if not isinstance(payload, dict):
        raise DashboardConfigurationError("dashboard config file must contain a mapping")
    dashboard_payload = payload.get("dashboard", {})
    if not isinstance(dashboard_payload, dict):
        raise DashboardConfigurationError("dashboard section must be a mapping")
    merged = dict(dashboard_payload)
    if isinstance(payload.get("triage"), dict):
        merged["triage"] = payload["triage"]
    if isinstance(payload.get("formatting"), dict):
        merged["formatting"] = payload["formatting"]
    if isinstance(payload.get("graph_view"), dict):
        merged["graph_view"] = payload["graph_view"]
    if isinstance(payload.get("account_profile"), dict):
        merged["account_profile"] = payload["account_profile"]
    if isinstance(payload.get("model_metrics"), dict):
        merged["model_metrics"] = payload["model_metrics"]
    if isinstance(payload.get("audit_log"), dict):
        merged["audit_log"] = payload["audit_log"]
    if isinstance(payload.get("validation_report"), dict):
        merged["validation_report"] = payload["validation_report"]
    return dashboard_config_from_mapping(merged)
