from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_authenticated_user, get_site_service
from app.modules.shared.domain.schemas import GenericResponse

from ..application.site_service import SiteService
from ..schemas.dto import (
    DPRImage,
    DPRCreate,
    RejectDPRRequest,
    SiteOverhead,
    SiteOverheadCreate,
    SiteOverheadUpdate,
    UpdateImageCaptionRequest,
    WorkersDailyLog,
    WorkersDailyLogCreate,
    WorkersDailyLogUpdate,
)

router = APIRouter()

# --- WORKER LOG ENDPOINTS ---


@router.post(
    "/worker-logs/",
    response_model=GenericResponse[WorkersDailyLog],
    status_code=status.HTTP_201_CREATED,
    tags=["Site Operations"],
)
async def create_worker_log(
    log_data: WorkersDailyLogCreate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.create_worker_log(user, log_data)
    return GenericResponse(
        data=result, message="Worker log created/updated successfully"
    )


@router.put(
    "/worker-logs/{log_id}",
    response_model=GenericResponse[WorkersDailyLog],
    tags=["Site Operations"],
)
async def update_worker_log(
    log_id: str,
    update_data: WorkersDailyLogUpdate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.update_worker_log(user, log_id, update_data)
    return GenericResponse(data=result, message="Worker log updated successfully")


@router.get(
    "/worker-logs", response_model=GenericResponse[List[Any]], tags=["Site Operations"]
)
async def list_worker_logs(
    project_id: str,
    limit: int = Query(100),
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    """List worker logs for a project."""
    result = await site_service.list_site_logs(user, project_id, limit=limit)
    return GenericResponse(data=result)


# --- DPR ENDPOINTS ---


@router.get(
    "/projects/{project_id}/dprs",
    response_model=GenericResponse[List[Any]],
    tags=["Site Operations"],
)
async def list_project_dprs(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.list_project_dprs(user, project_id)
    return GenericResponse(data=result)


@router.post(
    "/dprs/",
    response_model=GenericResponse[Any],
    status_code=status.HTTP_201_CREATED,
    tags=["Site Operations"],
)
async def create_dpr(
    dpr_data: DPRCreate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    """Creates a new DPR draft."""
    result = await site_service.create_dpr(user, dpr_data.project_id, dpr_data.dict())
    return GenericResponse(data=result)


@router.delete(
    "/dprs/{dpr_id}", response_model=GenericResponse[Any], tags=["Site Operations"]
)
async def delete_dpr(
    dpr_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.delete_dpr(user, dpr_id)
    return GenericResponse(data=result, message="DPR deleted successfully")


@router.get(
    "/dprs/{dpr_id}", response_model=GenericResponse[Any], tags=["Site Operations"]
)
async def get_dpr_detail(
    dpr_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.get_dpr_detail(user, dpr_id)
    return GenericResponse(data=result)


@router.patch(
    "/dprs/{dpr_id}/approve",
    response_model=GenericResponse[Any],
    tags=["Site Operations"],
)
async def approve_dpr(
    dpr_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.approve_dpr(user, dpr_id)
    return GenericResponse(data=result, message="DPR approved successfully")


@router.patch(
    "/dprs/{dpr_id}/reject",
    response_model=GenericResponse[Any],
    tags=["Site Operations"],
)
async def reject_dpr(
    dpr_id: str,
    body: RejectDPRRequest,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.reject_dpr(user, dpr_id, body.reason)
    return GenericResponse(data=result, message="DPR rejected successfully")


@router.post(
    "/dprs/{dpr_id}/images",
    response_model=GenericResponse[Any],
    status_code=status.HTTP_201_CREATED,
    tags=["Site Operations"],
)
async def add_dpr_image(
    dpr_id: str,
    image_data: DPRImage,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.add_dpr_image(user, dpr_id, image_data)
    return GenericResponse(data=result)


@router.put(
    "/dprs/{dpr_id}/images/{image_id}",
    response_model=GenericResponse[Any],
    tags=["Site Operations"],
)
async def update_image_caption(
    dpr_id: str,
    image_id: str,
    request: UpdateImageCaptionRequest,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.update_image_caption(
        user, dpr_id, image_id, request.caption
    )
    return GenericResponse(data=result)


@router.post(
    "/dprs/{dpr_id}/submit",
    response_model=GenericResponse[Any],
    tags=["Site Operations"],
)
async def submit_dpr(
    dpr_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.submit_dpr(user, dpr_id)
    return GenericResponse(data=result, message="DPR submitted successfully")


# --- ATTENDANCE ENDPOINTS ---


@router.get(
    "/projects/{project_id}/attendance",
    response_model=GenericResponse[List[Any]],
    tags=["Site Operations"],
)
async def list_project_attendance(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.list_project_attendance(user, project_id)
    return GenericResponse(data=result)


@router.get(
    "/attendance/today",
    response_model=GenericResponse[Optional[Any]],
    tags=["Site Operations"],
)
async def get_project_attendance_today(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.get_today_attendance(user, project_id)
    return GenericResponse(data=result)


@router.get(
    "/attendance/admin/all",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Site Operations"],
)
async def list_all_attendance(
    project_id: str,
    date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    """Admin view for all supervisor attendance records."""
    filters = {"project_id": project_id}
    if date:
        filters["date"] = date
    if start_date and end_date:
        filters["date_range"] = (start_date, end_date)
    if search:
        filters["search"] = search

    records = await site_service.list_project_attendance(
        user, project_id, filters=filters
    )
    return GenericResponse(data={"attendance": records})


@router.get(
    "/attendance/export",
    tags=["Site Operations"],
)
async def export_attendance_excel(
    project_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    from fastapi.responses import StreamingResponse
    import io
    from app.core.export_service import ExportService

    filters = {"project_id": project_id}
    if start_date and end_date:
        filters["date_range"] = (start_date, end_date)

    records = await site_service.list_project_attendance(user, project_id, filters=filters)
    # Map records to rows for ExportService
    rows = [
        [
            r.get("date"),
            r.get("worker_name"),
            r.get("category"),
            r.get("check_in"),
            r.get("check_out")
        ]
        for r in records
    ]
    
    excel_bytes = ExportService.export_to_excel("attendance", {"rows": rows})
    
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=attendance.xlsx"}
    )


@router.get(
    "/attendance/export-pdf",
    tags=["Site Operations"],
)
async def export_attendance_pdf(
    project_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    from fastapi.responses import StreamingResponse
    import io
    from app.core.export_service import ExportService

    filters = {"project_id": project_id}
    if start_date and end_date:
        filters["date_range"] = (start_date, end_date)

    records = await site_service.list_project_attendance(user, project_id, filters=filters)
    rows = [
        [
            r.get("date"),
            r.get("worker_name"),
            r.get("category"),
            r.get("check_in"),
            r.get("check_out")
        ]
        for r in records
    ]
    
    pdf_bytes = ExportService.export_to_pdf_service("attendance", {"rows": rows, "title": "Attendance Report"})
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=attendance.pdf"}
    )


@router.post(
    "/attendance/check-in",
    response_model=GenericResponse[Any],
    tags=["Site Operations"],
)
async def check_in(
    data: Dict[str, Any],
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    project_id = data.get("project_id")
    if not project_id:
        from app.modules.shared.domain.exceptions import ValidationError

        raise ValidationError("project_id is required")

    result = await site_service.check_in(user, project_id, data)
    return GenericResponse(data=result, message="Checked in successfully")


@router.post(
    "/attendance/check-out",
    response_model=GenericResponse[Any],
    tags=["Site Operations"],
)
async def check_out(
    data: Dict[str, Any],
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    project_id = data.get("project_id")
    if not project_id:
        from app.modules.shared.domain.exceptions import ValidationError

        raise ValidationError("project_id is required")

    result = await site_service.check_out(user, project_id, data)
    return GenericResponse(data=result, message="Checked out successfully")


@router.patch(
    "/attendance/{log_id}/verify",
    response_model=GenericResponse[Any],
    tags=["Site Operations"],
)
async def verify_attendance(
    log_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.verify_attendance(user, log_id)
    return GenericResponse(data=result)


# --- VOICE LOG ENDPOINTS ---


@router.get(
    "/projects/{project_id}/voice-logs",
    response_model=GenericResponse[List[Any]],
    tags=["Site Operations"],
)
async def list_project_voice_logs(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.list_project_voice_logs(user, project_id)
    return GenericResponse(data=result)


@router.post(
    "/voice-logs",
    response_model=GenericResponse[Any],
    status_code=status.HTTP_201_CREATED,
    tags=["Site Operations"],
)
async def create_voice_log(
    log_data: Dict[str, Any],
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    """Saves a transcribed voice log to project activity."""
    # Note: Using generic dict for flexibility, Service will validate
    result = await site_service.create_voice_log(user, log_data)
    return GenericResponse(data=result)


# --- SITE OVERHEAD ENDPOINTS ---


@router.get(
    "/projects/{project_id}/site-overheads",
    response_model=GenericResponse[List[SiteOverhead]],
    tags=["Site Operations"],
)
async def list_site_overheads(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.list_site_overheads(user, project_id)
    return GenericResponse(data=result)


@router.post(
    "/site-overheads",
    response_model=GenericResponse[SiteOverhead],
    status_code=status.HTTP_201_CREATED,
    tags=["Site Operations"],
)
async def create_site_overhead(
    overhead_data: SiteOverheadCreate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.create_site_overhead(user, overhead_data)
    return GenericResponse(data=result)


@router.put(
    "/site-overheads/{entry_id}",
    response_model=GenericResponse[SiteOverhead],
    tags=["Site Operations"],
)
async def update_site_overhead(
    entry_id: str,
    overhead_data: SiteOverheadUpdate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service),
):
    result = await site_service.update_site_overhead(user, entry_id, overhead_data)
    return GenericResponse(data=result)
