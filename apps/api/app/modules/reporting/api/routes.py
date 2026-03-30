from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import (
    PermissionChecker,
    get_ai_service,
    get_ai_summary_service,
    get_authenticated_user,
    get_dashboard_service,
    get_permission_checker,
    get_reporting_service,
)
from app.modules.shared.domain.schemas import GenericResponse

from ..application.ai_service import AIService
from ..application.ai_summary_service import AISummaryService
from ..application.dashboard_service import DashboardService
from ..application.reporting_service import ReportingService

router = APIRouter()

# --- AI ENDPOINTS ---


@router.post(
    "/speech-to-text", response_model=GenericResponse[Dict[str, Any]], tags=["AI"]
)
async def project_speech_to_text(
    data: Dict[str, Any],
    user: dict = Depends(get_authenticated_user),
    ai_service: AIService = Depends(get_ai_service),
):
    """Voice to Text transcription for DPRs."""
    text = await ai_service.transcribe_audio(user, data.get("audio_data", ""))
    return GenericResponse(data={"text": text})


# --- PROJECT REPORTING ENDPOINTS ---


@router.get(
    "/admin/projects-overview",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Admin"],
)
async def get_projects_overview(
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    """Provides a bird's-eye view of all projects for the admin dashboard."""
    overview = await reporting_service.get_projects_overview(user)
    return GenericResponse(data=overview)


@router.get(
    "/reports/{project_id}/{report_type}",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Reporting"],
)
async def get_report(
    project_id: str,
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    report = await reporting_service.get_report(
        user, project_id, report_type, start_date, end_date
    )
    return GenericResponse(data=report)


@router.get(
    "/reports/{project_id}/dashboard-stats",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Reporting"],
)
async def get_reporting_dashboard_stats(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    stats = await reporting_service.get_dashboard_stats(user, project_id)
    return GenericResponse(data=stats)


# --- DASHBOARD STATISTICS ENDPOINTS ---


@router.get(
    "/projects/{project_id}/dashboard-stats",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Dashboard Statistics"],
)
async def get_project_dashboard_stats(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """Returns aggregated statistics for the project dashboard."""
    await checker.check_project_access(user, project_id)
    stats = await dashboard_service.get_project_dashboard_stats(
        project_id, user["organisation_id"]
    )
    return GenericResponse(data=stats)


@router.get(
    "/projects/{project_id}/financials",
    response_model=GenericResponse[List[Any]],
    tags=["Dashboard Statistics"],
)
async def get_project_financials(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    await checker.check_project_access(user, project_id)
    financials = await dashboard_service.get_financials(project_id)
    return GenericResponse(data=financials)


@router.get(
    "/projects/{project_id}/vendor-payables",
    response_model=GenericResponse[List[Any]],
    tags=["Dashboard Statistics"],
)
async def get_project_vendor_payables(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    await checker.check_project_access(user, project_id)
    payables = await dashboard_service.get_vendor_payables(project_id)
    return GenericResponse(data=payables)


# --- AI SUMMARY ENDPOINTS ---


@router.get(
    "/reports/{project_id}/ai-summary",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Reporting"],
)
async def get_latest_ai_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    ai_service: AISummaryService = Depends(get_ai_summary_service),
):
    result = await ai_service.get_latest(user, project_id)
    return GenericResponse(data=result)


@router.post(
    "/reports/{project_id}/ai-summary/refresh",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Reporting"],
)
async def refresh_ai_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    ai_service: AISummaryService = Depends(get_ai_summary_service),
):
    result = await ai_service.refresh_summary(user, project_id)
    return GenericResponse(data=result, message="AI Summary refreshed successfully")
