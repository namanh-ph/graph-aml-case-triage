# Database Utilities

The database utility layer provides controlled PostgreSQL connection, health check, SQL execution, and initialisation helpers. It uses SQLAlchemy and the existing typed configuration system.

## Database URLs

Database URLs are built from `config/database.yaml` plus environment variables. The typed config provides defaults such as `localhost`, port `5432`, database `graph_aml`, and user `graph_aml_user`. Runtime values come from `.env` or the process environment.

## Engines and Sessions

`create_database_engine()` creates a SQLAlchemy engine with pool settings from typed config. It does not connect at import time and does not create a global engine.

`session_scope()` provides a transactional session context: commit on success, rollback on exception, and close in all cases.

## SQL Execution

`execute_sql()` and `execute_sql_file()` execute trusted local SQL artefacts inside a transaction. The current initialisation path uses:

- `001_create_schemas.sql`
- `003_create_core_tables.sql`

## Health Checks

Health helpers support:

- `SELECT 1` connectivity checks
- PostgreSQL server version lookup
- existing schema listing
- existing table listing by schema

## Initialisation

`initialise_database()` creates schemas first and core tables second. It is idempotent because the SQL artefacts use `IF NOT EXISTS`.

```bash
cp .env.example .env
make services-up
make db-check
make db-init
make db-list-schemas
```

## Reset Workflow

`reset_database(engine, confirm=True)` runs the destructive local reset workflow:

1. delete core tables through `004_drop_core_tables.sql`
2. delete project schemas through `002_drop_schemas.sql`
3. recreate schemas through `001_create_schemas.sql`
4. recreate core tables through `003_create_core_tables.sql`

The CLI requires an explicit confirmation flag:

```bash
make db-reset
```

## Smoke Seed Workflow

`seed_smoke_data(engine)` inserts a deterministic, tiny dataset for local checks. It includes
countries, customers, accounts, transactions, features, graph features, alerts, one case, audit
events, one model run, and one validation report.

```bash
make db-seed-smoke
make db-recreate-and-seed
```

The smoke seed uses deterministic IDs such as `CUST_SMOKE_001`, `TXN_SMOKE_001`, and
`CASE_SMOKE_001`. It is idempotent and safe to run repeatedly.

## Smoke Seed Cleanup

`delete_smoke_seed_data(engine, confirm=True)` deletes only deterministic smoke seed records using
targeted `DELETE` statements. It does not remove schemas, table definitions, or non-smoke data.

```bash
make db-delete-smoke-seed
```

## Destructive Command Safeguards

Reset and smoke seed cleanup require explicit confirmation internally. The CLI exposes this through
`--yes`, and the Makefile targets pass that flag deliberately. Seed insertion itself is not
destructive.

## Integration Tests

Unit tests do not require PostgreSQL. Optional smoke tests require a running local PostgreSQL service:

```bash
RUN_DATABASE_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_postgres_connection_smoke.py
RUN_DATABASE_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_postgres_reset_and_seed_smoke.py
```

## Excluded From This Ticket

Destructive reset and seed commands are intentionally excluded. They will be added separately so reset behaviour can be reviewed and tested independently.
