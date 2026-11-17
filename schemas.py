"""Pydantic models: what a valid trip looks like. FastAPI checks every request
body against them and answers 422 before any of our code runs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

# Money is a Decimal inside the app, but a plain JSON number in responses.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


def _not_in_past(value: date | None) -> date | None:
    if value is not None and value < date.today():
        raise ValueError("travel_date is in the past")
    return value


class TripCreate(BaseModel):
    traveller: str = Field(min_length=1, max_length=200)
    country: str = Field(min_length=1, max_length=200)
    budget_inr: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    travel_date: date

    @field_validator("traveller", "country")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("travel_date")
    @classmethod
    def date_not_in_past(cls, value: date) -> date:
        return _not_in_past(value)


class TripUpdate(BaseModel):
    """Every field is optional: only the fields sent are changed."""

    traveller: str | None = Field(default=None, min_length=1, max_length=200)
    country: str | None = Field(default=None, min_length=1, max_length=200)
    budget_inr: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    travel_date: date | None = None

    @field_validator("traveller", "country")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("travel_date")
    @classmethod
    def date_not_in_past(cls, value: date | None) -> date | None:
        return _not_in_past(value)

    @model_validator(mode="after")
    def no_explicit_nulls(self):
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    traveller: str
    country: str
    currency_code: str
    budget_inr: Money
    travel_date: date
    created_at: datetime


class TripWithRate(TripOut):
    rate: float | None
    budget_local: Money | None