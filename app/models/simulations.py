"""
simulations.py — Monte Carlo simulation runs and their results.

SimulationRun: captures the model inputs (GBM parameters, time horizon, etc.)
SimulationResult: the output percentile distribution and probability metrics.

The full percentile array is stored as JSON so you can reconstruct histograms
without blowing out the schema with 1000 float columns.

Supported sim_type values:
  "gbm"           — geometric Brownian motion (log-normal returns)
  "historical"    — bootstrap from actual historical returns
  "mean_revert"   — Ornstein-Uhlenbeck mean reversion
  "dcf_scenario"  — Monte Carlo over DCF inputs (growth rate, discount rate)
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.extensions import db


class SimulationRun(db.Model):
    __tablename__ = "simulation_run"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.id"), nullable=False, index=True
    )
    run_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    sim_type: Mapped[str] = mapped_column(String(32), nullable=False)  # see module docstring
    iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=10_000)
    time_horizon_years: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    # GBM / statistical inputs
    mu_annual_return: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))    # e.g. 0.08
    sigma_annual_vol: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))    # e.g. 0.22
    starting_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    risk_free_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))      # e.g. 0.045
    benchmark_return: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))    # e.g. 0.10

    # For DCF scenario simulations
    revenue_growth_low: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    revenue_growth_high: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    margin_low: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    margin_high: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    discount_rate_low: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    discount_rate_high: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    security: Mapped["Security"] = relationship(back_populates="simulation_runs")
    result: Mapped["SimulationResult | None"] = relationship(
        back_populates="run", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def time_horizon_yrs(self):
        return self.time_horizon_years

    @time_horizon_yrs.setter
    def time_horizon_yrs(self, value):
        self.time_horizon_years = value

    @property
    def mu_return(self):
        return self.mu_annual_return

    @mu_return.setter
    def mu_return(self, value):
        self.mu_annual_return = value

    @property
    def sigma_volatility(self):
        return self.sigma_annual_vol

    @sigma_volatility.setter
    def sigma_volatility(self, value):
        self.sigma_annual_vol = value

    def __repr__(self) -> str:
        return (
            f"<SimulationRun {self.security_id} type={self.sim_type} "
            f"n={self.iterations} t={self.time_horizon_years}yr>"
        )


class SimulationResult(db.Model):
    __tablename__ = "simulation_result"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_run.id"), nullable=False, unique=True
    )

    # Key percentile outcomes (price or return, matching the run's unit)
    p5_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    p10_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    p25_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    p50_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))  # median
    p75_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    p90_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    p95_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))

    mean_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    std_dev_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    min_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    max_outcome: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))

    # Probabilities (0.0 to 1.0)
    prob_positive_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    prob_beats_benchmark: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    prob_loss_gt_20pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))   # downside risk
    prob_gain_gt_50pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))   # upside probability
    value_at_risk_5pct: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))  # VaR at 95% conf

    # Full distribution — store as JSON array of {percentile, value} dicts
    # e.g. [{"p": 1, "v": 42.1}, {"p": 2, "v": 43.5}, ...]
    percentile_distribution: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["SimulationRun"] = relationship(back_populates="result")

    def __repr__(self) -> str:
        return (
            f"<SimulationResult run={self.run_id} "
            f"p50={self.p50_outcome} prob_pos={self.prob_positive_return}>"
        )


from .securities import Security  # noqa: E402, F401
