"""
securities.py — core company/security entities and their filed financial reports.

Design note: FINANCIAL_REPORT is the anchor between a security and its
accounting statements. One report → one balance sheet, one income statement,
one cash flow statement (mirroring GAAP structure).
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from decimal import Decimal


class Security(db.Model):
    __tablename__ = "security"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(32))
    sector: Mapped[str | None] = mapped_column(String(128))
    industry: Mapped[str | None] = mapped_column(String(128))
    # e.g. "common_stock", "etf", "reit", "bond", "preferred"
    security_type: Mapped[str] = mapped_column(String(32), nullable=False, default="common_stock")
    ipo_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # relationships
    reports: Mapped[list["FinancialReport"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="dynamic"
    )
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="dynamic"
    )
    moving_averages: Mapped[list["MovingAverage"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="dynamic"
    )
    intrinsic_values: Mapped[list["IntrinsicValue"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="dynamic"
    )
    valuation_ratios: Mapped[list["ValuationRatio"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="dynamic"
    )
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="security", lazy="dynamic"
    )
    watchlist_entries: Mapped[list["Watchlist"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="dynamic"
    )
    simulation_runs: Mapped[list["SimulationRun"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Security {self.ticker}>"


class FinancialReport(db.Model):
    """
    One row per SEC filing (10-K, 10-Q, 20-F, etc.).
    Acts as the foreign key anchor for the three accounting statements.
    """
    __tablename__ = "financial_report"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.id"), nullable=False, index=True
    )
    # "10-K", "10-Q", "20-F", "8-K", "annual", "quarterly"
    report_type: Mapped[str] = mapped_column(String(16), nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    filed_date: Mapped[date | None] = mapped_column(Date)
    fiscal_year: Mapped[str | None] = mapped_column(String(8))   # e.g. "2023"
    fiscal_quarter: Mapped[str | None] = mapped_column(String(4)) # e.g. "Q3"
    source_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    security: Mapped["Security"] = relationship(back_populates="reports")
    balance_sheet: Mapped["BalanceSheet | None"] = relationship(
        back_populates="report", uselist=False, cascade="all, delete-orphan"
    )
    income_statement: Mapped["IncomeStatement | None"] = relationship(
        back_populates="report", uselist=False, cascade="all, delete-orphan"
    )
    cash_flow_statement: Mapped["CashFlowStatement | None"] = relationship(
        back_populates="report", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FinancialReport {self.report_type} {self.period_end}>"


class BalanceSheet(db.Model):
    """
    Assets = Liabilities + Equity — always.
    All monetary columns are in whole dollars (no cents) stored as Numeric(20,0)
    to avoid float precision issues on large figures.
    """
    __tablename__ = "balance_sheet"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_report.id"), nullable=False, unique=True
    )

    # --- ASSETS ---
    cash_and_equivalents: Mapped[int | None] = mapped_column(Numeric(20, 0))
    short_term_investments: Mapped[int | None] = mapped_column(Numeric(20, 0))
    accounts_receivable: Mapped[int | None] = mapped_column(Numeric(20, 0))
    inventory: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_current_assets: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_current_assets: Mapped[int | None] = mapped_column(Numeric(20, 0))

    property_plant_equipment_net: Mapped[int | None] = mapped_column(Numeric(20, 0))
    goodwill: Mapped[int | None] = mapped_column(Numeric(20, 0))
    intangible_assets: Mapped[int | None] = mapped_column(Numeric(20, 0))
    long_term_investments: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_non_current_assets: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_non_current_assets: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_assets: Mapped[int | None] = mapped_column(Numeric(20, 0))

    # --- LIABILITIES ---
    accounts_payable: Mapped[int | None] = mapped_column(Numeric(20, 0))
    short_term_debt: Mapped[int | None] = mapped_column(Numeric(20, 0))
    current_portion_long_term_debt: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_current_liabilities: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_current_liabilities: Mapped[int | None] = mapped_column(Numeric(20, 0))

    long_term_debt: Mapped[int | None] = mapped_column(Numeric(20, 0))
    deferred_tax_liabilities: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_non_current_liabilities: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_non_current_liabilities: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_liabilities: Mapped[int | None] = mapped_column(Numeric(20, 0))

    # --- EQUITY ---
    common_stock: Mapped[int | None] = mapped_column(Numeric(20, 0))
    additional_paid_in_capital: Mapped[int | None] = mapped_column(Numeric(20, 0))
    retained_earnings: Mapped[int | None] = mapped_column(Numeric(20, 0))
    treasury_stock: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_equity: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_equity: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_liabilities_and_equity: Mapped[int | None] = mapped_column(Numeric(20, 0))

    # Graham-specific computed helpers (can be populated by a service layer)
    net_current_assets: Mapped[int | None] = mapped_column(Numeric(20, 0))  # current_assets - total_liabilities
    ncav: Mapped[int | None] = mapped_column(Numeric(20, 0))                 # net current asset value

    report: Mapped["FinancialReport"] = relationship(back_populates="balance_sheet")

    @property
    def cash_equivalents(self):
        return self.cash_and_equivalents

    @cash_equivalents.setter
    def cash_equivalents(self, value):
        self.cash_and_equivalents = value

    @property
    def current_assets(self):
        return self.total_current_assets

    @current_assets.setter
    def current_assets(self, value):
        self.total_current_assets = value

    @property
    def current_liabilities(self):
        return self.total_current_liabilities

    @current_liabilities.setter
    def current_liabilities(self, value):
        self.total_current_liabilities = value

    def __repr__(self) -> str:
        return f"<BalanceSheet report_id={self.report_id}>"


class IncomeStatement(db.Model):
    __tablename__ = "income_statement"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_report.id"), nullable=False, unique=True
    )

    revenue: Mapped[int | None] = mapped_column(Numeric(20, 0))
    cost_of_goods_sold: Mapped[int | None] = mapped_column(Numeric(20, 0))
    gross_profit: Mapped[int | None] = mapped_column(Numeric(20, 0))
    research_and_development: Mapped[int | None] = mapped_column(Numeric(20, 0))
    selling_general_admin: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_operating_expenses: Mapped[int | None] = mapped_column(Numeric(20, 0))
    total_operating_expenses: Mapped[int | None] = mapped_column(Numeric(20, 0))
    ebit: Mapped[int | None] = mapped_column(Numeric(20, 0))  # operating income
    interest_expense: Mapped[int | None] = mapped_column(Numeric(20, 0))
    interest_income: Mapped[int | None] = mapped_column(Numeric(20, 0))
    ebt: Mapped[int | None] = mapped_column(Numeric(20, 0))   # pre-tax income
    income_tax_expense: Mapped[int | None] = mapped_column(Numeric(20, 0))
    net_income: Mapped[int | None] = mapped_column(Numeric(20, 0))
    net_income_attributable: Mapped[int | None] = mapped_column(Numeric(20, 0))

    # Per-share data
    shares_outstanding_basic: Mapped[int | None] = mapped_column(Numeric(20, 0))
    shares_outstanding_diluted: Mapped[int | None] = mapped_column(Numeric(20, 0))
    eps_basic: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    eps_diluted: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    dividends_per_share: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # Graham uses 10-year avg EPS — store the period count for normalization queries
    period_months: Mapped[int | None] = mapped_column(Integer)  # 3 for Q, 12 for annual

    report: Mapped["FinancialReport"] = relationship(back_populates="income_statement")

    def __repr__(self) -> str:
        return f"<IncomeStatement report_id={self.report_id}>"


class CashFlowStatement(db.Model):
    __tablename__ = "cash_flow_statement"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_report.id"), nullable=False, unique=True
    )

    # Operating
    net_income_cfs: Mapped[int | None] = mapped_column(Numeric(20, 0))  # reconciliation start
    depreciation_amortization: Mapped[int | None] = mapped_column(Numeric(20, 0))
    stock_based_compensation: Mapped[int | None] = mapped_column(Numeric(20, 0))
    changes_in_working_capital: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_operating_activities: Mapped[int | None] = mapped_column(Numeric(20, 0))
    cash_from_operations: Mapped[int | None] = mapped_column(Numeric(20, 0))   # CFO

    # Investing
    capital_expenditures: Mapped[int | None] = mapped_column(Numeric(20, 0))   # CapEx (negative)
    acquisitions: Mapped[int | None] = mapped_column(Numeric(20, 0))
    purchase_of_investments: Mapped[int | None] = mapped_column(Numeric(20, 0))
    sale_of_investments: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_investing_activities: Mapped[int | None] = mapped_column(Numeric(20, 0))
    cash_from_investing: Mapped[int | None] = mapped_column(Numeric(20, 0))    # CFI

    # Financing
    debt_issuance: Mapped[int | None] = mapped_column(Numeric(20, 0))
    debt_repayment: Mapped[int | None] = mapped_column(Numeric(20, 0))
    dividends_paid: Mapped[int | None] = mapped_column(Numeric(20, 0))
    share_buybacks: Mapped[int | None] = mapped_column(Numeric(20, 0))
    share_issuance: Mapped[int | None] = mapped_column(Numeric(20, 0))
    other_financing_activities: Mapped[int | None] = mapped_column(Numeric(20, 0))
    cash_from_financing: Mapped[int | None] = mapped_column(Numeric(20, 0))   # CFF

    # Summary
    net_change_in_cash: Mapped[int | None] = mapped_column(Numeric(20, 0))
    free_cash_flow: Mapped[int | None] = mapped_column(Numeric(20, 0))  # CFO - CapEx

    report: Mapped["FinancialReport"] = relationship(back_populates="cash_flow_statement")

    @property
    def cfo(self):
        return self.cash_from_operations

    @cfo.setter
    def cfo(self, value):
        self.cash_from_operations = value

    @property
    def capex(self):
        return self.capital_expenditures

    @capex.setter
    def capex(self, value):
        self.capital_expenditures = value

    @property
    def cfi(self):
        return self.cash_from_investing

    @cfi.setter
    def cfi(self, value):
        self.cash_from_investing = value

    @property
    def cff(self):
        return self.cash_from_financing

    @cff.setter
    def cff(self, value):
        self.cash_from_financing = value

    def __repr__(self) -> str:
        return f"<CashFlowStatement report_id={self.report_id}>"


# Deferred imports to avoid circular refs — resolve at module level after all models load
# Needed at bottom as these have not been declared yet at top
from .market import PriceHistory, MovingAverage          # noqa: E402
from .valuation import IntrinsicValue, ValuationRatio    # noqa: E402
from .portfolio import Holding, Watchlist                # noqa: E402
from .simulations import SimulationRun                   # noqa: E402
