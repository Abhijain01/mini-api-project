"""Facade over both clients: one call per question the routes ask.

Does not call httpx and does not know about HTTP status codes.
It depends on the two small Protocols below, not on the concrete client
classes, so a fake client can be passed in for tests (dependency injection).
"""

from typing import Protocol

from clients.countries_client import CapitalInfo, CurrencyInfo
from exceptions import NotFoundError

HOME_CURRENCY = "INR"


class CountryProvider(Protocol):
    def get_currency(self, country: str) -> CurrencyInfo: ...
    def get_capital(self, country: str) -> CapitalInfo: ...


class RateProvider(Protocol):
    def get_rate(self, base: str, quote: str) -> float: ...


class TravelService:
    def __init__(self, countries: CountryProvider, rates: RateProvider) -> None:
        self._countries = countries
        self._rates = rates

    def get_country(self, name: str) -> dict:
        cur = self._countries.get_currency(name)
        cap = self._countries.get_capital(name)
        return {
            "name": cur.name or cap.name or name,
            "currency": cur.code,
            "capital": cap.capital,
        }

    def convert_budget(self, name: str, budget_inr: float) -> dict:
        cur = self._countries.get_currency(name)
        country = cur.name or name
        if not cur.code:
            raise NotFoundError(f"No currency found for '{country}'")

        rate = self._rates.get_rate(HOME_CURRENCY, cur.code)
        return {
            "country": country,
            "currency": cur.code,
            "rate": rate,
            "budget_inr": budget_inr,
            "budget_local": round(budget_inr * rate, 2),
        }