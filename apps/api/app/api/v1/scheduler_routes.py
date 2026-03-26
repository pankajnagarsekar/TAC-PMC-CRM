from fastapi import APIRouter, Depends, status, Query, Body
from typing import List, Dict, Any, Optional
from app.core.dependencies import get_authenticated_user, get_scheduler_service
from app.services.scheduler_service import SchedulerService
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

@router.post("/{project_id}/calculate", response_model=GenericResponse[Dict[str, Any]])
async def calculate_schedule(
    project_id: str,
    data: Dict[str, Any] = Body(...),
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    tasks = data.get("tasks", [])
    project_start = data.get("project_start", "01-01-26")
    results = await service.calculate_schedule(project_id, tasks, project_start)
    return GenericResponse(data=results)

@router.post("/{project_id}/save", response_model=GenericResponse[dict])
async def save_schedule(
    project_id: str,
    data: Dict[str, Any] = Body(...),
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    result = await service.save_schedule(project_id, user["organisation_id"], user["user_id"], data)
    return GenericResponse(data=result, message="Schedule saved successfully")

@router.get("/{project_id}/load", response_model=GenericResponse[Dict[str, Any]])
async def load_schedule(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    result = await service.load_schedule(project_id, user["organisation_id"])
    return GenericResponse(data=result)
