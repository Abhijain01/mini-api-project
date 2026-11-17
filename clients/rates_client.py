"""Adapter for the Frankfurter API.

Hides its URL and response shape behind one method.
Knows nothing about FastAPI or HTTP status codes.
"""

import httpx

from exceptions import NotFoundError, UpstreamError


class RatesClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout)

    def get_rate(self, base: str, quote: str) -> float:
        """Today's rate: 1 `base` = rate * `quote`."""
        url = f"{self._base_url}/rate/{base}/{quote}"
        try:
            resp = httpx.get(url, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"could not reach Frankfurter: {exc.__class__.__name__}"
            ) from exc

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