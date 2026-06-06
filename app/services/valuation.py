"""Graham valuation service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.extensions import db

from app.models.market import PriceHistory
from app.models.securities import BalanceSheet, FinancialReport, IncomeStatement
from app.models.valuation import IntrinsicValue, ValuationRatio
from ._helpers import decimal_or_none, quantize_or_none, ratio_or_none


class ValuationService:
    def __init__(self, session=None):
        self.session = session or db.session

    def compute_graham_valuation(
        self,
        security_id: UUID,
        calc_date: date | None = None,
        model_type: str = "graham_number",
    ) -> dict[str, object]:
        calc_date = calc_date or date.today()
        latest_income = self._latest_statement(IncomeStatement, security_id, calc_date)
        latest_balance = self._latest_statement(BalanceSheet, security_id, calc_date)
        if latest_income is None or latest_balance is None:
            raise ValueError("financial statements are required before valuation")

        eps_10yr_avg = self._average_eps(security_id, calc_date)
        shares = decimal_or_none(
            latest_income.shares_outstanding_diluted
            or latest_income.shares_outstanding_basic
        )
        total_equity = decimal_or_none(latest_balance.total_equity)
        bvps = ratio_or_none(total_equity, shares)
        current_assets = decimal_or_none(latest_balance.total_current_assets)
        total_liabilities = decimal_or_none(latest_balance.total_liabilities)
        ncav_per_share = ratio_or_none(
            current_assets - total_liabilities
            if current_assets is not None and total_liabilities is not None
            else None,
            shares,
        )

        graham_number = self._graham_number(eps_10yr_avg, bvps)
        market_price = self._latest_close(security_id, calc_date)
        intrinsic_value = graham_number or ncav_per_share
        margin_of_safety = None
        if intrinsic_value not in (None, 0) and market_price is not None:
            margin_of_safety = (intrinsic_value - market_price) / intrinsic_value

        intrinsic = IntrinsicValue(
            security_id=security_id,
            calc_date=calc_date,
            model_type=model_type,
            book_value_per_share=quantize_or_none(bvps),
            eps_ttm=latest_income.eps_diluted or latest_income.eps_basic,
            eps_10yr_avg=quantize_or_none(eps_10yr_avg),
            graham_number=quantize_or_none(graham_number),
            ncav_per_share=quantize_or_none(ncav_per_share),
            intrinsic_value=quantize_or_none(intrinsic_value),
            market_price_at_calc=market_price,
            margin_of_safety_pct=quantize_or_none(margin_of_safety),
        )

        ratios = ValuationRatio(
            security_id=security_id,
            calc_date=calc_date,
            pe_ratio=quantize_or_none(ratio_or_none(market_price, latest_income.eps_diluted or latest_income.eps_basic)),
            pb_ratio=quantize_or_none(ratio_or_none(market_price, bvps)),
            current_ratio=quantize_or_none(
                ratio_or_none(latest_balance.total_current_assets, latest_balance.total_current_liabilities)
            ),
            quick_ratio=quantize_or_none(
                ratio_or_none(
                    (decimal_or_none(latest_balance.total_current_assets) or 0)
                    - (decimal_or_none(latest_balance.inventory) or 0),
                    latest_balance.total_current_liabilities,
                )
            ),
            debt_to_equity=quantize_or_none(ratio_or_none(latest_balance.total_liabilities, total_equity)),
            roe=quantize_or_none(ratio_or_none(latest_income.net_income, total_equity)),
            roa=quantize_or_none(ratio_or_none(latest_income.net_income, latest_balance.total_assets)),
        )
        if ratios.pe_ratio is not None and ratios.pb_ratio is not None:
            ratios.pe_times_pb = quantize_or_none(ratios.pe_ratio * ratios.pb_ratio)

        self.session.add(intrinsic)
        self.session.add(ratios)
        self.session.commit()
        return {"intrinsic_value": intrinsic, "valuation_ratio": ratios}

    def _latest_statement(self, statement_cls, security_id: UUID, calc_date: date):
        return (
            self.session.query(statement_cls)
            .join(FinancialReport, statement_cls.report_id == FinancialReport.id)
            .filter(
                FinancialReport.security_id == security_id,
                FinancialReport.period_end <= calc_date,
            )
            .order_by(FinancialReport.period_end.desc())
            .first()
        )

    def _average_eps(self, security_id: UUID, calc_date: date) -> Decimal | None:
        rows = (
            self.session.query(IncomeStatement)
            .join(FinancialReport, IncomeStatement.report_id == FinancialReport.id)
            .filter(
                FinancialReport.security_id == security_id,
                FinancialReport.period_end <= calc_date,
            )
            .order_by(FinancialReport.period_end.desc())
            .limit(10)
            .all()
        )
        values = [
            decimal_or_none(row.eps_diluted if row.eps_diluted is not None else row.eps_basic)
            for row in rows
        ]
        values = [value for value in values if value is not None]
        if not values:
            return None
        return sum(values) / Decimal(len(values))

    def _latest_close(self, security_id: UUID, calc_date: date) -> Decimal | None:
        price = (
            self.session.query(PriceHistory)
            .filter(
                PriceHistory.security_id == security_id,
                PriceHistory.price_date <= calc_date,
            )
            .order_by(PriceHistory.price_date.desc())
            .first()
        )
        if price is None:
            return None
        return decimal_or_none(price.adj_close if price.adj_close is not None else price.close)

    @staticmethod
    def _graham_number(eps: Decimal | None, bvps: Decimal | None) -> Decimal | None:
        if eps is None or bvps is None or eps <= 0 or bvps <= 0:
            return None
        return (Decimal("22.5") * eps * bvps).sqrt()
