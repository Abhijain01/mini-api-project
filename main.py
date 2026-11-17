"""Routes only: read the request, call a service, return the result."""

import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse
from loguru import logger

from clients.countries_client import CountriesClient
from clients.rates_client import RatesClient
from config import load_settings
from db import Database
from exceptions import NotFoundError, UpstreamError
from logging_setup import setup_logging
from repositories.trip_repository import TripRepository
from schemas import TripCreate, TripOut, TripUpdate, TripWithRate
from services.travel_service import TravelService
from services.trip_service import TripService

# Fails at startup, naming the setting, if one is missing.
settings = load_settings()
setup_logging(settings.log_level)

countries_client = CountriesClient(settings.countries_api_base, settings.request_timeout)
rates_client = RatesClient(settings.frankfurter_api_base, settings.request_timeout)
service = TravelService(countries=countries_client, rates=rates_client)

database = Database(settings.database_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.create_tables()
    yield


app = FastAPI(title="Mini API Project", lifespan=lifespan)


def get_trip_service(session=Depends(database.session)) -> TripService:
    return TripService(TripRepository(session), countries_client, rates_client)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        ms = (time.perf_counter() - started) * 1000
        logger.exception(f"{request.method} {request.url.path} -> unhandled error in {ms:.0f} ms")
        raise
    ms = (time.perf_counter() - started) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} in {ms:.0f} ms")
    return response


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


@app.post("/trips", response_model=TripOut, status_code=201)
def create_trip(body: TripCreate, trips: TripService = Depends(get_trip_service)):
    return trips.create_trip(**body.model_dump())


@app.get("/trips", response_model=list[TripWithRate])
def list_trips(trips: TripService = Depends(get_trip_service)):
    return trips.list_trips()


@app.get("/trips/{trip_id}", response_model=TripOut)
def get_trip(trip_id: int, trips: TripService = Depends(get_trip_service)):
    return trips.get_trip(trip_id)


@app.patch("/trips/{trip_id}", response_model=TripOut)
def update_trip(
    trip_id: int, body: TripUpdate, trips: TripService = Depends(get_trip_service)
):
    return trips.update_trip(trip_id, body.model_dump(exclude_unset=True))


@app.delete("/trips/{trip_id}", status_code=204)
def delete_trip(trip_id: int, trips: TripService = Depends(get_trip_service)) -> Response:
    trips.delete_trip(trip_id)
    return Response(status_code=204)