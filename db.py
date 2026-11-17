"""The engine, the trips table and per-request sessions. SQLAlchemy is imported
only here and in repositories/trip_repository.py."""

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class TripRow(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    traveller: Mapped[str] = mapped_column(Text)
    country: Mapped[str] = mapped_column(Text)
    currency_code: Mapped[str] = mapped_column(String(3))
    budget_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    travel_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Database:
    def __init__(self, url: str, **engine_kwargs) -> None:
        # pool_pre_ping: test a connection before using it, so a restarted
        # database doesn't leave the app with dead connections.
        self.engine = create_engine(url, pool_pre_ping=True, **engine_kwargs)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Iterator[Session]:
        """One session per request, closed when the request ends.
        Use it as a FastAPI dependency: Depends(database.session)."""
        with self._sessions() as session:
            yield session