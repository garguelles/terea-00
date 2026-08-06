# Terea Ride API

A Django REST Framework API for managing users, rides, ride events, and
cross-context reports.

## Architecture

The project is organized as a modular monolith. Each Django application owns a
bounded context:

- `apps.users` owns users, authentication behavior, and role authorization.
- `apps.rides` owns rides, ride events, and optimized ride queries.
- `apps.reporting` owns read-only queries that combine application data.
- `common` contains only application-independent infrastructure.
- `config` composes settings and application URLs.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the detailed dependency and design
rules.

## Settings

The available settings modules are:

- `config.settings.local` for local development and `manage.py` commands.
- `config.settings.test` for automated tests.
- `config.settings.production` for ASGI and WSGI deployments.

Copy `.env.example` to `.env` before starting the development services.

```shell
podman compose up
```

The API is available at `http://localhost:8000/api/v1/` and the Django admin at
`http://localhost:8000/admin/`.
