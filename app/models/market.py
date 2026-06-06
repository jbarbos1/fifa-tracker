"""
market.py — price history and computed moving averages.

PriceHistory: raw OHLCV data, one row per trading day per security.
MovingAverage: computed table — store multiple windows (20, 50, 200-day)
               per date so you can query across windows in one shot.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.extensions import db


class PriceHistory(db.Model):
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("security_id", "price_date", name="uq_price_history_security_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.id"), nullable=False, index=True
    )
    price_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    open: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    high: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    low: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    close: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    adj_close: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))  # split/dividend adjusted
    volume: Mapped[int | None] = mapped_column(Numeric(20, 0))

    # Source tag so you know where the row came from
    data_source: Mapped[str | None] = mapped_column(String(32))  # "yahoo", "polygon", "manual"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    security: Mapped["Security"] = relationship(back_populates="price_history")

    def __repr__(self) -> str:
        return f"<PriceHistory {self.security_id} {self.price_date} close={self.close}>"


class MovingAverage(db.Model):
    """
    Computed moving averages. Store the result of each calculation run
    rather than recomputing on every query — pandas does the heavy lifting
    in the service layer, this just persists the results.

    window_days: 20, 50, 200 are the standard Graham/technical windows.
    """
    __tablename__ = "moving_average"
    __table_args__ = (
        UniqueConstraint(
            "security_id", "calc_date", "window_days",
            name="uq_ma_security_date_window"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.id"), nullable=False, index=True
    )
    calc_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)  # 20 | 50 | 200

    sma: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))   # simple moving average
    ema: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))   # exponential moving average
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))  # volume-weighted avg price

    # Price position relative to MA (useful for Graham screen queries)
    price_to_sma_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))  # close / sma
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    security: Mapped["Security"] = relationship(back_populates="moving_averages")

    def __repr__(self) -> str:
        return f"<MovingAverage {self.security_id} {self.window_days}d {self.calc_date}>"


# Resolve forward ref
from .securities import Security  # noqa: E402, F401
