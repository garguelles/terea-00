# Terea Ride API

A Django REST Framework API for managing users, rides, and ride events. It
includes an optimized Ride List endpoint and the assessment's bonus report as a
documented PostgreSQL statement.

## Prerequisites

- Podman with the Compose plugin.
- Loopback ports `8000`, `5432`, and `8081` available for Django, PostgreSQL,
  and pgweb.

The container image installs the supported Python 3.14 and Django 6.0 runtime
from the locked project dependencies.

## Local Setup

Create the local environment file, build the services, and initialize the
database:

```shell
cp .env.example .env
podman compose up --build -d
podman compose exec web python manage.py migrate
podman compose exec web python manage.py createsuperuser
```

The custom `createsuperuser` prompt requests email, first name, last name, phone
number, and password. Use `admin@example.com` to follow the examples below. The
command automatically creates a user with `role=admin`, `is_staff=true`, and
`is_superuser=true`.

The local services are:

| Service | URL or address | Access |
| --- | --- | --- |
| API prefix | `http://localhost:8000/api/v1/` | HTTP Basic authentication |
| Health check | `http://localhost:8000/health/` | No authentication; `GET` and `HEAD` only |
| Django admin | `http://localhost:8000/admin/` | Django staff account |
| PostgreSQL | `localhost:5432` | Credentials from `.env` |
| pgweb | `http://localhost:8081/` | Local database browser |

`/api/v1/` is a URL prefix, not a browsable API-root response. Stop the services
without deleting database data with:

```shell
podman compose down
```

### Environment

`.env.example` contains development-only defaults. Compose binds all published
ports to `127.0.0.1`; do not expose these credentials or services to an
untrusted network. Do not commit `.env` or production credentials.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django signing secret; replace outside local development |
| `DJANGO_DEBUG` | Enables local debug mode when `true` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames without schemes |
| `POSTGRES_DB` | PostgreSQL database name |
| `POSTGRES_USER` | PostgreSQL user |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_HOST` | PostgreSQL host; `db` inside Compose |
| `POSTGRES_PORT` | PostgreSQL port |
| `DJANGO_DEFAULT_FROM_EMAIL` | Production sender address |
| `DJANGO_EMAIL_*` | Production SMTP connection and TLS settings |
| `DJANGO_SECURE_HSTS_*` | Production HSTS duration and subdomain/preload policy |

The available settings modules are `config.settings.local` for development,
`config.settings.test` for tests, and `config.settings.production` for ASGI and
WSGI deployments. Production requires SMTP configuration; local development
uses the console email backend.

## Authentication

The API uses HTTP Basic authentication with the user's email address as the
username. Every API resource requires an active user whose `role` is `admin`.
The application role is deliberately independent from Django's `is_staff` flag:
an active role-admin can use the API without staff access, while a staff user
without the admin role cannot.

Basic authentication transmits reusable credentials with every request. The
local examples use loopback HTTP only; any non-local deployment must use HTTPS.

For example, `curl -u` prompts for the password without putting it in shell
history:

```shell
curl -u 'admin@example.com' http://localhost:8000/api/v1/rides/
```

Authentication outcomes are:

| Condition | Status |
| --- | --- |
| Missing or invalid credentials | `401 Unauthorized` with `WWW-Authenticate: Basic realm="api"` |
| Inactive account | `401 Unauthorized` |
| Authenticated user without `role=admin` | `403 Forbidden` |
| Active user with `role=admin` | Request proceeds |

## API Contract

All resource routes support JSON requests and responses.

| Route | Methods |
| --- | --- |
| `/api/v1/users/` | `GET`, `POST` |
| `/api/v1/users/{id_user}/` | `GET`, `PUT`, `PATCH`, `DELETE` |
| `/api/v1/rides/` | `GET`, `POST` |
| `/api/v1/rides/{id_ride}/` | `GET`, `PUT`, `PATCH`, `DELETE` |
| `/api/v1/ride-events/` | `GET`, `POST` |
| `/api/v1/ride-events/{id_ride_event}/` | `GET`, `PUT`, `PATCH`, `DELETE` |

Successful creates return `201 Created`, reads and updates return `200 OK`, and
deletes return `204 No Content`.

### Resources

User fields are `id_user`, `role`, `first_name`, `last_name`, `email`,
`phone_number`, and `is_active`. `role` is one of `admin`, `rider`, or `driver`.
`password` is required when creating a user and optional when updating one; it is
validated, hashed, write-only, and never returned.

Create a rider:

```shell
curl -u 'admin@example.com' \
  -H 'Content-Type: application/json' \
  -d '{
    "role": "rider",
    "first_name": "Riley",
    "last_name": "Stone",
    "email": "rider@example.com",
    "phone_number": "+15550100",
    "password": "Rider-passphrase-917!"
  }' \
  http://localhost:8000/api/v1/users/
```

Create a driver in the same way and record the `id_user` values returned by both
responses:

```shell
curl -u 'admin@example.com' \
  -H 'Content-Type: application/json' \
  -d '{
    "role": "driver",
    "first_name": "Dana",
    "last_name": "Cole",
    "email": "driver@example.com",
    "phone_number": "+15550200",
    "password": "Driver-passphrase-917!"
  }' \
  http://localhost:8000/api/v1/users/
```

Ride fields are `id_ride`, `status`, `id_rider`, `id_driver`,
`pickup_latitude`, `pickup_longitude`, `dropoff_latitude`,
`dropoff_longitude`, and `pickup_time`. `status` is one of `en-route`, `pickup`,
or `dropoff`. `id_rider` must identify a user with the rider role, and
`id_driver` must identify a user with the driver role. Coordinates must be finite;
latitudes are in `[-90, 90]` and longitudes in `[-180, 180]`.

Create a ride after creating rider and driver users:

```shell
curl -u 'admin@example.com' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "en-route",
    "id_rider": <id_rider>,
    "id_driver": <id_driver>,
    "pickup_latitude": 37.7749,
    "pickup_longitude": -122.4194,
    "dropoff_latitude": 37.6213,
    "dropoff_longitude": -122.3790,
    "pickup_time": "2026-08-10T14:30:00Z"
  }' \
  http://localhost:8000/api/v1/rides/
```

RideEvent fields are `id_ride_event`, `id_ride`, `description`, and
`created_at`. The server generates the read-only `created_at` timestamp.

```shell
curl -u 'admin@example.com' \
  -H 'Content-Type: application/json' \
  -d '{"id_ride": <id_ride>, "description": "Status changed to pickup"}' \
  http://localhost:8000/api/v1/ride-events/
```

Replace angle-bracket placeholders with identifiers returned by preceding
requests. The following commands exercise list, retrieve, full update, partial
update, and delete routes. A `PUT` sends the complete writable representation.

```shell
curl -u 'admin@example.com' http://localhost:8000/api/v1/users/
curl -u 'admin@example.com' http://localhost:8000/api/v1/users/<id_rider>/
curl -u 'admin@example.com' -X PUT -H 'Content-Type: application/json' \
  -d '{
    "role":"rider",
    "first_name":"Riley",
    "last_name":"Stone",
    "email":"rider@example.com",
    "phone_number":"+15550101",
    "is_active":true
  }' http://localhost:8000/api/v1/users/<id_rider>/
curl -u 'admin@example.com' -X PATCH -H 'Content-Type: application/json' \
  -d '{"phone_number":"+15550101"}' \
  http://localhost:8000/api/v1/users/<id_rider>/

curl -u 'admin@example.com' http://localhost:8000/api/v1/rides/<id_ride>/
curl -u 'admin@example.com' -X PUT -H 'Content-Type: application/json' \
  -d '{
    "status":"pickup",
    "id_rider":<id_rider>,
    "id_driver":<id_driver>,
    "pickup_latitude":37.7749,
    "pickup_longitude":-122.4194,
    "dropoff_latitude":37.6213,
    "dropoff_longitude":-122.3790,
    "pickup_time":"2026-08-10T14:30:00Z"
  }' http://localhost:8000/api/v1/rides/<id_ride>/
curl -u 'admin@example.com' -X PATCH -H 'Content-Type: application/json' \
  -d '{"status":"pickup"}' http://localhost:8000/api/v1/rides/<id_ride>/

curl -u 'admin@example.com' http://localhost:8000/api/v1/ride-events/
curl -u 'admin@example.com' \
  http://localhost:8000/api/v1/ride-events/<id_ride_event>/
curl -u 'admin@example.com' -X PUT -H 'Content-Type: application/json' \
  -d '{"id_ride":<id_ride>,"description":"Status changed to dropoff"}' \
  http://localhost:8000/api/v1/ride-events/<id_ride_event>/
curl -u 'admin@example.com' -X PATCH -H 'Content-Type: application/json' \
  -d '{"description":"Status changed to dropoff"}' \
  http://localhost:8000/api/v1/ride-events/<id_ride_event>/

curl -u 'admin@example.com' -X DELETE \
  http://localhost:8000/api/v1/ride-events/<id_ride_event>/
curl -u 'admin@example.com' -X DELETE \
  http://localhost:8000/api/v1/rides/<id_ride>/
curl -u 'admin@example.com' -X DELETE \
  http://localhost:8000/api/v1/users/<id_rider>/
```

Delete dependent events before their ride, and delete rides before their users.
The collection `GET` examples for users and RideEvents above complement the Ride
List examples below.

All list routes use page-number pagination with a default page size of 20 and a
maximum requested page size of 100:

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

Use `page` and `page_size` to navigate results. The Ride List validates these as
a positive page number and a page size from 1 through 100.

### Errors

| Condition | Status and response |
| --- | --- |
| Body or query validation failure | `400 Bad Request`; errors are keyed by field or `non_field_errors` |
| Malformed JSON | `400 Bad Request`; response contains `detail` |
| Missing resource | `404 Not Found` |
| User assigned to a ride | `409 Conflict`: `{"detail":"This user is assigned to one or more rides."}` |
| Ride with existing events | `409 Conflict`: `{"detail":"This ride has one or more ride events."}` |

The conflict responses protect historical ride and event records from cascading
deletion.

## Ride List

`GET /api/v1/rides/` returns each ride with `id_rider`, `id_driver`, and
`todays_ride_events`. The collection contains only events whose `created_at` is
in the inclusive interval `[current time - 24 hours, current time]`. Events are
ordered by newest timestamp and then highest event ID. Without explicit sorting,
rides are ordered by ascending ride ID.

Ride detail, create, and update responses use the base Ride representation and
therefore do not contain `todays_ride_events`. Complete event history remains
available as paginated RideEvent resources at `/api/v1/ride-events/`. The
assessment also asks for related RideEvents while prohibiting the Ride List from
loading full event history; this implementation treats `todays_ride_events` as
the list's related-event collection to satisfy both requirements.

The Ride List accepts:

| Parameter | Contract |
| --- | --- |
| `status` | `en-route`, `pickup`, or `dropoff` |
| `rider_email` | Valid email; normalized to lowercase before exact lookup |
| `sort_by` | `pickup_time` or `distance`; requires `sort_order` |
| `sort_order` | `asc` or `desc`; requires `sort_by` |
| `pickup_latitude` | Finite value from `-90` to `90` |
| `pickup_longitude` | Finite value from `-180` to `180` |
| `page` | Positive integer |
| `page_size` | Integer from 1 through 100; default 20 |

Distance sorting requires both coordinates. Coordinates must be supplied as a
pair and are rejected unless `sort_by=distance`. Filters can be combined with
either sorting mode. Filtering, annotation, ordering, and pagination happen in
PostgreSQL. Both ascending and descending modes apply the same direction to the
ride ID tie-breaker, keeping equal values stable across pages.

```shell
curl -u 'admin@example.com' \
  'http://localhost:8000/api/v1/rides/?status=pickup&rider_email=rider@example.com&sort_by=pickup_time&sort_order=desc&page=1&page_size=20'

curl -u 'admin@example.com' \
  'http://localhost:8000/api/v1/rides/?sort_by=distance&sort_order=asc&pickup_latitude=37.7749&pickup_longitude=-122.4194&page=1&page_size=20'
```

### Performance

The Ride List selector joins rider and driver with `select_related` and uses a
filtered `Prefetch` with `to_attr="todays_ride_events"`. The dedicated attribute
prevents serialization from evaluating the unfiltered `ride_events` reverse
manager. A page therefore performs two data queries: one for rides with joined
users and one for all recent events on the page. Pagination adds one count query,
and the query count remains constant as page contents grow.

Distance is calculated in kilometers using a clamped great-circle expression.
PostgreSQL calculates and orders it before pagination, so rides are never loaded
and sorted in Python. The assessment fixes the Ride schema and prohibits storing
trip distance. Without spatial columns and an index, PostgreSQL must calculate
distance for every ride remaining after filters. A production system at larger
scale should use an indexed geospatial type such as PostGIS `geography`, or
persist an appropriate derived location representation.

## Architecture

The project is organized as a modular monolith. Each Django application owns a
bounded context:

- `apps.users` owns users, authentication behavior, and role authorization.
- `apps.rides` owns rides, ride events, and optimized ride queries.
- `apps.reporting` reserves the boundary for future executable cross-context
  read models; this assessment adds no reporting endpoint.
- `common` contains only application-independent infrastructure.
- `config` composes settings and application URLs.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the detailed dependency and design
rules.

The performance-sensitive read flow is:

```text
RideViewSet.list
  -> RideListQuerySerializer
  -> apps.rides.selectors.ride_list_queryset
  -> PostgreSQL and DefaultPagination
  -> RideListSerializer
```

The view is a thin HTTP adapter: it validates query parameters, invokes the
selector, paginates, and serializes. Query construction, joins, filtering,
annotations, prefetching, and ordering remain in `apps.rides.selectors`.
Transport validation and representation remain in API serializers. Shared
page-number mechanics live in `common.pagination`, and the reusable role policy
lives in `apps.users.api.permissions`.

Simple CRUD uses DRF `ModelViewSet` and `ModelSerializer` directly. The users and
rides service modules are intentionally empty because there is no multi-step
command workflow requiring orchestration or a transaction boundary. The bonus
SQL remains documentation because the assessment requests a raw statement, not
an executable report. If reporting behavior is added later, it belongs as a
read-only projection in `apps.reporting`.

### Design Decisions

- Assessment-compatible API and database names are retained while Django model
  attributes follow framework conventions.
- API authorization uses the explicit application role rather than conflating
  it with Django admin-site access.
- Rider and driver assignments are validated against their respective roles.
- User and ride deletion uses protected foreign keys to preserve history.
- RideEvent timestamps are server-owned to provide trustworthy event ordering.
- Recent events use a filtered prefetch instead of loading complete history.
- Distance ordering uses PostgreSQL expressions because the fixed schema cannot
  store distance or add a geospatial location column.
- Stable primary-key tie-breakers prevent records moving between pages when sort
  values are equal.

### Requirement Traceability

| Requirement | Implementation | Verification |
| --- | --- | --- |
| User, Ride, and RideEvent schema | `apps.users.models`, `apps.rides.models`, migrations | Application model tests |
| JSON conversion and CRUD ViewSets | Application API serializers, views, and routers | Serializer and API tests |
| Active admin-role access only | `IsActiveAdminRole`, HTTP Basic authentication | `apps.users.tests.test_permissions` |
| Paginated Ride List with related IDs | `RideViewSet.list`, `DefaultPagination`, `RideListSerializer` | Ride API tests |
| Status and rider-email filters | `RideListQuerySerializer`, rides selector | Serializer, selector, and API tests |
| Pickup-time and distance ordering | PostgreSQL ordering and distance annotation in the rides selector | Selector and API sorting tests |
| Last-24-hour events without full history | Filtered `Prefetch` with `to_attr` | Boundary and full-history exclusion tests |
| Two data queries, three with count | Joined ride query plus event prefetch | Constant query-count selector and API tests |
| Trips over one hour by month and driver | README PostgreSQL statement | SQL reviewed against the schema and documented edge-case policy |

## Bonus SQL Report

The following PostgreSQL statement counts trips lasting strictly longer than one
hour, grouped by the UTC month in which pickup occurred and by driver:

```sql
WITH first_pickups AS (
    SELECT DISTINCT ON (event.id_ride)
        event.id_ride,
        event.created_at AS pickup_at
    FROM rides_rideevent AS event
    WHERE event.description = 'Status changed to pickup'
    ORDER BY event.id_ride, event.created_at, event.id_ride_event
),
completed_trips AS (
    SELECT
        pickup.id_ride,
        pickup.pickup_at,
        dropoff.dropoff_at
    FROM first_pickups AS pickup
    CROSS JOIN LATERAL (
        SELECT event.created_at AS dropoff_at
        FROM rides_rideevent AS event
        WHERE event.id_ride = pickup.id_ride
          AND event.description = 'Status changed to dropoff'
          AND event.created_at > pickup.pickup_at
        ORDER BY event.created_at, event.id_ride_event
        LIMIT 1
    ) AS dropoff
)
SELECT
    to_char(
        date_trunc('month', trip.pickup_at AT TIME ZONE 'UTC'),
        'YYYY-MM'
    ) AS month,
    concat_ws(' ', driver.first_name, left(driver.last_name, 1)) AS driver,
    count(*) AS trips_over_one_hour
FROM completed_trips AS trip
JOIN rides_ride AS ride ON ride.id_ride = trip.id_ride
JOIN users_user AS driver ON driver.id_user = ride.id_driver
WHERE trip.dropoff_at - trip.pickup_at > INTERVAL '1 hour'
GROUP BY
    date_trunc('month', trip.pickup_at AT TIME ZONE 'UTC'),
    driver.id_user,
    driver.first_name,
    driver.last_name
ORDER BY
    date_trunc('month', trip.pickup_at AT TIME ZONE 'UTC'),
    driver.first_name,
    driver.last_name,
    driver.id_user;
```

A ride contributes at most once. When duplicate status events exist, the query
chooses the earliest pickup, using the event ID to break timestamp ties, and
pairs it with the earliest dropoff whose timestamp is strictly later. Dropoffs
before or at pickup are therefore ignored, and a missing later dropoff excludes
the ride. The strict interval comparison also excludes trips lasting exactly one
hour.

Django stores aware timestamps in PostgreSQL and this project uses UTC. Duration
is calculated between the stored instants, while `AT TIME ZONE 'UTC'` makes the
month boundary explicit. Driver ID is retained in the grouping and final ordering
so different users with identical names are never combined; the displayed value
matches the abbreviated names in the assessment's sample report.

## Verification

The test suite runs against PostgreSQL so database functions and query behavior
match the application environment:

```shell
podman compose config --quiet
podman compose exec web python manage.py check
podman compose exec web python manage.py makemigrations --check --dry-run
podman compose exec \
  -e DJANGO_SETTINGS_MODULE=config.settings.test \
  web python manage.py test
```

The suite covers models, constraints, password handling, permissions, CRUD,
validation errors, filtering, ordering, pagination, recent-event boundaries,
full-history exclusion, and constant Ride List query counts.

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
