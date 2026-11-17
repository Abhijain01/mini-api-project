"""Adapter for the CountriesNow API.

Hides its URLs and response shapes behind two simple methods and logs every
call. Knows nothing about FastAPI or HTTP status codes.
"""

import time
from dataclasses import dataclass

import httpx
from loguru import logger

from exceptions import CountryNotFoundError, UpstreamError


@dataclass(frozen=True)
class CurrencyInfo:
    name: str | None
    code: str | None


@dataclass(frozen=True)
class CapitalInfo:
    name: str | None
    capital: str | None


class CountriesClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout)

    def get_currency(self, country: str) -> CurrencyInfo:
        data = self._get_data("currency", country)
        return CurrencyInfo(name=data.get("name"), code=data.get("currency"))

    def get_capital(self, country: str) -> CapitalInfo:
        data = self._get_data("capital", country)
        return CapitalInfo(name=data.get("name"), capital=data.get("capital"))

    def _get_data(self, endpoint: str, country: str) -> dict:
        # Always the /q version: without it CountriesNow redirects and httpx
        # does not follow redirects by default.
        path = f"/{endpoint}/q"
        started = time.perf_counter()
        try:
            resp = httpx.get(
                f"{self._base_url}{path}", params={"country": country}, timeout=self._timeout
            )
        except httpx.HTTPError as exc:  # timeouts, connection errors, ...
            ms = (time.perf_counter() - started) * 1000
            reason = "timeout" if isinstance(exc, httpx.TimeoutException) else exc.__class__.__name__
            logger.warning(f"CountriesNow GET {path} -> {reason} after {ms:.0f} ms")
            raise UpstreamError(
                f"could not reach CountriesNow: {exc.__class__.__name__}"
            ) from exc

        ms = (time.perf_counter() - started) * 1000
        log = logger.warning if resp.status_code >= 500 else logger.info
        log(f"CountriesNow GET {path} -> {resp.status_code} in {ms:.0f} ms")

        try:
            body = resp.json()
        except ValueError:
            body = None

        # Unknown country: CountriesNow answers with error=true (and usually a 404).
        if isinstance(body, dict) and body.get("error") is True:
            msg = str(body.get("msg", "")).lower()
            if resp.status_code == 404 or "not found" in msg:
                raise CountryNotFoundError(f"Country '{country}' not found")
            raise UpstreamError(f"CountriesNow error: {body.get('msg')}")
        if resp.status_code == 404:
            raise CountryNotFoundError(f"Country '{country}' not found")
        if resp.status_code >= 400 or not isinstance(body, dict):
            raise UpstreamError(f"CountriesNow returned HTTP {resp.status_code}")

        data = body.get("data")
        if not isinstance(data, dict):
            raise UpstreamError("CountriesNow returned an unexpected response")
        return data