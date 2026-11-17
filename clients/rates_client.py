"""Adapter for the Frankfurter API.

Hides its URL and response shape behind one method and logs every call.
Knows nothing about FastAPI or HTTP status codes.
"""

import time

import httpx
from loguru import logger

from exceptions import NotFoundError, UpstreamError


class RatesClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout)

    def get_rate(self, base: str, quote: str) -> float:
        """Today's rate: 1 `base` = rate * `quote`."""
        path = f"/rate/{base}/{quote}"
        started = time.perf_counter()
        try:
            resp = httpx.get(f"{self._base_url}{path}", timeout=self._timeout)
        except httpx.HTTPError as exc:
            ms = (time.perf_counter() - started) * 1000
            reason = "timeout" if isinstance(exc, httpx.TimeoutException) else exc.__class__.__name__
            logger.warning(f"Frankfurter GET {path} -> {reason} after {ms:.0f} ms")
            raise UpstreamError(
                f"could not reach Frankfurter: {exc.__class__.__name__}"
            ) from exc

        ms = (time.perf_counter() - started) * 1000
        log = logger.warning if resp.status_code >= 500 else logger.info
        log(f"Frankfurter GET {path} -> {resp.status_code} in {ms:.0f} ms")

        # Frankfurter answers 404 (or 400/422) for an unknown currency code.
        if resp.status_code in (400, 404, 422):
            raise NotFoundError(f"No exchange rate available for {base}/{quote}")
        if resp.status_code >= 400:
            raise UpstreamError(f"Frankfurter returned HTTP {resp.status_code}")

        try:
            rate = resp.json().get("rate")
        except (ValueError, AttributeError):
            raise UpstreamError("Frankfurter returned invalid JSON") from None
        if not isinstance(rate, (int, float)):
            raise UpstreamError("no rate in response")
        return float(rate)