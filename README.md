# dev-services

A personal toolbox of reusable, project-agnostic Docker services for local development.

The idea: instead of installing MySQL, PostgreSQL, Redis, etc. directly on your machine, you spin them up on demand as Docker containers and connect to them from `localhost`. Your applications (e.g. a Laravel app) keep running directly on the host — only the databases/caches live in containers. This repo is not tied to any specific project; it's just infrastructure you keep around and reuse across all of them.

Each service is independent: you start only what you need (e.g. just Postgres), and it doesn't affect the others.

## Prerequisites

- [Docker Engine](https://docs.docker.com/engine/install/)
- The Docker Compose plugin (`docker compose version` should work)

## Setup

Copy the example environment file and adjust values if you want non-default credentials/ports:

```bash
cp .env.example .env
```

`.env` is gitignored, so your local credentials never get committed.

## Starting and stopping services

Each service lives behind its own Compose [profile](https://docs.docker.com/compose/profiles/), so you can start only what you need.

**Postgres**

```bash
docker compose --profile postgres up -d
docker compose --profile postgres down
```

**MySQL**

```bash
docker compose --profile mysql up -d
docker compose --profile mysql down
```

**Redis**

```bash
docker compose --profile redis up -d
docker compose --profile redis down
```

You can also start more than one at a time by repeating `--profile`:

```bash
docker compose --profile postgres --profile redis up -d
```

Data for Postgres and MySQL is stored in named Docker volumes, so it persists across `down`/`up` cycles. To wipe a service's data, remove its volume explicitly (e.g. `docker volume rm dev-services_postgres_data`).

## Connecting from a host application

All services bind only to `127.0.0.1`, so they're reachable from your host machine but not from other devices on your network.

| Service  | Host        | Default port | Credentials/env vars |
|----------|-------------|---------------|-----------------------|
| Postgres | `127.0.0.1` | `5432`        | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| MySQL    | `127.0.0.1` | `3306`        | `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` (or `MYSQL_ROOT_PASSWORD` for root) |
| Redis    | `127.0.0.1` | `6379`        | none by default |

Use the values you set in your `.env` file (or the defaults from `.env.example` if you didn't change them) when configuring your application's database/cache connection.

## Adding new services

To add another service later (e.g. MongoDB), follow the same pattern in `docker-compose.yml`:

1. Add a new service block with its own `profiles: ["name"]` entry.
2. Bind its port(s) to `127.0.0.1` using an environment variable, e.g. `"127.0.0.1:${MONGO_PORT:-27017}:27017"`.
3. Add a named volume if it needs persistent data.
4. Add the corresponding environment variables (with defaults) to `.env.example`.

That's it — the new service can then be started independently with `docker compose --profile name up -d`.
