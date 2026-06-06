"""Market data and simulation services."""

from __future__ import annotations

import math
import random
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.extensions import db

from app.models.market import MovingAverage, PriceHistory
from app.models.simulations import SimulationResult, SimulationRun
from ._helpers import decimal_or_none, quantize_or_none, ratio_or_none


class MarketService:
    def __init__(self, session=None):
        self.session = session or db.session

    def ingest_prices(self, security_id: UUID, ohlcv_rows: list[dict]) -> list[PriceHistory]:
        rows: list[PriceHistory] = []
        for item in ohlcv_rows:
            price_date = item["price_date"]
            row = (
                self.session.query(PriceHistory)
                .filter(
                    PriceHistory.security_id == security_id,
                    PriceHistory.price_date == price_date,
                )
                .one_or_none()
            )
            if row is None:
                row = PriceHistory(security_id=security_id, price_date=price_date)
                self.session.add(row)
            for key in ["open", "high", "low", "close", "adj_close", "volume", "data_source"]:
                if key in item:
                    setattr(row, key, item[key])
            rows.append(row)

        self.session.flush()
        self.compute_moving_averages(security_id)
        self.session.commit()
        return rows

    def compute_moving_averages(
        self,
        security_id: UUID,
        windows: tuple[int, ...] = (20, 50, 200),
    ) -> list[MovingAverage]:
        prices = (
            self.session.query(PriceHistory)
            .filter(PriceHistory.security_id == security_id)
            .order_by(PriceHistory.price_date)
            .all()
        )
        created: list[MovingAverage] = []
        for idx, price in enumerate(prices):
            close = decimal_or_none(price.adj_close if price.adj_close is not None else price.close)
            if close is None:
                continue
            for window in windows:
                if idx + 1 < window:
                    continue
                window_rows = prices[idx + 1 - window : idx + 1]
                closes = [
                    decimal_or_none(row.adj_close if row.adj_close is not None else row.close)
                    for row in window_rows
                ]
                closes = [item for item in closes if item is not None]
                if not closes:
                    continue

                ma = (
                    self.session.query(MovingAverage)
                    .filter(
                        MovingAverage.security_id == security_id,
                        MovingAverage.calc_date == price.price_date,
                        MovingAverage.window_days == window,
                    )
                    .one_or_none()
                )
                if ma is None:
                    ma = MovingAverage(
                        security_id=security_id,
                        calc_date=price.price_date,
                        window_days=window,
                    )
                    self.session.add(ma)

                ma.sma = quantize_or_none(sum(closes) / Decimal(len(closes)))
                ma.vwap = self._vwap(window_rows)
                ma.price_to_sma_ratio = quantize_or_none(ratio_or_none(close, ma.sma))
                created.append(ma)
        return created

    def run_simulation(
        self,
        security_id: UUID,
        mu: Decimal,
        sigma: Decimal,
        horizon: Decimal,
        iterations: int = 10_000,
        sim_type: str = "gbm",
        starting_price: Decimal | None = None,
        benchmark_return: Decimal | None = None,
    ) -> SimulationResult:
        start = starting_price or self._latest_close(security_id)
        if start is None:
            raise ValueError("starting_price is required when no price history exists")

        run = SimulationRun(
            security_id=security_id,
            run_date=date.today(),
            sim_type=sim_type,
            iterations=iterations,
            time_horizon_years=horizon,
            mu_annual_return=mu,
            sigma_annual_vol=sigma,
            starting_price=start,
            benchmark_return=benchmark_return,
        )
        self.session.add(run)
        self.session.flush()

        outcomes = self._gbm_outcomes(start, mu, sigma, horizon, iterations)
        result = SimulationResult(
            run_id=run.id,
            p5_outcome=self._percentile(outcomes, 5),
            p10_outcome=self._percentile(outcomes, 10),
            p25_outcome=self._percentile(outcomes, 25),
            p50_outcome=self._percentile(outcomes, 50),
            p75_outcome=self._percentile(outcomes, 75),
            p90_outcome=self._percentile(outcomes, 90),
            p95_outcome=self._percentile(outcomes, 95),
            mean_outcome=quantize_or_none(sum(outcomes) / Decimal(len(outcomes))),
            min_outcome=min(outcomes),
            max_outcome=max(outcomes),
            prob_positive_return=self._probability(outcomes, lambda value: value > start),
            prob_beats_benchmark=self._prob_beats_benchmark(outcomes, start, benchmark_return),
            percentile_distribution=[
                {"p": p, "v": str(self._percentile(outcomes, p))}
                for p in range(1, 100)
            ],
        )
        self.session.add(result)
        self.session.commit()
        return result

    @staticmethod
    def _vwap(rows: list[PriceHistory]) -> Decimal | None:
        numerator = Decimal(0)
        denominator = Decimal(0)
        for row in rows:
            close = decimal_or_none(row.adj_close if row.adj_close is not None else row.close)
            volume = decimal_or_none(row.volume)
            if close is None or volume is None:
                continue
            numerator += close * volume
            denominator += volume
        return quantize_or_none(numerator / denominator) if denominator else None

    def _latest_close(self, security_id: UUID) -> Decimal | None:
        price = (
            self.session.query(PriceHistory)
            .filter(PriceHistory.security_id == security_id)
            .order_by(PriceHistory.price_date.desc())
            .first()
        )
        if price is None:
            return None
        return decimal_or_none(price.adj_close if price.adj_close is not None else price.close)

    @staticmethod
    def _gbm_outcomes(
        start: Decimal,
        mu: Decimal,
        sigma: Decimal,
        horizon: Decimal,
        iterations: int,
    ) -> list[Decimal]:
        start_f = float(start)
        mu_f = float(mu)
        sigma_f = float(sigma)
        horizon_f = float(horizon)
        drift = (mu_f - 0.5 * sigma_f * sigma_f) * horizon_f
        shock_scale = sigma_f * math.sqrt(horizon_f)
        return [
            quantize_or_none(start_f * math.exp(drift + shock_scale * random.gauss(0, 1)))
            for _ in range(iterations)
        ]

    @staticmethod
    def _percentile(values: list[Decimal], percentile: int) -> Decimal:
        ordered = sorted(values)
        idx = round((len(ordered) - 1) * (percentile / 100))
        return ordered[idx]

    @staticmethod
    def _probability(values: list[Decimal], predicate) -> Decimal:
        matches = sum(1 for value in values if predicate(value))
        return quantize_or_none(Decimal(matches) / Decimal(len(values)), "0.0001")

    def _prob_beats_benchmark(
        self,
        outcomes: list[Decimal],
        start: Decimal,
        benchmark_return: Decimal | None,
    ) -> Decimal | None:
        if benchmark_return is None:
            return None
        target = start * (Decimal(1) + benchmark_return)
        return self._probability(outcomes, lambda value: value > target)
