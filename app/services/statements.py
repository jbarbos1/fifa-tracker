"""Statement parsing and persistence service."""

from __future__ import annotations

from uuid import UUID

from app.extensions import db

from app.models.securities import BalanceSheet, CashFlowStatement, IncomeStatement
from ._helpers import set_known_attrs


class StatementService:
    def __init__(self, session=None):
        self.session = session or db.session

    def parse_statements(self, report_id: UUID, raw_data: dict) -> dict[str, object]:
        balance_sheet = self._upsert_one_to_one(
            BalanceSheet,
            report_id,
            self._normalize_balance_sheet(raw_data.get("balance_sheet", {})),
        )
        income_statement = self._upsert_one_to_one(
            IncomeStatement,
            report_id,
            self._normalize_income_statement(raw_data.get("income_statement", {})),
        )
        cash_flow_statement = self._upsert_one_to_one(
            CashFlowStatement,
            report_id,
            self._normalize_cash_flow(raw_data.get("cash_flow_statement", {})),
        )

        self.session.commit()
        return {
            "balance_sheet": balance_sheet,
            "income_statement": income_statement,
            "cash_flow_statement": cash_flow_statement,
        }

    def _upsert_one_to_one(self, model_cls, report_id: UUID, values: dict):
        row = self.session.query(model_cls).filter(model_cls.report_id == report_id).one_or_none()
        if row is None:
            row = model_cls(report_id=report_id)
            self.session.add(row)
        set_known_attrs(row, values)
        return row

    @staticmethod
    def _normalize_balance_sheet(values: dict) -> dict:
        normalized = dict(values)
        aliases = {
            "cash_equivalents": "cash_and_equivalents",
            "current_assets": "total_current_assets",
            "current_liabilities": "total_current_liabilities",
        }
        for source, target in aliases.items():
            if source in normalized and target not in normalized:
                normalized[target] = normalized[source]
        if "net_current_assets" not in normalized:
            current_assets = normalized.get("total_current_assets")
            total_liabilities = normalized.get("total_liabilities")
            if current_assets is not None and total_liabilities is not None:
                normalized["net_current_assets"] = current_assets - total_liabilities
        if "ncav" not in normalized and "net_current_assets" in normalized:
            normalized["ncav"] = normalized["net_current_assets"]
        return normalized

    @staticmethod
    def _normalize_income_statement(values: dict) -> dict:
        normalized = dict(values)
        aliases = {
            "operating_expenses": "total_operating_expenses",
            "tax_expense": "income_tax_expense",
            "shares_outstanding": "shares_outstanding_diluted",
        }
        for source, target in aliases.items():
            if source in normalized and target not in normalized:
                normalized[target] = normalized[source]
        return normalized

    @staticmethod
    def _normalize_cash_flow(values: dict) -> dict:
        normalized = dict(values)
        aliases = {
            "cfo": "cash_from_operations",
            "capex": "capital_expenditures",
            "cfi": "cash_from_investing",
            "cff": "cash_from_financing",
        }
        for source, target in aliases.items():
            if source in normalized and target not in normalized:
                normalized[target] = normalized[source]
        if "free_cash_flow" not in normalized:
            cfo = normalized.get("cash_from_operations")
            capex = normalized.get("capital_expenditures")
            if cfo is not None and capex is not None:
                normalized["free_cash_flow"] = cfo + capex
        return normalized
