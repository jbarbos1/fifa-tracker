"""Financial report ingestion service."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.extensions import db

from app.models.securities import FinancialReport


class ReportService:
    def __init__(self, session=None):
        self.session = session or db.session

    def ingest_report(
        self,
        security_id: UUID,
        report_type: str,
        period_end: date,
        filed_date: date | None = None,
        fiscal_year: str | None = None,
        fiscal_quarter: str | None = None,
        source_url: str | None = None,
        notes: str | None = None,
    ) -> FinancialReport:
        report = (
            self.session.query(FinancialReport)
            .filter(
                FinancialReport.security_id == security_id,
                FinancialReport.report_type == report_type,
                FinancialReport.period_end == period_end,
            )
            .one_or_none()
        )
        if report is None:
            report = FinancialReport(
                security_id=security_id,
                report_type=report_type,
                period_end=period_end,
            )
            self.session.add(report)

        report.filed_date = filed_date
        report.fiscal_year = fiscal_year
        report.fiscal_quarter = fiscal_quarter
        report.source_url = source_url
        report.notes = notes

        self.session.commit()
        return report
