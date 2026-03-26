from fastapi import APIRouter, Depends, Query
from typing import Optional, Dict, Any

from app.core.dependencies import get_authenticated_user, get_reporting_service
from app.services.reporting_service import ReportingService
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/reports", tags=["Reporting"])

@router.get("/{project_id}/{report_type}", response_model=GenericResponse[Dict[str, Any]])
async def get_report(
    project_id: str,
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service)
):
    report = await reporting_service.get_report(user, project_id, report_type, start_date, end_date)
    return GenericResponse(data=report)

@router.get("/{project_id}/dashboard-stats", response_model=GenericResponse[Dict[str, Any]])
async def get_dashboard_stats(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service)
):
    stats = await reporting_service.get_dashboard_stats(user, project_id)
    return GenericResponse(data=stats)
