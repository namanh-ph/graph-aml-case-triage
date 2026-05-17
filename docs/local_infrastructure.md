# Local Infrastructure

Docker Compose provides reproducible local infrastructure for PostgreSQL, Neo4j, and optional MLflow. These services are infrastructure only; application schemas, database clients, graph loading, and model workflows are implemented in later tickets.

## Setup

```bash
cp .env.example .env
make services-up
make services-ps
make services-logs
make services-down
```

## PostgreSQL

- Host: `localhost`
- Port: `5432`
- Database: `graph_aml`
- User: `graph_aml_user`
- Password: from `POSTGRES_PASSWORD` in `.env`

The service stores data in the named Docker volume `postgres_data`.

## Neo4j

- Browser: `http://localhost:7474`
- Bolt URI: `bolt://localhost:7687`
- User: `neo4j`
- Password: from `NEO4J_PASSWORD` in `.env`

Neo4j persists data, logs, import files, and plugins in named Docker volumes.

## MLflow

MLflow is optional and starts only with the `mlflow` profile:

```bash
make mlflow-up
```

When enabled, the MLflow UI runs at `http://localhost:5000`. The current Python config defaults to local file tracking with `mlruns`; set `MLFLOW_TRACKING_URI=http://localhost:5000` when using the optional service.

## Service Commands

```bash
make services-up
make postgres-up
make neo4j-up
make mlflow-up
make services-ps
make services-logs
make services-down
```

## Resetting Volumes

This command is destructive. It removes local PostgreSQL, Neo4j, and MLflow state stored in Docker volumes:

```bash
docker compose down -v
```

Use it only when you intentionally want to reset local infrastructure state.
