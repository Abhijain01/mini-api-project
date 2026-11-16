# Mini API Project

A small FastAPI app that takes a country and a budget in rupees (INR), asks two
public APIs about that country, and tells you what the budget is worth there.
It uses [CountriesNow](https://countriesnow.space) for the currency and capital
and [Frankfurter](https://frankfurter.dev) for today's exchange rate.

## Requirements

- Python 3.12
- Docker Desktop (only if you want to run it in a container)

## Run it locally

```bash
git clone https://github.com/Abhijain01/mini-api-project.git
cd mini-api-project
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Mac/Linux:            source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs.

## Run it with Docker

```bash
cp .env.example .env        # Windows: copy .env.example .env
docker build -t mini-api-project .
docker run --rm -p 8000:8000 --env-file .env mini-api-project
```

Open http://localhost:8000/docs. Press Ctrl+C to stop. The `.env` file is not
baked into the image, so it must exist before you run the container.
## Configuration

Settings are read from environment variables, loaded from `.env`.

| Name | What it controls | Example / default |
|---|---|---|
| `COUNTRIES_API_BASE` | Base URL of CountriesNow (required) | `https://countriesnow.space/api/v0.1/countries` |
| `FRANKFURTER_API_BASE` | Base URL of Frankfurter (required) | `https://api.frankfurter.dev/v2` |
| `REQUEST_TIMEOUT_SECONDS` | Seconds to wait for an outside API | `5` (default) |

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
{"country": "Japan", "currency": "JPY", "rate": 1.7007, "budget_inr": 150000.0, "budget_local": 255105.0}
```
(The numbers change with the daily rate.)

### Errors

| Case | Status | Example |
|---|---|---|
| Unknown country | 404 | `{"detail": "Country 'Atlantis' not found"}` |
| Outside API down or too slow | 503 | `{"detail": "Upstream API unavailable: ..."}` |
| Budget zero, negative or missing | 422 | FastAPI validation error |

## Project structure

```
main.py                      Routes only; turns our errors into 404 and 503
config.py                    Reads settings from .env / environment
exceptions.py                Our own error types
clients/countries_client.py  Adapter for CountriesNow
clients/rates_client.py      Adapter for Frankfurter
services/travel_service.py   Facade combining both clients
Dockerfile, .dockerignore    Container build
postman/                     Postman collection
```

## Design notes

- **Adapter:** each client class hides one outside API (its URLs and response
  shape) behind simple methods, and raises our own errors instead of HTTP ones.
- **Facade:** `TravelService` combines both clients so a route needs one call.
- **Dependency injection:** the service receives its clients when created, so
  a fake client can be used later in tests.
- **Single responsibility:** each class has one reason to change.