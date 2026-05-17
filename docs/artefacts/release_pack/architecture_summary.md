# Architecture Summary

- PostgreSQL stores raw, staging, mart, AML, and governance records.
- Neo4j supports graph loading and graph analytics for network context.
- AML rules create deterministic alerts from configured typologies.
- Graph analytics and feature persistence enrich account and case context.
- ML scoring combines anomaly detection, supervised outputs, and risk scoring.
- Case triage links alerts, entities, evidence packs, lifecycle actions, and audit records.
- The Streamlit dashboard presents operations, model metrics, audit, and validation pages.
- Governance inventory records lineage, artefacts, model inventory, and validation inventory.
- Security controls classify sensitive fields, sanitise exports, and validate audit integrity.
