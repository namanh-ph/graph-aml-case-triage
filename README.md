# Graph-Based AML Case Triage And Risk Scoring System


## Overview

This is a financial crime analytics project for detecting, explaining, and prioritising suspicious financial activity across a synthetic banking transaction portfolio. In this project, AML alerts, graph-based risk signals, anomaly scores, investigation cases, and triage outputs from trandaction data.

  

## Features

- Bronze / Silver / Gold data architecture with DVC-tracked lineage

- Reference banking dataset with labelled positives across six AML typologies (structuring, fan-in, fan-out, rapid movement, circular flow, dormant reactivation)

- Ingestion, staging, and Pandera schema validation across all three data layers

- Account, behavioural, jurisdiction, and graph-based feature engineering

- AML rule engine, Isolation Forest anomaly scoring, and composite account risk scoring

- Graph analytics on a customer-account-transaction-counterparty network (NetworkX + Neo4j)

- Case generation, case risk scoring, evidence packs, and deterministic explanations

- Analyst lifecycle workflows for assignment, status changes, closure, and feedback labels

- Supervised baseline modelling with comparison, threshold calibration, monitoring, drift validation, and model cards

- Streamlit dashboard for alerts, cases, accounts, graph, model metrics, audit, and validation views

- MLflow tracking of input datasets and model runs

  

## Tech Stack

- Language: Python (uv, Makefile)

- Storage: Apache Parquet (DVC-versioned), PostgreSQL, Neo4j

- Analytics: Polars, DuckDB, pandas, NetworkX

- ML: scikit-learn (Isolation Forest, Logistic Regression, Random Forest), MLflow

- Validation: Pandera, Pydantic

- Dashboard: Streamlit

- Infrastructure: Docker Compose

- Quality: pytest, ruff, mypy