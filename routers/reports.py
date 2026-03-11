"""/api/reports — pre-generated report access."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Report
from services.report_generator import generate_all_reports

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
async def list_reports(
    report_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all reports (metadata only). Optionally filter by type."""
    query = select(Report).order_by(Report.report_type, Report.report_key)
    if report_type:
        query = query.where(Report.report_type == report_type)

    result = await db.execute(query)
    reports = result.scalars().all()

    return {
        "total": len(reports),
        "reports": [
            {
                "report_type": r.report_type,
                "report_key": r.report_key,
                "title": r.title,
                "category": r.category,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "data_coverage": r.data_coverage,
            }
            for r in reports
        ],
    }


@router.get("/{report_type}/{report_key}")
async def get_report(
    report_type: str,
    report_key: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single report with full data."""
    result = await db.execute(
        select(Report).where(
            Report.report_type == report_type,
            Report.report_key == report_key,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "report_type": report.report_type,
        "report_key": report.report_key,
        "title": report.title,
        "category": report.category,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "data_coverage": report.data_coverage,
        "data": json.loads(report.data),
    }


@router.post("/generate")
async def trigger_generation(db: AsyncSession = Depends(get_db)):
    """Regenerate all reports."""
    count = await generate_all_reports(db)
    return {"reports_generated": count}
