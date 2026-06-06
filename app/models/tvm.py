"""
tvm.py — time value of money templates.

Three entity groups:
  1. ProjectCashflow + CashflowPeriod + ProjectMetrics
       — NPV, IRR, MIRR, payback, profitability index
       — Each period stores its own PV factor so you can audit row-by-row

  2. Loan + LoanAmortization
       — Full amortization schedule (fixed, interest-only, balloon)
       — Standard, interest-only, or graduated payment types

These are standalone — no FK to Security. You may link a project to a
security later (e.g. evaluating a REIT acquisition) by adding an optional FK.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.extensions import db


# ---------------------------------------------------------------------------
# Project / DCF analysis
# ---------------------------------------------------------------------------

class ProjectCashflow(db.Model):
    """
    Template for any capital budgeting analysis — IRR, NPV, payback period.
    Works for stock valuation (multi-year FCF projection) or real projects.
    """
    __tablename__ = "project_cashflow"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    initial_investment: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    # Weighted average cost of capital — used as the default discount rate
    wacc: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    # Override discount rate — if None, uses wacc
    discount_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    # Terminal growth rate for perpetuity value (Gordon Growth)
    terminal_growth_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    reinvestment_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))  # for MIRR

    currency: Mapped[str] = mapped_column(String(8), default="USD")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    periods: Mapped[list["CashflowPeriod"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="CashflowPeriod.period_number"
    )
    metrics: Mapped["ProjectMetrics | None"] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ProjectCashflow '{self.project_name}'>"


class CashflowPeriod(db.Model):
    """
    One row per period (year, quarter, month — your choice).
    Storing pv_factor and present_value per period makes the math fully auditable.
    """
    __tablename__ = "cashflow_period"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_cashflow.id"), nullable=False, index=True
    )
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = t0, 1 = t1 ...
    period_label: Mapped[str | None] = mapped_column(String(32))         # "Year 1", "Q3 2026"
    period_date: Mapped[date | None] = mapped_column(Date)

    cash_inflow: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    cash_outflow: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    net_cashflow: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))   # inflow - outflow

    # Computed by the service layer
    pv_factor: Mapped[Decimal | None] = mapped_column(Numeric(14, 8))      # 1 / (1+r)^t
    present_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))  # net_cashflow * pv_factor
    cumulative_cashflow: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))  # for payback calc

    notes: Mapped[str | None] = mapped_column(String(256))

    project: Mapped["ProjectCashflow"] = relationship(back_populates="periods")

    def __repr__(self) -> str:
        return f"<CashflowPeriod t={self.period_number} ncf={self.net_cashflow}>"


class ProjectMetrics(db.Model):
    """
    Derived output metrics — recalculate and upsert after any period change.
    """
    __tablename__ = "project_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_cashflow.id"), nullable=False, unique=True
    )

    npv: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    # Sum of PVs - initial investment. Positive = value-creating.

    irr: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    # Discount rate that makes NPV = 0. Compare to WACC: IRR > WACC = accept.

    mirr: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    # Modified IRR — reinvests positive CFs at reinvestment_rate, finances negatives at finance_rate.

    payback_period_years: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    # Years to recover initial investment (undiscounted).

    discounted_payback_years: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    # Years to recover on a PV basis.

    profitability_index: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    # NPV / initial_investment + 1. PI > 1 = accept.

    roi_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    # (total_returns - initial_investment) / initial_investment.

    terminal_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    # Gordon Growth terminal value if terminal_growth_rate set.

    calc_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["ProjectCashflow"] = relationship(back_populates="metrics")

    @property
    def payback_period(self):
        return self.payback_period_years

    @payback_period.setter
    def payback_period(self, value):
        self.payback_period_years = value

    def __repr__(self) -> str:
        return (
            f"<ProjectMetrics project={self.project_id} "
            f"NPV={self.npv} IRR={self.irr} PI={self.profitability_index}>"
        )


# ---------------------------------------------------------------------------
# Loan / debt analysis
# ---------------------------------------------------------------------------

class Loan(db.Model):
    __tablename__ = "loan"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    loan_name: Mapped[str] = mapped_column(String(256), nullable=False)
    principal: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)  # e.g. 0.065
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    # "fixed" | "interest_only" | "balloon" | "graduated"
    amort_type: Mapped[str] = mapped_column(String(32), nullable=False, default="fixed")
    origination_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    balloon_payment: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))  # for balloon loans
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    schedule: Mapped[list["LoanAmortization"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan",
        order_by="LoanAmortization.payment_number"
    )

    def __repr__(self) -> str:
        return f"<Loan '{self.loan_name}' principal={self.principal} rate={self.annual_rate}>"


class LoanAmortization(db.Model):
    """One row per payment — full amortization schedule."""
    __tablename__ = "loan_amortization"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan.id"), nullable=False, index=True
    )
    payment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)

    payment_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    principal_portion: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    interest_portion: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)

    # Cumulative totals — useful for "how much interest have I paid so far" queries
    cumulative_principal: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    cumulative_interest: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))

    loan: Mapped["Loan"] = relationship(back_populates="schedule")

    def __repr__(self) -> str:
        return (
            f"<LoanAmortization #{self.payment_number} "
            f"pmt={self.payment_amount} bal={self.remaining_balance}>"
        )
