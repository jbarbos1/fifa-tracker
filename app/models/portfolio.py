"""
portfolio_service.py — portfolio, holdings (cost basis per lot), and watchlist.

Watchlist stores your Graham screening thresholds per ticker so you can
run a single query: "which watched stocks currently pass my criteria?"
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.extensions import db


class Portfolio(db.Model):
    __tablename__ = "portfolio"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Portfolio {self.name}>"


class Holding(db.Model):
    """
    One row per purchase lot — keeps cost basis accurate for tax lots
    and lets you track Graham's entry discipline (did you buy below intrinsic value?).
    """
    __tablename__ = "holding"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolio.id"), nullable=False, index=True
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.id"), nullable=False, index=True
    )

    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)  # price * shares

    # Optional: snapshot of intrinsic value at time of purchase
    intrinsic_value_at_purchase: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    margin_of_safety_at_purchase: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    # Disposition
    sold_date: Mapped[date | None] = mapped_column(Date)
    sold_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    realized_gain_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")
    security: Mapped["Security"] = relationship(back_populates="holdings")

    @property
    def is_open(self) -> bool:
        return self.sold_date is None

    def __repr__(self) -> str:
        return (
            f"<Holding {self.security_id} {self.shares}sh "
            f"@ {self.purchase_price} {'open' if self.is_open else 'closed'}>"
        )


class Watchlist(db.Model):
    """
    Per-security screening thresholds you want to enforce before buying.
    Query pattern: join Watchlist → ValuationRatio → IntrinsicValue
    to get "which of my watched stocks are currently buyable by Graham criteria."
    """
    __tablename__ = "watchlist"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.id"), nullable=False, unique=True
    )

    # Your personal thresholds — defaults mirror Graham defensive investor criteria
    target_buy_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    max_acceptable_pe: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=15.0)
    max_acceptable_pb: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=1.5)
    min_margin_of_safety: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0.33)
    min_current_ratio: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=2.0)
    max_debt_to_equity: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=1.0)

    # Free-text notes — Graham's qualitative criteria live here
    # e.g. "20+ years consecutive dividends", "no earnings deficit last 10 yrs"
    graham_criteria_notes: Mapped[str | None] = mapped_column(Text)
    thesis: Mapped[str | None] = mapped_column(Text)  # your investment thesis

    added_date: Mapped[date] = mapped_column(Date, default=date.today)
    alert_enabled: Mapped[bool | None] = mapped_column(default=True)

    security: Mapped["Security"] = relationship(back_populates="watchlist_entries")

    @property
    def target_price(self):
        return self.target_buy_price

    @target_price.setter
    def target_price(self, value):
        self.target_buy_price = value

    def __repr__(self) -> str:
        return f"<Watchlist {self.security_id} min_mos={self.min_margin_of_safety}>"


from .securities import Security  # noqa: E402, F401
