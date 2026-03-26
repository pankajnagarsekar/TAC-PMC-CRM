from fastapi import APIRouter, Depends, status, Query, Body
from typing import List, Dict, Any, Optional
from app.core.dependencies import get_authenticated_user, get_scheduler_service
from app.services.scheduler_service import SchedulerService
from app.schemas.shared import GenericResponse
from app.schemas.scheduler import ScheduleCalculateRequest, ScheduleSaveRequest, ScheduleResponse

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

@router.post("/{project_id}/calculate", response_model=GenericResponse[ScheduleResponse])
async def calculate_schedule(
    project_id: str,
    request: ScheduleCalculateRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    """Calculate project schedule using critical path method."""
    # Fixed CR-12: Added typed request body with Pydantic validation
    task_dicts = [task.dict() for task in request.tasks]
    results = await service.calculate_schedule(project_id, task_dicts, request.project_start)
    return GenericResponse(data=results)

@router.post("/{project_id}/save", response_model=GenericResponse[dict])
async def save_schedule(
    project_id: str,
    request: ScheduleSaveRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    """Save calculated project schedule to database."""
    # Fixed CR-12: Added typed request body with Pydantic validation
    result = await service.save_schedule(project_id, user["organisation_id"], user["user_id"], request.dict())
    return GenericResponse(data=result, message="Schedule saved successfully")

@router.get("/{project_id}/load", response_model=GenericResponse[Dict[str, Any]])
async def load_schedule(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    result = await service.load_schedule(project_id, user["organisation_id"])
    return GenericResponse(data=result)
