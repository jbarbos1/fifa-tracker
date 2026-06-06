"""
valuation.py — Graham-principled intrinsic value and ratio tables.

IntrinsicValue: the computed Graham valuation snapshot per security per date.
  - graham_number:    sqrt(22.5 * EPS_10yr_avg * book_value_per_share)
  - ncav_per_share:   (current_assets - total_liabilities) / shares
  - margin_of_safety: (intrinsic_value - market_price) / intrinsic_value

ValuationRatio: standard screening ratios Graham used to filter candidates.
  Graham's criteria (Security Analysis / Intelligent Investor):
  - P/E ≤ 15 (or P/E × P/B ≤ 22.5)
  - P/B ≤ 1.5
  - Debt/Equity ≤ 1.0
  - Current Ratio ≥ 2.0
  - EPS growth > 0 over 10 years
  - Dividend history: uninterrupted for 20 years (track in a separate event table if needed)
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.extensions import db


class IntrinsicValue(db.Model):
    """
    Time-stamped intrinsic value snapshot. Recalculate and insert a new row
    each time you rerun valuation — keeps the history so you can see how
    margin of safety has evolved as market price moves.
    """
    __tablename__ = "intrinsic_value"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.id"), nullable=False, index=True
    )
    calc_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Model used: "graham_number" | "ncav" | "dcf" | "earnings_power" | "composite"
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Input variables (store alongside result so you can audit the calc)
    book_value_per_share: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    eps_ttm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))       # trailing 12-month EPS
    eps_10yr_avg: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))  # Graham's preferred
    eps_growth_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    discount_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))  # e.g. 0.09 for 9%
    terminal_growth_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))

    # Graham-specific outputs
    graham_number: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    # sqrt(22.5 * eps_10yr_avg * book_value_per_share)

    ncav_per_share: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    # (total_current_assets - total_liabilities) / shares_outstanding

    dcf_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    # standard DCF using discount_rate + terminal_growth_rate

    earnings_power_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    # normalized earnings / discount_rate (Bruce Greenwald approach)

    # The final number used for MoS calculation
    intrinsic_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    market_price_at_calc: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))

    # (intrinsic_value - market_price) / intrinsic_value
    # Positive = stock trading below intrinsic value (Graham wants ≥ 0.33)
    margin_of_safety_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    notes: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    security: Mapped["Security"] = relationship(back_populates="intrinsic_values")

    @property
    def passes_graham_mos(self) -> bool:
        """True if margin of safety meets Graham's ≥ 33% threshold."""
        return (self.margin_of_safety_pct or 0) >= 0.33

    def __repr__(self) -> str:
        return (
            f"<IntrinsicValue {self.security_id} {self.calc_date} "
            f"model={self.model_type} mos={self.margin_of_safety_pct}>"
        )


class ValuationRatio(db.Model):
    """
    Point-in-time valuation and financial health ratios.
    Recalculate after each new filing or price update.
    Graham screens are annotated inline — query on these columns directly.
    """
    __tablename__ = "valuation_ratio"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.id"), nullable=False, index=True
    )
    calc_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # --- Valuation multiples ---
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))   # Graham screen: ≤ 15
    pb_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))   # Graham screen: ≤ 1.5
    ps_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    peg_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    ev_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    pe_times_pb: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))  # Graham: ≤ 22.5

    # --- Liquidity (Graham: current_ratio ≥ 2.0 for industrials) ---
    current_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    quick_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    cash_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    # --- Leverage (Graham: long_term_debt ≤ net_current_assets) ---
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))   # Graham: ≤ 1.0
    debt_to_assets: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    interest_coverage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4)) # EBIT / interest

    # --- Profitability & returns ---
    roe: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))    # return on equity
    roa: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))    # return on assets
    roic: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))   # return on invested capital
    gross_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    operating_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    net_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    fcf_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))  # FCF / market cap

    # --- Dividend ---
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    payout_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    security: Mapped["Security"] = relationship(back_populates="valuation_ratios")

    @property
    def passes_graham_screen(self) -> bool:
        """
        Basic Graham defensive investor screen from The Intelligent Investor Ch.14.
        All six conditions must be met.
        """
        checks = [
            self.pe_ratio is not None and self.pe_ratio <= 15,
            self.pb_ratio is not None and self.pb_ratio <= 1.5,
            self.pe_times_pb is not None and self.pe_times_pb <= 22.5,
            self.current_ratio is not None and self.current_ratio >= 2.0,
            self.debt_to_equity is not None and self.debt_to_equity <= 1.0,
            self.interest_coverage is not None and self.interest_coverage >= 1.5,
        ]
        return all(checks)

    def __repr__(self) -> str:
        return f"<ValuationRatio {self.security_id} {self.calc_date} PE={self.pe_ratio}>"


from .securities import Security  # noqa: E402, F401