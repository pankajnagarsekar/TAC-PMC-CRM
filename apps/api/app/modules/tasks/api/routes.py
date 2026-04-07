from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from app.core.dependencies import get_authenticated_user, get_db, get_audit_service, get_permission_checker, get_snapshot_service
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.schemas.dto import Task, TaskCreate, TaskUpdate, TaskStatusUpdate
from app.modules.shared.domain.schemas import GenericResponse

router = APIRouter(prefix="/tasks", tags=["Tasks"])

def get_task_service(
    db = Depends(get_db),
    audit = Depends(get_audit_service),
    perm = Depends(get_permission_checker),
    snap = Depends(get_snapshot_service)
):
    return TaskService(db, audit, perm, snap)

@router.post("/", response_model=GenericResponse[Task], status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service)
):
    try:
        result = await service.create_task(user, data)
        return GenericResponse(data=result, message="Task created successfully")
    except Exception as e:
        import traceback
        print(f"DIAGNOSTIC_TRACEBACK: {traceback.format_exc()}")
        raise e

@router.get("/{task_id}", response_model=GenericResponse[Task])
async def get_task(
    task_id: str,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service)
):
    result = await service.get_task(user, task_id)
    return GenericResponse(data=result)

@router.patch("/{task_id}/status", response_model=GenericResponse[Task])
async def update_status(
    task_id: str,
    data: TaskStatusUpdate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service)
):
    result = await service.update_status(user, task_id, data.status)
    return GenericResponse(data=result, message="Status updated successfully")

@router.patch("/{task_id}", response_model=GenericResponse[Task])
async def update_task(
    task_id: str,
    data: TaskUpdate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service)
):
    result = await service.update_task_details(user, task_id, data)
    return GenericResponse(data=result, message="Task details updated successfully")
