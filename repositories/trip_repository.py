"""All database access for trips. Returns plain Python objects (Trip) and
never raises HTTP errors or calls outside APIs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from db import TripRow

UPDATABLE_FIELDS = {"traveller", "country", "currency_code", "budget_inr", "travel_date"}


@dataclass(frozen=True)
class Trip:
    id: int
    traveller: str
    country: str
    currency_code: str
    budget_inr: Decimal
    travel_date: date
    created_at: datetime


def _to_trip(row: TripRow) -> Trip:
    return Trip(
        id=row.id,
        traveller=row.traveller,
        country=row.country,
        currency_code=row.currency_code,
        budget_inr=row.budget_inr,
        travel_date=row.travel_date,
        created_at=row.created_at,
    )


class TripRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        traveller: str,
        country: str,
        currency_code: str,
        budget_inr: Decimal,
        travel_date: date,
    ) -> Trip:
        row = TripRow(
            traveller=traveller,
            country=country,
            currency_code=currency_code,
            budget_inr=budget_inr,
            travel_date=travel_date,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)  # loads id and created_at, set by the database
        return _to_trip(row)

    def get(self, trip_id: int) -> Trip | None:
        row = self._session.get(TripRow, trip_id)
        return _to_trip(row) if row else None

    def list(self) -> list[Trip]:
        rows = self._session.scalars(select(TripRow).order_by(TripRow.id))
        return [_to_trip(row) for row in rows]

    def update(self, trip_id: int, **fields) -> Trip | None:
        row = self._session.get(TripRow, trip_id)
        if row is None:
            return None
        for name, value in fields.items():
            if name not in UPDATABLE_FIELDS:
                raise ValueError(f"cannot update field {name!r}")
            setattr(row, name, value)
        self._session.commit()
        self._session.refresh(row)
        return _to_trip(row)

    def delete(self, trip_id: int) -> bool:
        row = self._session.get(TripRow, trip_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True