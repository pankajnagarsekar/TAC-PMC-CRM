from fastapi import APIRouter, Depends, status, Query
from typing import Dict, Any, List

from app.core.dependencies import get_authenticated_user, get_site_service
from app.services.site_service import SiteService
from app.schemas.site import (
    WorkersDailyLog, WorkersDailyLogCreate, WorkersDailyLogUpdate, 
    DPRImage, UpdateImageCaptionRequest,
    SiteOverhead, SiteOverheadCreate, SiteOverheadUpdate
)
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/site", tags=["Site Operations"])

@router.post("/worker-logs", response_model=GenericResponse[WorkersDailyLog], status_code=status.HTTP_201_CREATED)
async def create_worker_log(
    log_data: WorkersDailyLogCreate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.create_worker_log(user, log_data)
    return GenericResponse(data=result, message="Worker log created/updated successfully")

@router.put("/worker-logs/{log_id}", response_model=GenericResponse[WorkersDailyLog])
async def update_worker_log(
    log_id: str,
    update_data: WorkersDailyLogUpdate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.update_worker_log(user, log_id, update_data)
    return GenericResponse(data=result, message="Worker log updated successfully")

@router.get("/projects/{project_id}/dprs", response_model=GenericResponse[List[Any]])
async def list_project_dprs(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.list_project_dprs(user, project_id)
    return GenericResponse(data=result)

@router.get("/dprs/{dpr_id}", response_model=GenericResponse[Any])
async def get_dpr_detail(
    dpr_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.get_dpr_detail(user, dpr_id)
    return GenericResponse(data=result)

@router.patch("/dprs/{dpr_id}/approve", response_model=GenericResponse[Any])
async def approve_dpr(
    dpr_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.approve_dpr(user, dpr_id)
    return GenericResponse(data=result, message="DPR approved successfully")

@router.patch("/dprs/{dpr_id}/reject", response_model=GenericResponse[Any])
async def reject_dpr(
    dpr_id: str,
    reason: str = Query("", min_length=1, max_length=500),
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.reject_dpr(user, dpr_id, reason)
    return GenericResponse(data=result, message="DPR rejected successfully")

@router.get("/projects/{project_id}/attendance", response_model=GenericResponse[List[Any]])
async def list_project_attendance(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.list_project_attendance(user, project_id)
    return GenericResponse(data=result)

@router.patch("/attendance/{log_id}/verify", response_model=GenericResponse[Any])
async def verify_attendance(
    log_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.verify_attendance(user, log_id)
    return GenericResponse(data=result)

@router.get("/projects/{project_id}/voice-logs", response_model=GenericResponse[List[Any]])
async def list_project_voice_logs(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.list_project_voice_logs(user, project_id)
    return GenericResponse(data=result)

@router.post("/dprs/{dpr_id}/images", response_model=GenericResponse[Any], status_code=status.HTTP_201_CREATED)
async def add_dpr_image(
    dpr_id: str,
    image_data: DPRImage,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.add_dpr_image(user, dpr_id, image_data)
    return GenericResponse(data=result)

@router.put("/dprs/{dpr_id}/images/{image_id}", response_model=GenericResponse[Any])
async def update_image_caption(
    dpr_id: str,
    image_id: str,
    request: UpdateImageCaptionRequest,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.update_image_caption(user, dpr_id, image_id, request.caption)
    return GenericResponse(data=result)

@router.post("/dprs/{dpr_id}/submit", response_model=GenericResponse[Any])
async def submit_dpr(
    dpr_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.submit_dpr(user, dpr_id)
    return GenericResponse(data=result, message="DPR submitted successfully")

@router.get("/projects/{project_id}/site-overheads", response_model=GenericResponse[List[SiteOverhead]])
async def list_site_overheads(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.list_site_overheads(user, project_id)
    return GenericResponse(data=result)

@router.post("/site-overheads", response_model=GenericResponse[SiteOverhead], status_code=status.HTTP_201_CREATED)
async def create_site_overhead(
    overhead_data: SiteOverheadCreate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.create_site_overhead(user, overhead_data)
    return GenericResponse(data=result)

@router.put("/site-overheads/{entry_id}", response_model=GenericResponse[SiteOverhead])
async def update_site_overhead(
    entry_id: str,
    overhead_data: SiteOverheadUpdate,
    user: dict = Depends(get_authenticated_user),
    site_service: SiteService = Depends(get_site_service)
):
    result = await site_service.update_site_overhead(user, entry_id, overhead_data)
    return GenericResponse(data=result)
