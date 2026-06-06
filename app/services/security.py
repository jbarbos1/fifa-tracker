"""Security registration service."""

from __future__ import annotations

from app.extensions import db

from app.models.securities import Security


class SecurityService:
    def __init__(self, session=None):
        self.session = session or db.session

    def register_security(
        self,
        ticker: str,
        exchange: str | None = None,
        name: str | None = None,
        **attrs,
    ) -> Security:
        normalized_ticker = ticker.strip().upper()
        security = (
            self.session.query(Security)
            .filter(Security.ticker == normalized_ticker)
            .one_or_none()
        )
        if security is None:
            security = Security(
                ticker=normalized_ticker,
                name=name or normalized_ticker,
                exchange=exchange,
                **attrs,
            )
            self.session.add(security)
        else:
            if exchange is not None:
                security.exchange = exchange
            if name is not None:
                security.name = name
            for key, value in attrs.items():
                if hasattr(security, key):
                    setattr(security, key, value)

        self.session.commit()
        return security
