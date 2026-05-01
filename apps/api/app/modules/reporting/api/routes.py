from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.core.dependencies import (
    PermissionChecker,
    get_ai_service,
    get_ai_summary_service,
    get_authenticated_user,
    get_analytics_service,
    get_dashboard_service,
    get_permission_checker,
    get_reporting_service,
)
from app.modules.shared.domain.schemas import GenericResponse
from app.modules.reporting.domain.metrics import (
    ProjectDashboardData,
    ScheduleHealthMetrics,
    ResourceUtilizationData,
    FinancialSummaryData,
    TimelineAnalytics,
)

from ..application.ai_service import AIService
from ..application.ai_summary_service import AISummaryService
from ..application.analytics_service import AnalyticsService
from ..application.dashboard_service import DashboardService
from ..application.reporting_service import ReportingService

router = APIRouter()

# --- ANALYTICS & DASHBOARD ENDPOINTS (B1.4) ---


@router.get(
    "/reporting/{project_id}/dashboard",
    response_model=GenericResponse[ProjectDashboardData],
    tags=["Analytics Dashboard"],
)
async def get_project_dashboard(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """Get complete dashboard data (cached 30 seconds)."""
    await checker.check_project_access(user, project_id)
    data = await dashboard_service.get_project_dashboard(
        project_id, user["organisation_id"]
    )
    return GenericResponse(data=data)


@router.get(
    "/reporting/{project_id}/analytics/schedule-health",
    response_model=GenericResponse[ScheduleHealthMetrics],
    tags=["Analytics Dashboard"],
)
async def get_schedule_health(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """Get schedule health metrics."""
    await checker.check_project_access(user, project_id)
    metrics = await analytics_service.calculate_schedule_health(
        project_id, user["organisation_id"]
    )
    return GenericResponse(data=metrics.to_dict())


@router.get(
    "/reporting/{project_id}/analytics/resource-utilization",
    response_model=GenericResponse[ResourceUtilizationData],
    tags=["Analytics Dashboard"],
)
async def get_resource_utilization(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """Get resource utilization metrics."""
    await checker.check_project_access(user, project_id)
    data = await analytics_service.calculate_resource_utilization(
        project_id, user["organisation_id"]
    )
    return GenericResponse(data=data.to_dict())


@router.get(
    "/reporting/{project_id}/analytics/financial-summary",
    response_model=GenericResponse[FinancialSummaryData],
    tags=["Analytics Dashboard"],
)
async def get_financial_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """Get financial summary metrics."""
    await checker.check_project_access(user, project_id)
    data = await analytics_service.calculate_financial_summary(
        project_id, user["organisation_id"]
    )
    return GenericResponse(data=data.to_dict())


@router.get(
    "/reporting/{project_id}/analytics/timeline",
    response_model=GenericResponse[TimelineAnalytics],
    tags=["Analytics Dashboard"],
)
async def get_timeline_analytics(
    project_id: str,
    start: Optional[str] = Query(None, description="Start date (ISO format)"),
    end: Optional[str] = Query(None, description="End date (ISO format)"),
    user: dict = Depends(get_authenticated_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """Get timeline analytics over date range (default: last 30 days)."""
    await checker.check_project_access(user, project_id)

    # Parse dates
    start_date = None
    end_date = None
    if start:
        start_date = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if end:
        end_date = datetime.fromisoformat(end.replace("Z", "+00:00"))

    data = await analytics_service.calculate_timeline_analytics(
        project_id, user["organisation_id"], start_date, end_date
    )
    return GenericResponse(data=data.to_dict())


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


@router.get(
    "/reports/{project_id}/ai-summary/stream/{summary_type}",
    tags=["Reporting"],
)
async def stream_summary(
    project_id: str,
    summary_type: str,
    user: dict = Depends(get_authenticated_user),
    ai_service: AISummaryService = Depends(get_ai_summary_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """Stream a summary word-by-word (schedule, financial, resources)."""
    await checker.check_project_access(user, project_id)

    async def generate():
        async for chunk in ai_service.stream_summary(
            summary_type, project_id, user["organisation_id"]
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- PROJECT REPORTING ENDPOINTS ---


@router.get(
    "/admin/projects-overview",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Admin"],
)
async def get_projects_overview(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    """Provides a bird's-eye view with resilient loading and pagination (BUG-024)."""
    overview = await reporting_service.get_projects_overview(user, skip=skip, limit=limit)
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
    "/reports/{project_id}/{report_type}/export/excel",
    tags=["Reporting"],
)
async def export_report_excel(
    project_id: str,
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sync: bool = Query(True),
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service),
    background_tasks: BackgroundTasks = None,
):
    from fastapi.responses import StreamingResponse
    import io
    from app.core.export_service import ExportService
    from app.core.jobs import JobTracker

    if not sync:
        job_id = JobTracker.create_job(f"excel_{report_type}")

        async def run_task():
            try:
                report_data = await reporting_service.get_report(
                    user, project_id, report_type, start_date, end_date
                )
                ExportService.export_to_excel(report_type, report_data)
                JobTracker.update_job(job_id, "SUCCESS")
            except Exception as e:
                JobTracker.update_job(job_id, "FAILED", error=str(e))

        from fastapi import BackgroundTasks
        if isinstance(background_tasks, BackgroundTasks):
            background_tasks.add_task(run_task)
        return {"job_id": job_id}

    report_data = await reporting_service.get_report(
        user, project_id, report_type, start_date, end_date
    )
    excel_bytes = ExportService.export_to_excel(report_type, report_data)

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={report_type}.xlsx"}
    )


@router.get(
    "/reports/{project_id}/{report_type}/export/pdf",
    tags=["Reporting"],
)
async def export_report_pdf(
    project_id: str,
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sync: bool = Query(True),
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service),
    background_tasks: BackgroundTasks = None,
):
    from fastapi.responses import StreamingResponse
    import io
    from app.core.export_service import ExportService
    from app.core.jobs import JobTracker

    if not sync:
        job_id = JobTracker.create_job(f"pdf_{report_type}")

        async def run_task():
            try:
                report_data = await reporting_service.get_report(
                    user, project_id, report_type, start_date, end_date
                )
                ExportService.export_to_pdf_service(report_type, report_data)
                JobTracker.update_job(job_id, "SUCCESS")
            except Exception as e:
                JobTracker.update_job(job_id, "FAILED", error=str(e))

        from fastapi import BackgroundTasks
        if isinstance(background_tasks, BackgroundTasks):
            background_tasks.add_task(run_task)
        return {"job_id": job_id}

    report_data = await reporting_service.get_report(
        user, project_id, report_type, start_date, end_date
    )
    pdf_bytes = ExportService.export_to_pdf_service(report_type, report_data)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={report_type}.pdf"}
    )


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
