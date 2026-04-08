from typing import List
from fastapi import APIRouter, Depends, status
from app.core.dependencies import (
    get_authenticated_user, get_db, get_audit_service,
    get_permission_checker, get_snapshot_service,
)
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.schemas.dto import Task, TaskCreate, TaskUpdate, TaskStatusUpdate
from app.modules.shared.domain.schemas import GenericResponse

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def get_task_service(
    db=Depends(get_db),
    audit=Depends(get_audit_service),
    perm=Depends(get_permission_checker),
    snap=Depends(get_snapshot_service),
):
    return TaskService(db, audit, perm, snap)


# ── COLLECTION ROUTES ────────────────────────────────────────────────────────

@router.post("/", response_model=GenericResponse[Task], status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.create_task(user, data)
    return GenericResponse(data=result, message="Task created successfully")


@router.get("/", response_model=GenericResponse[List[Task]])
async def list_tasks(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.get_tasks(user, project_id)
    return GenericResponse(data=result)


# ── SPECIFIC SUB-PATHS (must precede wildcard /{task_id}) ────────────────────

@router.get("/ai-summary", response_model=GenericResponse)
async def get_task_ai_summary(
    project_id: str = None,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    from fastapi import HTTPException

    if not project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id query parameter is required"
        )

    try:
        result = await service.get_task_summary_for_ai(user, project_id)
        return GenericResponse(data=result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate AI summary: {str(e)}"
        )


# ── ITEM ROUTES (wildcard — must come last) ──────────────────────────────────

@router.get("/{task_id}", response_model=GenericResponse[Task])
async def get_task(
    task_id: str,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.get_task(user, task_id)
    return GenericResponse(data=result)


@router.patch("/{task_id}/status", response_model=GenericResponse[Task])
async def update_status(
    task_id: str,
    data: TaskStatusUpdate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.update_status(user, task_id, data.status)
    return GenericResponse(data=result, message="Status updated successfully")


@router.patch("/{task_id}", response_model=GenericResponse[Task])
async def update_task(
    task_id: str,
    data: TaskUpdate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.update_task_details(user, task_id, data)
    return GenericResponse(data=result, message="Task updated successfully")


@router.delete("/{task_id}", response_model=GenericResponse)
async def delete_task(
    task_id: str,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    await service.delete_task(user, task_id)
    return GenericResponse(data=None, message="Task deleted successfully")
