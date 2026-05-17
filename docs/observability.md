# Observability

The observability package provides lightweight structured runtime logging for the local-first AML project. It uses the standard library `logging` module and writes one JSON object per log line.

## Runtime Logs

Runtime logs are diagnostics for pipeline execution, development, and local troubleshooting. They are not the persistent governance audit trail. Future audit tables will store selected business and model-risk events in PostgreSQL with stronger retention and review semantics.

## Event Fields

Structured events include `timestamp`, `event_type`, `message`, `component`, optional status and severity fields, optional entity or metric fields, and a `metadata` object for event-specific values.

## Run Context

`RunContext` carries shared fields across related events: `run_id`, `component`, `environment`, `pipeline_stage`, optional `model_run_id`, `case_id`, `alert_id`, `account_id`, and metadata.

## Supported Event Types

- `pipeline`
- `validation`
- `rule_execution`
- `model`
- `case`

## Examples

Pipeline stage:

```python
log_pipeline_event(logger, "Started raw load", "ingestion", "raw_load", "started", context)
```

AML rule execution:

```python
log_rule_event(logger, "Structuring rule completed", "structuring", "completed", context)
```

Model training:

```python
log_model_event(logger, "Isolation Forest training completed", "completed", context)
```

Case generation:

```python
log_case_event(logger, "Case generated", "CA001", "created", context)
```
