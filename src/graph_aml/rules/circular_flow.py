"""Deterministic circular flow detection over transaction networks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import isfinite
from typing import Any, cast

import networkx as nx
import pandas as pd

from graph_aml.alerts import (
    ALERT_SEVERITIES,
    AlertRecord,
    build_alert_id,
    create_alert_record,
    validate_alert_records,
)
from graph_aml.rules.common import normalise_rule_transactions, require_columns
from graph_aml.rules.exceptions import (
    RuleConfigurationError,
    RuleExecutionError,
    RuleInputError,
)

CIRCULAR_FLOW_EDGE_COLUMNS = (
    "source_account_id",
    "target_account_id",
    "transaction_id",
    "transaction_timestamp",
    "amount",
    "transaction_type",
    "counterparty_id",
)

CIRCULAR_FLOW_DETECTION_COLUMNS = (
    "cycle_id",
    "primary_account_id",
    "cycle_accounts",
    "cycle_length",
    "detection_window_start",
    "detection_window_end",
    "time_span_hours",
    "transaction_count",
    "total_amount",
    "min_amount",
    "max_amount",
    "evidence_ids",
    "cycle_path",
)


@dataclass(frozen=True)
class CircularFlowDetectionConfig:
    """Configuration for deterministic directed-cycle detection."""

    rule_name: str = "Circular flow"
    typology: str = "circular_flow"
    max_cycle_hops: int = 4
    min_cycle_hops: int = 2
    min_total_amount: float = 0.0
    max_time_span_hours: int | None = 168
    transaction_types: tuple[str, ...] = ("transfer", "wire")
    include_counterparty_edges: bool = False
    include_self_loops: bool = False
    max_cycles_per_account: int = 3
    max_total_cycles: int = 500

    def __post_init__(self) -> None:
        try:
            max_cycle_hops = int(self.max_cycle_hops)
            min_cycle_hops = int(self.min_cycle_hops)
            min_total_amount = float(self.min_total_amount)
            max_cycles_per_account = int(self.max_cycles_per_account)
            max_total_cycles = int(self.max_total_cycles)
            max_time_span_hours = (
                None if self.max_time_span_hours is None else int(self.max_time_span_hours)
            )
        except (TypeError, ValueError) as exc:
            raise RuleConfigurationError(
                "circular flow numeric configuration values must be valid"
            ) from exc
        if not self.rule_name.strip():
            raise RuleConfigurationError("rule_name must be non-empty")
        if not self.typology.strip():
            raise RuleConfigurationError("typology must be non-empty")
        if max_cycle_hops < 2:
            raise RuleConfigurationError("max_cycle_hops must be at least 2")
        if min_cycle_hops < 2:
            raise RuleConfigurationError("min_cycle_hops must be at least 2")
        if max_cycle_hops < min_cycle_hops:
            raise RuleConfigurationError(
                "max_cycle_hops must be greater than or equal to min_cycle_hops"
            )
        if not isfinite(min_total_amount) or min_total_amount < 0:
            raise RuleConfigurationError("min_total_amount must be non-negative")
        if max_time_span_hours is not None and max_time_span_hours <= 0:
            raise RuleConfigurationError("max_time_span_hours must be positive when supplied")
        if not isinstance(self.include_counterparty_edges, bool):
            raise RuleConfigurationError("include_counterparty_edges must be boolean")
        if not isinstance(self.include_self_loops, bool):
            raise RuleConfigurationError("include_self_loops must be boolean")
        if max_cycles_per_account <= 0:
            raise RuleConfigurationError("max_cycles_per_account must be positive")
        if max_total_cycles <= 0:
            raise RuleConfigurationError("max_total_cycles must be positive")
        transaction_types = tuple(
            str(value).strip().lower() for value in self.transaction_types if str(value).strip()
        )
        if not transaction_types:
            raise RuleConfigurationError("at least one transaction type must be configured")
        object.__setattr__(self, "rule_name", self.rule_name.strip())
        object.__setattr__(self, "typology", self.typology.strip().lower())
        object.__setattr__(self, "max_cycle_hops", max_cycle_hops)
        object.__setattr__(self, "min_cycle_hops", min_cycle_hops)
        object.__setattr__(self, "min_total_amount", min_total_amount)
        object.__setattr__(self, "max_time_span_hours", max_time_span_hours)
        object.__setattr__(self, "transaction_types", transaction_types)
        object.__setattr__(self, "max_cycles_per_account", max_cycles_per_account)
        object.__setattr__(self, "max_total_cycles", max_total_cycles)


@dataclass(frozen=True)
class CircularFlowRuleConfig:
    """Configuration for circular-flow alert conversion."""

    rule_name: str = "Circular flow"
    typology: str = "circular_flow"
    severity: str = "high"
    base_risk_score: float = 85.0
    high_amount_risk_score: float = 90.0
    high_amount_threshold: float = 50000.0
    long_cycle_risk_score: float = 90.0
    long_cycle_hop_threshold: int = 4
    detection_config: CircularFlowDetectionConfig | None = None

    def __post_init__(self) -> None:
        try:
            base_risk_score = float(self.base_risk_score)
            high_amount_risk_score = float(self.high_amount_risk_score)
            high_amount_threshold = float(self.high_amount_threshold)
            long_cycle_risk_score = float(self.long_cycle_risk_score)
            long_cycle_hop_threshold = int(self.long_cycle_hop_threshold)
        except (TypeError, ValueError) as exc:
            raise RuleConfigurationError(
                "circular flow alert numeric configuration values must be valid"
            ) from exc
        if not self.rule_name.strip():
            raise RuleConfigurationError("rule_name must be non-empty")
        if not self.typology.strip():
            raise RuleConfigurationError("typology must be non-empty")
        if self.severity.lower() not in ALERT_SEVERITIES:
            raise RuleConfigurationError(f"severity must be one of {ALERT_SEVERITIES}")
        for field_name, score in (
            ("base_risk_score", base_risk_score),
            ("high_amount_risk_score", high_amount_risk_score),
            ("long_cycle_risk_score", long_cycle_risk_score),
        ):
            if not isfinite(score) or score < 0 or score > 100:
                raise RuleConfigurationError(f"{field_name} must be between 0 and 100")
        if not isfinite(high_amount_threshold) or high_amount_threshold < 0:
            raise RuleConfigurationError("high_amount_threshold must be non-negative")
        if long_cycle_hop_threshold < 2:
            raise RuleConfigurationError("long_cycle_hop_threshold must be at least 2")
        detection_config = (
            CircularFlowDetectionConfig()
            if self.detection_config is None
            else self.detection_config
        )
        object.__setattr__(self, "rule_name", self.rule_name.strip())
        object.__setattr__(self, "typology", self.typology.strip().lower())
        object.__setattr__(self, "severity", self.severity.lower())
        object.__setattr__(self, "base_risk_score", base_risk_score)
        object.__setattr__(self, "high_amount_risk_score", high_amount_risk_score)
        object.__setattr__(self, "high_amount_threshold", high_amount_threshold)
        object.__setattr__(self, "long_cycle_risk_score", long_cycle_risk_score)
        object.__setattr__(self, "long_cycle_hop_threshold", long_cycle_hop_threshold)
        object.__setattr__(self, "detection_config", detection_config)


def build_circular_flow_reason_code(
    cycle_length: int,
    total_amount: float,
    time_span_hours: float | int | None,
    template: str | None = None,
) -> str:
    """Build deterministic circular-flow reason text."""

    try:
        cycle_length_value = int(cycle_length)
    except (TypeError, ValueError) as exc:
        raise RuleInputError("cycle_length must be an integer") from exc
    try:
        amount = float(total_amount)
    except (TypeError, ValueError) as exc:
        raise RuleInputError("total_amount must be numeric") from exc
    if cycle_length_value < 2:
        raise RuleInputError("cycle_length must be at least 2")
    if not isfinite(amount) or amount < 0:
        raise RuleInputError("total_amount must be non-negative")
    time_span: float | None = None
    if time_span_hours is not None:
        try:
            time_span = float(time_span_hours)
        except (TypeError, ValueError) as exc:
            raise RuleInputError("time_span_hours must be numeric when supplied") from exc
        if not isfinite(time_span) or time_span < 0:
            raise RuleInputError("time_span_hours must be non-negative when supplied")
    if template is not None:
        return template.format(
            cycle_length=cycle_length_value,
            total_amount=amount,
            total_amount_formatted=f"{amount:.2f}",
            time_span_hours=time_span,
            time_span_hours_formatted=None
            if time_span is None
            else _format_time_span_hours(time_span),
        )
    base = f"{cycle_length_value}-account circular flow with {amount:.2f} total value"
    if time_span is None:
        return base
    return f"{base} over {_format_time_span_hours(time_span)} hours"


def attach_circular_flow_customer_ids(
    detections: pd.DataFrame,
    accounts: pd.DataFrame,
) -> pd.DataFrame:
    """Attach customer IDs for circular-flow primary accounts."""

    require_columns(detections, CIRCULAR_FLOW_DETECTION_COLUMNS, "detections")
    try:
        output = detections.copy()
        if output.empty:
            output["customer_id"] = pd.Series(dtype="object")
            return output
        output["customer_id"] = None
        if (
            accounts.empty
            or "account_id" not in accounts.columns
            or "customer_id" not in accounts.columns
        ):
            return output
        account_lookup = accounts.loc[:, ["account_id", "customer_id"]].copy()
        account_lookup["account_id"] = account_lookup["account_id"].apply(
            _normalise_account_lookup_id
        )
        with_customer = output.merge(
            account_lookup.drop_duplicates("account_id", keep="last"),
            left_on="primary_account_id",
            right_on="account_id",
            how="left",
            suffixes=("", "_account"),
        )
        if "customer_id_account" in with_customer.columns:
            with_customer["customer_id"] = with_customer["customer_id_account"]
            with_customer = with_customer.drop(columns=["customer_id_account"])
        if "account_id" in with_customer.columns:
            with_customer = with_customer.drop(columns=["account_id"])
        with_customer["customer_id"] = with_customer["customer_id"].apply(_optional_string)
        return with_customer
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleInputError(f"Failed to attach circular flow customer IDs: {exc}") from exc


def calculate_circular_flow_rule_score(
    detection: pd.Series | dict[str, object],
    config: CircularFlowRuleConfig | None = None,
) -> float:
    """Select the rule score for a circular-flow detection."""

    resolved_config = CircularFlowRuleConfig() if config is None else config
    try:
        detection_payload = (
            cast(dict[str, Any], detection.to_dict())
            if isinstance(detection, pd.Series)
            else cast(dict[str, Any], detection)
        )
        total_amount = float(cast(Any, detection_payload["total_amount"]))
        cycle_length = int(cast(Any, detection_payload["cycle_length"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise RuleExecutionError(f"Invalid circular flow detection payload: {exc}") from exc
    score = resolved_config.base_risk_score
    if total_amount >= resolved_config.high_amount_threshold:
        score = max(score, resolved_config.high_amount_risk_score)
    if cycle_length >= resolved_config.long_cycle_hop_threshold:
        score = max(score, resolved_config.long_cycle_risk_score)
    return float(score)


def prepare_circular_flow_transactions(
    transactions: pd.DataFrame,
    config: CircularFlowDetectionConfig | None = None,
) -> pd.DataFrame:
    """Prepare staged transactions as directed graph edges."""

    resolved_config = CircularFlowDetectionConfig() if config is None else config
    try:
        require_columns(transactions, ("receiver_account_id", "counterparty_id"), "transactions")
        frame = normalise_rule_transactions(transactions)
        mask = (
            frame["sender_account_id"].notna()
            & frame["amount"].gt(0)
            & frame["transaction_type"].isin(resolved_config.transaction_types)
        )
        output = frame.loc[mask].copy()
        if output.empty:
            return _empty_prepared_transactions(output)

        receiver_present = output["receiver_account_id"].notna()
        counterparty_present = output["counterparty_id"].notna()
        if resolved_config.include_counterparty_edges:
            output = output.loc[receiver_present | counterparty_present].copy()
        else:
            output = output.loc[receiver_present].copy()
        if output.empty:
            return _empty_prepared_transactions(output)

        receiver_present = output["receiver_account_id"].notna()
        output["source_account_id"] = output["sender_account_id"]
        output["target_account_id"] = output["receiver_account_id"]
        if resolved_config.include_counterparty_edges:
            output.loc[~receiver_present, "target_account_id"] = output.loc[
                ~receiver_present,
                "counterparty_id",
            ].apply(_counterparty_node_id)
        output["target_node_type"] = "account"
        output.loc[~receiver_present, "target_node_type"] = "counterparty"
        if not resolved_config.include_self_loops:
            output = output.loc[
                output["target_node_type"].ne("account")
                | output["source_account_id"].ne(output["target_account_id"])
            ].copy()

        return output.sort_values(
            [
                "source_account_id",
                "target_account_id",
                "transaction_timestamp",
                "transaction_id",
            ],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to prepare circular flow transactions: {exc}") from exc


def build_circular_flow_edges(
    transactions: pd.DataFrame,
    config: CircularFlowDetectionConfig | None = None,
) -> pd.DataFrame:
    """Build the circular-flow edge table with one row per transaction edge."""

    resolved_config = CircularFlowDetectionConfig() if config is None else config
    try:
        frame = prepare_circular_flow_transactions(transactions, resolved_config)
        if frame.empty:
            return pd.DataFrame(columns=CIRCULAR_FLOW_EDGE_COLUMNS)
        output = frame.loc[:, CIRCULAR_FLOW_EDGE_COLUMNS].copy()
        output["transaction_timestamp"] = pd.to_datetime(
            output["transaction_timestamp"],
            utc=True,
            errors="coerce",
        )
        output["amount"] = pd.to_numeric(output["amount"], errors="coerce").astype(float)
        output = output.loc[
            output["source_account_id"].notna()
            & output["target_account_id"].notna()
            & output["transaction_timestamp"].notna()
            & output["amount"].notna()
            & output["amount"].gt(0)
        ].copy()
        return output.sort_values(
            [
                "source_account_id",
                "target_account_id",
                "transaction_timestamp",
                "transaction_id",
            ],
            kind="mergesort",
        ).reset_index(drop=True)
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to build circular flow edges: {exc}") from exc


def build_circular_flow_graph(edges: pd.DataFrame) -> nx.MultiDiGraph:
    """Build a directed multigraph from circular-flow edges."""

    require_columns(edges, CIRCULAR_FLOW_EDGE_COLUMNS, "edges")
    graph = nx.MultiDiGraph()
    if edges.empty:
        return graph

    ordered = edges.sort_values(
        [
            "source_account_id",
            "target_account_id",
            "transaction_timestamp",
            "transaction_id",
        ],
        kind="mergesort",
    )
    for _, row in ordered.iterrows():
        source = str(row["source_account_id"])
        target = str(row["target_account_id"])
        transaction_id = str(row["transaction_id"])
        graph.add_node(source, node_id=source)
        graph.add_node(target, node_id=target)
        graph.add_edge(
            source,
            target,
            key=transaction_id,
            transaction_id=transaction_id,
            transaction_timestamp=row["transaction_timestamp"],
            amount=float(row["amount"]),
            transaction_type=row["transaction_type"],
            counterparty_id=row["counterparty_id"],
        )
    return graph


def canonicalise_cycle_accounts(accounts: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Rotate a directed cycle so the lexicographically smallest node starts it."""

    values = tuple(str(value).strip() for value in accounts)
    if len(values) >= 2 and values[0] == values[-1]:
        values = values[:-1]
    if len(values) < 2:
        raise RuleInputError("cycle must contain at least two accounts")
    if any(not value for value in values):
        raise RuleInputError("cycle accounts must be non-empty")
    if len(set(values)) != len(values):
        raise RuleInputError("cycle accounts must not contain duplicate intermediate nodes")
    smallest = min(values)
    start_index = values.index(smallest)
    return values[start_index:] + values[:start_index]


def build_cycle_id(
    cycle_accounts: tuple[str, ...] | list[str],
    evidence_ids: tuple[str, ...] | list[str],
) -> str:
    """Build a deterministic circular-flow cycle identifier."""

    canonical = canonicalise_cycle_accounts(cycle_accounts)
    evidence = tuple(sorted(str(value).strip() for value in evidence_ids if str(value).strip()))
    if not evidence:
        raise RuleInputError("evidence_ids must contain at least one transaction ID")
    payload = "|".join(canonical) + "||" + "|".join(evidence)
    suffix = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8].upper()
    return f"CF_{suffix}"


def normalise_cycle_path(cycle_accounts: tuple[str, ...] | list[str]) -> str:
    """Return a deterministic closed-cycle path string."""

    canonical = canonicalise_cycle_accounts(cycle_accounts)
    return " -> ".join((*canonical, canonical[0]))


def select_cycle_edge_evidence(
    cycle_accounts: tuple[str, ...] | list[str],
    edges: pd.DataFrame,
) -> pd.DataFrame:
    """Select all transaction evidence for every directed step in a cycle."""

    require_columns(edges, CIRCULAR_FLOW_EDGE_COLUMNS, "edges")
    canonical = canonicalise_cycle_accounts(cycle_accounts)
    if edges.empty:
        raise RuleExecutionError("cannot select cycle evidence from empty edges")
    try:
        ordered_steps: list[pd.DataFrame] = []
        for step_index, source in enumerate(canonical):
            target = canonical[(step_index + 1) % len(canonical)]
            step_edges = edges.loc[
                edges["source_account_id"].eq(source) & edges["target_account_id"].eq(target)
            ].copy()
            if step_edges.empty:
                raise RuleExecutionError(
                    f"Missing evidence for circular flow step {source} -> {target}"
                )
            step_edges["_cycle_step"] = step_index
            ordered_steps.append(step_edges)
        output = pd.concat(ordered_steps, ignore_index=True)
        output = output.sort_values(
            ["_cycle_step", "transaction_timestamp", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
        return output.loc[:, CIRCULAR_FLOW_EDGE_COLUMNS].copy()
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to select circular flow evidence: {exc}") from exc


def detect_circular_flows(
    transactions: pd.DataFrame,
    config: CircularFlowDetectionConfig | None = None,
) -> pd.DataFrame:
    """Detect directed transaction cycles within the configured hop and time limits."""

    resolved_config = CircularFlowDetectionConfig() if config is None else config
    try:
        edges = build_circular_flow_edges(transactions, resolved_config)
        if edges.empty:
            return pd.DataFrame(columns=CIRCULAR_FLOW_DETECTION_COLUMNS)
        graph = build_circular_flow_graph(edges)
        if graph.number_of_edges() == 0:
            return pd.DataFrame(columns=CIRCULAR_FLOW_DETECTION_COLUMNS)

        simple_graph = nx.DiGraph()
        simple_graph.add_nodes_from(graph.nodes())
        simple_graph.add_edges_from((source, target) for source, target in graph.edges())

        rows_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, object]] = {}
        raw_cycles = sorted(
            cast(list[list[str]], nx.simple_cycles(simple_graph)),
            key=lambda cycle: (len(cycle), tuple(cycle)),
        )
        for raw_cycle in raw_cycles:
            if len(raw_cycle) < resolved_config.min_cycle_hops:
                continue
            if len(raw_cycle) > resolved_config.max_cycle_hops:
                continue
            canonical = canonicalise_cycle_accounts(raw_cycle)
            if len(canonical) < resolved_config.min_cycle_hops:
                continue
            evidence = select_cycle_edge_evidence(canonical, edges)
            total_amount = float(evidence["amount"].sum())
            if total_amount < resolved_config.min_total_amount:
                continue
            start_timestamp = pd.Timestamp(evidence["transaction_timestamp"].min())
            end_timestamp = pd.Timestamp(evidence["transaction_timestamp"].max())
            time_span_hours = float((end_timestamp - start_timestamp).total_seconds() / 3600.0)
            if (
                resolved_config.max_time_span_hours is not None
                and time_span_hours > resolved_config.max_time_span_hours
            ):
                continue
            evidence_ids = tuple(evidence["transaction_id"].astype(str).tolist())
            key = (canonical, tuple(sorted(evidence_ids)))
            rows_by_key[key] = {
                "cycle_id": build_cycle_id(canonical, evidence_ids),
                "primary_account_id": canonical[0],
                "cycle_accounts": canonical,
                "cycle_length": int(len(canonical)),
                "detection_window_start": start_timestamp.isoformat(),
                "detection_window_end": end_timestamp.isoformat(),
                "time_span_hours": time_span_hours,
                "transaction_count": int(len(evidence)),
                "total_amount": total_amount,
                "min_amount": float(evidence["amount"].min()),
                "max_amount": float(evidence["amount"].max()),
                "evidence_ids": evidence_ids,
                "cycle_path": normalise_cycle_path(canonical),
            }

        if not rows_by_key:
            return pd.DataFrame(columns=CIRCULAR_FLOW_DETECTION_COLUMNS)

        rows = sorted(rows_by_key.values(), key=_circular_flow_detection_sort_key)
        limited_rows: list[dict[str, object]] = []
        counts_by_account: dict[str, int] = {}
        for row in rows:
            primary_account_id = str(row["primary_account_id"])
            current_count = counts_by_account.get(primary_account_id, 0)
            if current_count >= resolved_config.max_cycles_per_account:
                continue
            limited_rows.append(row)
            counts_by_account[primary_account_id] = current_count + 1
            if len(limited_rows) >= resolved_config.max_total_cycles:
                break

        return (
            pd.DataFrame(
                limited_rows,
                columns=CIRCULAR_FLOW_DETECTION_COLUMNS,
            )
            .sort_values(
                ["primary_account_id", "cycle_length", "detection_window_start", "cycle_id"],
                kind="mergesort",
            )
            .reset_index(drop=True)
        )
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to detect circular flows: {exc}") from exc


def circular_flow_detections_to_dicts(
    detections: pd.DataFrame,
) -> list[dict[str, object]]:
    """Convert circular-flow detections to JSON-serialisable dictionaries."""

    require_columns(detections, CIRCULAR_FLOW_DETECTION_COLUMNS, "detections")
    if detections.empty:
        return []
    payload: list[dict[str, object]] = []
    for record in detections.loc[:, CIRCULAR_FLOW_DETECTION_COLUMNS].to_dict(orient="records"):
        item = dict(record)
        item["cycle_accounts"] = list(_normalise_tuple(item.get("cycle_accounts")))
        item["evidence_ids"] = list(_normalise_tuple(item.get("evidence_ids")))
        payload.append(item)
    return payload


def circular_flow_detections_to_dataframe(
    payload: list[dict[str, object]],
) -> pd.DataFrame:
    """Convert serialised circular-flow detection dictionaries back to a DataFrame."""

    if not payload:
        return pd.DataFrame(columns=CIRCULAR_FLOW_DETECTION_COLUMNS)
    rows: list[dict[str, object]] = []
    for item in payload:
        row = {column: item.get(column) for column in CIRCULAR_FLOW_DETECTION_COLUMNS}
        row["cycle_accounts"] = _normalise_tuple(row.get("cycle_accounts"))
        row["evidence_ids"] = _normalise_tuple(row.get("evidence_ids"))
        rows.append(row)
    return pd.DataFrame(rows, columns=CIRCULAR_FLOW_DETECTION_COLUMNS)


def build_circular_flow_alerts(
    detections: pd.DataFrame,
    accounts: pd.DataFrame,
    config: CircularFlowRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Convert circular-flow detections into common AlertRecord objects."""

    resolved_config = CircularFlowRuleConfig() if config is None else config
    try:
        if detections.empty:
            return ()
        require_columns(detections, CIRCULAR_FLOW_DETECTION_COLUMNS, "detections")
        with_customers = attach_circular_flow_customer_ids(detections, accounts)
        alerts: list[AlertRecord] = []
        for record in with_customers.sort_values(
            ["primary_account_id", "detection_window_start", "cycle_id"],
            kind="mergesort",
        ).to_dict(orient="records"):
            evidence_ids = _normalise_tuple(record["evidence_ids"])
            account_id = str(record["primary_account_id"])
            detection_window_start = str(record["detection_window_start"])
            alert = create_alert_record(
                alert_id=build_alert_id(
                    resolved_config.rule_name,
                    account_id,
                    detection_window_start,
                    evidence_ids,
                ),
                account_id=account_id,
                customer_id=_optional_string(record.get("customer_id")),
                rule_name=resolved_config.rule_name,
                typology=resolved_config.typology,
                severity=resolved_config.severity,
                risk_score_rule=calculate_circular_flow_rule_score(
                    record,
                    resolved_config,
                ),
                reason_code=build_circular_flow_reason_code(
                    int(record["cycle_length"]),
                    float(record["total_amount"]),
                    record.get("time_span_hours"),
                ),
                evidence_ids=evidence_ids,
                detection_window_start=detection_window_start,
                detection_window_end=str(record["detection_window_end"]),
                model_run_id=model_run_id,
            )
            alerts.append(alert)
        output = tuple(
            sorted(
                alerts,
                key=lambda alert: (
                    alert.account_id,
                    alert.detection_window_start or "",
                    alert.alert_id,
                ),
            )
        )
        validate_alert_records(output)
        return output
    except RuleInputError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to build circular flow alerts: {exc}") from exc


def run_circular_flow_rule(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    detection_config: CircularFlowDetectionConfig | None = None,
    alert_config: CircularFlowRuleConfig | None = None,
    model_run_id: str | None = None,
) -> tuple[AlertRecord, ...]:
    """Run circular-flow detection and alert conversion without persistence."""

    resolved_alert_config = CircularFlowRuleConfig() if alert_config is None else alert_config
    resolved_detection_config = (
        detection_config if detection_config is not None else resolved_alert_config.detection_config
    )
    try:
        require_columns(
            transactions,
            (
                "transaction_id",
                "sender_account_id",
                "receiver_account_id",
                "counterparty_id",
                "transaction_timestamp",
                "amount",
                "transaction_type",
            ),
            "transactions",
        )
        require_columns(accounts, ("account_id",), "accounts")
        detections = detect_circular_flows(transactions, resolved_detection_config)
        return build_circular_flow_alerts(
            detections,
            accounts,
            resolved_alert_config,
            model_run_id=model_run_id,
        )
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(f"Failed to run circular flow rule: {exc}") from exc


def run_circular_flow_detection_and_alerts(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    detection_config: CircularFlowDetectionConfig | None = None,
    alert_config: CircularFlowRuleConfig | None = None,
    model_run_id: str | None = None,
) -> dict[str, object]:
    """Run circular-flow detection once and derive alerts and summaries."""

    resolved_alert_config = CircularFlowRuleConfig() if alert_config is None else alert_config
    resolved_detection_config = (
        detection_config if detection_config is not None else resolved_alert_config.detection_config
    )
    try:
        from graph_aml.rules.summary import (  # noqa: PLC0415
            summarise_circular_flow_detections,
            summarise_rule_alerts,
        )

        detections = detect_circular_flows(transactions, resolved_detection_config)
        alerts = build_circular_flow_alerts(
            detections,
            accounts,
            resolved_alert_config,
            model_run_id=model_run_id,
        )
        return {
            "detections": detections,
            "alerts": alerts,
            "detection_summary": summarise_circular_flow_detections(detections),
            "alert_summary": summarise_rule_alerts(alerts),
        }
    except RuleInputError:
        raise
    except RuleExecutionError:
        raise
    except Exception as exc:
        raise RuleExecutionError(
            f"Failed to run circular flow detection and alerts: {exc}"
        ) from exc


def _empty_prepared_transactions(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in ("source_account_id", "target_account_id", "target_node_type"):
        if column not in output.columns:
            output[column] = pd.Series(dtype="object")
    return output.reset_index(drop=True)


def _counterparty_node_id(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return f"CP:{text}"


def _normalise_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, tuple | list):
        return tuple(str(item) for item in value)
    return tuple(str(item) for item in cast(Any, value))


def _normalise_account_lookup_id(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text.upper() if text else None


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


def _format_time_span_hours(value: float) -> str:
    return f"{value:.1f}"


def _circular_flow_detection_sort_key(item: dict[str, object]) -> tuple[str, int, str, str]:
    return (
        str(item["primary_account_id"]),
        int(cast(Any, item["cycle_length"])),
        str(item["detection_window_start"]),
        str(item["cycle_id"]),
    )
