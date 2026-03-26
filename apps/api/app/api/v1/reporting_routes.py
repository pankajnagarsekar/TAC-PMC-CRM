from fastapi import APIRouter, Depends, Query
from typing import Optional, Dict, Any

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_reporting_service
from app.services.reporting_service import ReportingService

router = APIRouter(prefix="/reports", tags=["Reporting"])

@router.get("/{project_id}/{report_type}")
async def get_report(
    project_id: str,
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service)
):
    return await reporting_service.get_report(user, project_id, report_type, start_date, end_date)
