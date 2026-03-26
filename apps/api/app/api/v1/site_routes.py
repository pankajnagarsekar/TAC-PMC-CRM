from fastapi import APIRouter, Depends, status
from typing import Dict, Any, List

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_site_service
from app.services.site_service import SiteService
from app.schemas.site import WorkersDailyLog, WorkersDailyLogCreate, WorkersDailyLogUpdate
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
