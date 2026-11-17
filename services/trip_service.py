"""Trips: looks up the currency, stores trips through the repository, and
converts budgets at today's rate. Writes no SQL and opens no database session."""

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal

from exceptions import NotFoundError, TripNotFoundError
from repositories.trip_repository import Trip, TripRepository
from services.travel_service import HOME_CURRENCY, CountryProvider, RateProvider

CENT = Decimal("0.01")


@dataclass(frozen=True)
class PricedTrip:
    """A trip plus its budget converted at today's rate (None if no rate exists)."""

    id: int
    traveller: str
    country: str
    currency_code: str
    budget_inr: Decimal
    travel_date: date
    created_at: datetime
    rate: float | None
    budget_local: Decimal | None


class TripService:
    def __init__(
        self, repository: TripRepository, countries: CountryProvider, rates: RateProvider
    ) -> None:
        self._repo = repository
        self._countries = countries
        self._rates = rates

    def create_trip(
        self, *, traveller: str, country: str, budget_inr: Decimal, travel_date: date
    ) -> Trip:
        name, code = self._lookup_currency(country)
        return self._repo.add(
            traveller=traveller,
            country=name,
            currency_code=code,
            budget_inr=budget_inr,
            travel_date=travel_date,
        )

    def get_trip(self, trip_id: int) -> Trip:
        trip = self._repo.get(trip_id)
        if trip is None:
            raise TripNotFoundError(f"Trip {trip_id} not found")
        return trip

    def list_trips(self) -> list[PricedTrip]:
        trips = self._repo.list()
        rates: dict[str, float | None] = {}  # one rate per currency, not per trip
        priced = []
        for trip in trips:
            code = trip.currency_code
            if code not in rates:
                rates[code] = self._rate_for(code)
            rate = rates[code]
            local = None
            if rate is not None:
                local = (trip.budget_inr * Decimal(str(rate))).quantize(CENT)
            priced.append(PricedTrip(**asdict(trip), rate=rate, budget_local=local))
        return priced

    def update_trip(self, trip_id: int, changes: dict) -> Trip:
        self.get_trip(trip_id)  # 404 first if the trip does not exist
        changes = dict(changes)
        if "country" in changes:
            name, code = self._lookup_currency(changes["country"])
            changes["country"] = name
            changes["currency_code"] = code
        trip = self._repo.update(trip_id, **changes)
        if trip is None:  # deleted between the check and the update
            raise TripNotFoundError(f"Trip {trip_id} not found")
        return trip

    def delete_trip(self, trip_id: int) -> None:
        if not self._repo.delete(trip_id):
            raise TripNotFoundError(f"Trip {trip_id} not found")

    def _lookup_currency(self, country: str) -> tuple[str, str]:
        info = self._countries.get_currency(country)  # raises CountryNotFoundError
        name = info.name or country
        code = info.code
        if not code or len(code) != 3:
            raise NotFoundError(f"No currency found for '{name}'")
        return name, code

    def _rate_for(self, code: str) -> float | None:
        if code == HOME_CURRENCY:
            return 1.0
        try:
            return self._rates.get_rate(HOME_CURRENCY, code)
        except NotFoundError:
            return None  # no rate for this currency: show the trip without a conversion