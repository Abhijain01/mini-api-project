# Mini API Project

A small FastAPI app that takes a country and a budget in rupees (INR), asks two
public APIs about that country, and tells you what the budget is worth there.
It also stores trips in a Postgres database. It uses
[CountriesNow](https://countriesnow.space) for the currency and capital and
[Frankfurter](https://frankfurter.dev) for today's exchange rate.

## Requirements

- Python 3.12 (to run it without Docker)
- Docker Desktop (to run the app and the database with Docker Compose)

## Run it with Docker (recommended)

```bash
cp .env.example .env        # Windows: copy .env.example .env
docker compose up --build
```

Open http://localhost:8000/docs. The app waits until Postgres is healthy.

| Command | What it does |
|---|---|
| `docker compose up --build -d` | Build and start both services in the background |
| `docker compose logs -f app` | Follow the app's logs |
| `docker compose down` | Stop both services; trips stay in the volume |
| `docker compose down -v` | Stop and delete the data (empty database next time) |

## Run it locally (without the app container)

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Mac/Linux:            source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
docker compose up db -d     # the database still runs in Docker
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs.

## Configuration

Settings are read from environment variables, loaded from `.env`.

| Name | What it controls | Example / default |
|---|---|---|
| `COUNTRIES_API_BASE` | Base URL of CountriesNow (required) | `https://countriesnow.space/api/v0.1/countries` |
| `FRANKFURTER_API_BASE` | Base URL of Frankfurter (required) | `https://api.frankfurter.dev/v2` |
| `REQUEST_TIMEOUT_SECONDS` | Seconds to wait for an outside API | `5` (default) |
| `LOG_LEVEL` | Log verbosity | `INFO` (default) |
| `DATABASE_URL` | Database connection (required). Use host `localhost` when running uvicorn on your laptop; Compose sets host `db` for the app container | `postgresql+psycopg://mini_api:change-me@localhost:5432/mini_api` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credentials and name for the Postgres container (used by Compose) | `mini_api`, `change-me`, `mini_api` |

The app refuses to start if a required setting is missing.

## Endpoints

### `GET /health`
```json
{"status": "ok"}
```

### `GET /countries/{name}`
`GET /countries/japan`
```json
{"name": "Japan", "currency": "JPY", "capital": "Tokyo"}
```

### `GET /roam/{name}?budget_inr=`
`GET /roam/japan?budget_inr=150000`
```json
{"country": "Japan", "currency": "JPY", "rate": 1.7, "budget_inr": 150000.0, "budget_local": 255000.0}
```
(The numbers change with the daily rate.)

### `POST /trips`
Request body: `traveller`, `country`, `budget_inr` (above 0) and `travel_date` (today or later).
```json
{"traveller": "Asha", "country": "Japan", "budget_inr": 150000, "travel_date": "2026-12-20"}
```
Response `201`:
```json
{"id": 1, "traveller": "Asha", "country": "Japan", "currency_code": "JPY", "budget_inr": 150000.0, "travel_date": "2026-12-20", "created_at": "2026-11-17T10:42:00Z"}
```

### `GET /trips`
Lists all trips with each budget at today's rate (one rate per currency per request).
```json
[{"id": 1, "traveller": "Asha", "country": "Japan", "currency_code": "JPY", "budget_inr": 150000.0, "rate": 1.7, "budget_local": 255000.0, "travel_date": "2026-12-20", "created_at": "2026-11-17T10:42:00Z"}]
```
If no rate exists for a trip's currency, `rate` and `budget_local` are `null`.

### `GET /trips/{id}`
Returns one trip (same fields as `POST` response).

### `PATCH /trips/{id}`
Send only the fields to change, for example `{"budget_inr": 200000}`. If `country` changes, the currency is looked up again. Returns the updated trip.

### `DELETE /trips/{id}`
Response `204`, no body.

### Errors

| Case | Status | Example |
|---|---|---|
| Unknown country | 404 | `{"detail": "Country 'Atlantis' not found"}` |
| Trip id does not exist | 404 | `{"detail": "Trip 99999 not found"}` |
| Outside API down or too slow | 503 | `{"detail": "Upstream API unavailable: ..."}` |
| Budget zero or negative, travel date in the past, missing or wrong-type field | 422 | FastAPI validation error |

## Logging

Every request and every outside API call is logged with its status and time,
for example:
```
2026-11-17 10:42:01 | INFO    | Frankfurter GET /rate/INR/JPY -> 200 in 188 ms
2026-11-17 10:42:01 | INFO    | GET /trips -> 200 in 412 ms
```
View them with `docker compose logs -f app`.

## Project structure

```
main.py                        Routes only; turns our errors into 404 and 503
config.py                      Reads settings from .env / environment
exceptions.py                  Our own error types
db.py                          Database engine and the trips table
schemas.py                     Pydantic models: validation for trips
logging_setup.py               loguru configuration
clients/countries_client.py    Adapter for CountriesNow
clients/rates_client.py        Adapter for Frankfurter
repositories/trip_repository.py  All database access for trips
services/travel_service.py     Facade over both clients (/countries, /roam)
services/trip_service.py       Trips: lookup, storage, conversion
docker-compose.yml             App + Postgres
Dockerfile, .dockerignore      Container build
postman/                       Postman collection
```

## Design notes

- **Adapter:** each client class hides one outside API (its URLs and response
  shape) behind simple methods, and raises our own errors instead of HTTP ones.
- **Facade:** `TravelService` and `TripService` combine several parts so a route
  needs one call.
- **Repository:** `TripRepository` is the only class that talks to the database
  and returns plain Python objects. The rest of the app never sees SQL or a
  session, so the database could change without touching the routes or services.
- **Dependency injection:** services receive their clients and repository when
  created, so fakes can be used in tests.
- **Validation:** Pydantic models reject bad input with a 422 before any of our
  code runs, so bad data never reaches the database.