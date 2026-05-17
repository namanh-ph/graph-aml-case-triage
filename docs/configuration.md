# Configuration

The `config/` directory contains declarative YAML settings for the local-first AML analytics project. These files define stable defaults and environment-variable references for later typed loading.

## Files

- `project.yaml`: project metadata, runtime mode, and governance feature flags.
- `paths.yaml`: repository-relative directories and key file paths.
- `database.yaml`: PostgreSQL connection environment variable names, safe defaults, schemas, and table names.
- `neo4j.yaml`: Neo4j connection environment variable names, graph labels, relationship types, load settings, and analytics toggles.
- `rules.yaml`: AML typology thresholds, severity bands, reason templates, and base scores.
- `scoring.yaml`: account and case composite risk weights, severity mappings, and score normalisation defaults.
- `model.yaml`: feature lists, Isolation Forest parameters, optional supervised baselines, evaluation metrics, and MLflow tracking reference.
- `dashboard.yaml`: Streamlit page metadata, table defaults, chart defaults, and filter values.

## Environment Variables

YAML files reference environment variable names such as `POSTGRES_HOST`, `NEO4J_URI`, and `MLFLOW_TRACKING_URI`. Local values are listed in `.env.example`.

Secrets stay in `.env` files rather than YAML so credentials are not committed to version control. YAML files may contain safe local defaults, but passwords and deploy-specific secrets should only come from the environment.

Typed configuration loading reads these YAML files, resolves environment variables where required, validates required fields, and exposes strongly typed settings to future ETL, database, graph, model, scoring, dashboard, and governance modules.

## Typed Loading

YAML files remain the source of declarative configuration. The `graph_aml.config` package loads these files with `yaml.safe_load`, validates structure and values with Pydantic schemas, and exposes a single `AppConfig` object for later modules.

Environment variables resolve local secrets and connection settings through helper functions. These helpers can build PostgreSQL DSNs, Neo4j connection dictionaries, and MLflow tracking URI values without opening any external connections.

Later tickets will use the typed config API for database setup, graph construction, AML rules, scoring, model workflows, dashboard defaults, audit events, and validation artefacts.
