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

Production email uses SMTP. Configure the `DJANGO_DEFAULT_FROM_EMAIL` and
`DJANGO_EMAIL_*` variables documented in `.env.example` before starting an ASGI
or WSGI deployment.

Copy `.env.example` to `.env` before starting the development services.

```shell
podman compose up
```

The API is available at `http://localhost:8000/api/v1/` and the Django admin at
`http://localhost:8000/admin/`.

## Railway

Configure Railway to build the application with `Dockerfile.prod`. The image
runs Gunicorn as a non-root user and automatically binds to Railway's `PORT`
variable. WhiteNoise serves compressed, content-hashed static assets collected
during the image build.

Set the Railway health-check path to `/health/`. Production settings permit
Railway's `healthcheck.railway.app` hostname and exempt only this route from
HTTPS redirection so deployment probes receive a direct `200` response.

Configure these application variables in Railway:

```text
DJANGO_SECRET_KEY=<generated secret>
DJANGO_ALLOWED_HOSTS=<railway or custom domain without https://>
DJANGO_DEFAULT_FROM_EMAIL=<sender address>
DJANGO_EMAIL_HOST=<SMTP host>
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USERNAME=<SMTP username>
DJANGO_EMAIL_PASSWORD=<SMTP password>
DJANGO_EMAIL_USE_TLS=true
DJANGO_EMAIL_USE_SSL=false
```

Map the attached Railway PostgreSQL service variables to the names expected by
the application:

```text
POSTGRES_DB=${{Postgres.PGDATABASE}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
```

Set Railway's pre-deploy command to:

```shell
python manage.py migrate
```

Production sends a one-year HSTS policy that includes subdomains and the preload
directive. Railway provides HTTPS for Railway and custom domains, but verify
that every subdomain of a custom domain supports HTTPS before using that domain.
The HSTS variables in `.env.example` can be reduced during a staged rollout.
