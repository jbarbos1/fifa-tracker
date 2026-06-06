"""Portfolio and watchlist service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.extensions import db

from app.models.portfolio import Holding, Portfolio, Watchlist
from app.models.valuation import IntrinsicValue, ValuationRatio


class PortfolioService:
    def __init__(self, session=None):
        self.session = session or db.session

    def add_holding(
        self,
        portfolio_id: UUID,
        security_id: UUID,
        shares: int,
        purchase_price: Decimal,
        purchase_date: date | None = None,
        notes: str | None = None,
    ) -> Holding:
        holding = Holding(
            portfolio_id=portfolio_id,
            security_id=security_id,
            purchase_date=purchase_date or date.today(),
            purchase_price=purchase_price,
            shares=shares,
            cost_basis=purchase_price * shares,
            notes=notes,
        )
        latest_value = self._latest_intrinsic_value(security_id)
        if latest_value is not None:
            holding.intrinsic_value_at_purchase = latest_value.intrinsic_value
            holding.margin_of_safety_at_purchase = latest_value.margin_of_safety_pct
        self.session.add(holding)
        self.session.commit()
        return holding

    def watch_security(
        self,
        security_id: UUID,
        target_buy_price: Decimal | None = None,
        max_pe: Decimal = Decimal("15.0"),
        min_margin_of_safety: Decimal = Decimal("0.33"),
        **thresholds,
    ) -> dict[str, object]:
        watchlist = (
            self.session.query(Watchlist)
            .filter(Watchlist.security_id == security_id)
            .one_or_none()
        )
        if watchlist is None:
            watchlist = Watchlist(security_id=security_id)
            self.session.add(watchlist)

        watchlist.target_buy_price = target_buy_price
        watchlist.max_acceptable_pe = max_pe
        watchlist.min_margin_of_safety = min_margin_of_safety
        for key, value in thresholds.items():
            if hasattr(watchlist, key):
                setattr(watchlist, key, value)

        passes_screen = self._passes_watchlist_screen(watchlist)
        self.session.commit()
        return {"watchlist_entry": watchlist, "passes_screen": passes_screen}

    def create_portfolio(
        self,
        name: str,
        description: str | None = None,
        cash_balance: Decimal = Decimal("0"),
    ) -> Portfolio:
        portfolio = Portfolio(
            name=name,
            description=description,
            cash_balance=cash_balance,
        )
        self.session.add(portfolio)
        self.session.commit()
        return portfolio

    def _passes_watchlist_screen(self, watchlist: Watchlist) -> bool:
        latest_ratio = (
            self.session.query(ValuationRatio)
            .filter(ValuationRatio.security_id == watchlist.security_id)
            .order_by(ValuationRatio.calc_date.desc())
            .first()
        )
        latest_value = self._latest_intrinsic_value(watchlist.security_id)
        if latest_ratio is None or latest_value is None:
            return False
        checks = [
            latest_ratio.pe_ratio is not None and latest_ratio.pe_ratio <= watchlist.max_acceptable_pe,
            latest_ratio.pb_ratio is None or latest_ratio.pb_ratio <= watchlist.max_acceptable_pb,
            latest_ratio.current_ratio is None or latest_ratio.current_ratio >= watchlist.min_current_ratio,
            latest_ratio.debt_to_equity is None or latest_ratio.debt_to_equity <= watchlist.max_debt_to_equity,
            latest_value.margin_of_safety_pct is not None
            and latest_value.margin_of_safety_pct >= watchlist.min_margin_of_safety,
        ]
        return all(checks)

    def _latest_intrinsic_value(self, security_id: UUID) -> IntrinsicValue | None:
        return (
            self.session.query(IntrinsicValue)
            .filter(IntrinsicValue.security_id == security_id)
            .order_by(IntrinsicValue.calc_date.desc())
            .first()
        )
