import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

load_dotenv()

COUNTRIES_BASE = os.getenv(
    "COUNTRIES_API_BASE", "https://countriesnow.space/api/v0.1/countries"
).rstrip("/")
FRANKFURTER_BASE = os.getenv(
    "FRANKFURTER_API_BASE", "https://api.frankfurter.dev/v2"
).rstrip("/")

# A slow API must never hang our app.
TIMEOUT = httpx.Timeout(5.0)

app = FastAPI(title="Mini API Project")


class UpstreamError(Exception):
    """An upstream API is down, too slow, or returned something unusable."""


class NotFound(Exception):
    """The upstream API says the thing we asked for doesn't exist."""


def _get_json(url: str) -> dict:
    try:
        resp = httpx.get(url, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise UpstreamError(f"could not reach {url}: {exc.__class__.__name__}") from exc

    if resp.status_code in (400, 404, 422):
        raise NotFound()
    if resp.status_code >= 400:
        raise UpstreamError(f"{url} returned HTTP {resp.status_code}")

    try:
        return resp.json()
    except ValueError as exc:
        raise UpstreamError(f"{url} returned invalid JSON") from exc


def _countries_data(endpoint: str, name: str) -> dict:
    # Always the /q version: without it CountriesNow redirects and httpx
    # does not follow redirects by default.
    url = f"{COUNTRIES_BASE}/{endpoint}/q"
    try:
        resp = httpx.get(url, params={"country": name}, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise UpstreamError(f"could not reach CountriesNow: {exc.__class__.__name__}") from exc

    try:
        body = resp.json()
    except ValueError:
        body = None

    if isinstance(body, dict) and body.get("error") is True:
        msg = str(body.get("msg", "")).lower()
        if resp.status_code == 404 or "not found" in msg:
            raise NotFound()
        raise UpstreamError(f"CountriesNow error: {body.get('msg')}")
    if resp.status_code == 404:
        raise NotFound()
    if resp.status_code >= 400 or not isinstance(body, dict):
        raise UpstreamError(f"CountriesNow returned HTTP {resp.status_code}")

    data = body.get("data")
    if not isinstance(data, dict):
        raise UpstreamError("CountriesNow returned an unexpected response")
    return data


def get_country_info(name: str) -> dict:
    try:
        cur = _countries_data("currency", name)
        cap = _countries_data("capital", name)
    except NotFound:
        raise HTTPException(status_code=404, detail=f"Country '{name}' not found")
    except UpstreamError as exc:
        raise HTTPException(status_code=503, detail=f"Upstream API unavailable: {exc}")

    return {
        "name": cur.get("name") or cap.get("name") or name,
        "currency": cur.get("currency"),
        "capital": cap.get("capital"),
    }


def get_rate(base: str, quote: str) -> float:
    try:
        data = _get_json(f"{FRANKFURTER_BASE}/rate/{base}/{quote}")
    except NotFound:
        raise HTTPException(
            status_code=404, detail=f"No exchange rate available for {base}/{quote}"
        )
    except UpstreamError as exc:
        raise HTTPException(status_code=503, detail=f"Upstream API unavailable: {exc}")

    rate = data.get("rate")
    if not isinstance(rate, (int, float)):
        raise HTTPException(
            status_code=503, detail="Upstream API unavailable: no rate in response"
        )
    return float(rate)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/countries/{name}")
def country(name: str) -> dict:
    return get_country_info(name)


@app.get("/roam/{name}")
def roam(
    name: str,
    budget_inr: float = Query(..., gt=0, description="Budget in rupees, must be > 0"),
) -> dict:
    info = get_country_info(name)
    currency = info["currency"]
    if not currency:
        raise HTTPException(
            status_code=404, detail=f"No currency found for '{info['name']}'"
        )

    rate = get_rate("INR", currency)
    return {
        "country": info["name"],
        "currency": currency,
        "rate": rate,
        "budget_inr": budget_inr,
        "budget_local": round(budget_inr * rate, 2),
    }