"""Routes only: read the request, call the service, return the result."""

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from clients.countries_client import CountriesClient
from clients.rates_client import RatesClient
from config import load_settings
from exceptions import NotFoundError, UpstreamError
from services.travel_service import TravelService

# Fails at startup, naming the setting, if one is missing.
settings = load_settings()

service = TravelService(
    countries=CountriesClient(settings.countries_api_base, settings.request_timeout),
    rates=RatesClient(settings.frankfurter_api_base, settings.request_timeout),
)

app = FastAPI(title="Mini API Project")


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(UpstreamError)
async def upstream_handler(request: Request, exc: UpstreamError) -> JSONResponse:
    return JSONResponse(
        status_code=503, content={"detail": f"Upstream API unavailable: {exc}"}
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/countries/{name}")
def country(name: str) -> dict:
    return service.get_country(name)


@app.get("/roam/{name}")
def roam(
    name: str,
    budget_inr: float = Query(..., gt=0, description="Budget in rupees, must be > 0"),
) -> dict:
    return service.convert_budget(name, budget_inr)