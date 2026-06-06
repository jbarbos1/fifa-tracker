"""
models/__init__.py

Single import point for the entire model layer.
Usage in Flask app factory:

    from app.models import db
    db.init_app(app)
"""
"""
models/__init__.py

Single import point for the model layer.
"""

from app.extensions import db

from .securities import (
    Security,
    FinancialReport,
    BalanceSheet,
    IncomeStatement,
    CashFlowStatement,
)

from .market import PriceHistory, MovingAverage
from .valuation import IntrinsicValue, ValuationRatio
from .portfolio import Portfolio, Holding, Watchlist
from .simulations import SimulationRun, SimulationResult
from .tvm import (
    ProjectCashflow,
    CashflowPeriod,
    ProjectMetrics,
    Loan,
    LoanAmortization,
)

from .leaue import League
from .league_member import LeagueMember

__all__ = [
    "db",
    "Security",
    "FinancialReport",
    "BalanceSheet",
    "IncomeStatement",
    "CashFlowStatement",
    "PriceHistory",
    "MovingAverage",
    "IntrinsicValue",
    "ValuationRatio",
    "Portfolio",
    "Holding",
    "Watchlist",
    "SimulationRun",
    "SimulationResult",
    "ProjectCashflow",
    "CashflowPeriod",
    "ProjectMetrics",
    "Loan",
    "LoanAmortization",
    "League",
    "LeagueMember",
]