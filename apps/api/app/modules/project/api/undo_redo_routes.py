"""
Undo/Redo API Routes
RESTful endpoints for schedule undo/redo functionality.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from app.core.dependencies import (
    get_authenticated_user,
    get_undo_redo_service,
    get_scheduler_service,
)
from app.modules.project.application.undo_redo_service import UndoRedoService
from app.modules.project.application.scheduler_service import SchedulerService
from app.modules.shared.domain.schemas import GenericResponse

router = APIRouter(tags=["Scheduler History"])


@router.get(
    "/scheduler/{project_id}/history",
    response_model=GenericResponse[List[Dict[str, Any]]],
)
async def list_history(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    undo_redo_service: UndoRedoService = Depends(get_undo_redo_service),
):
    """List schedule history entries for a project (most recent first)."""
    entries = await undo_redo_service.list_history(project_id, user["organisation_id"])
    return GenericResponse(data=entries)


@router.get(
    "/scheduler/{project_id}/history/stack-info",
    response_model=GenericResponse[Dict[str, Any]],
)
async def get_stack_info(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    undo_redo_service: UndoRedoService = Depends(get_undo_redo_service),
):
    """Return can_undo / can_redo / current version metadata."""
    info = await undo_redo_service.get_stack_info(
        project_id, user["organisation_id"]
    )
    return GenericResponse(data=info)


@router.post(
    "/scheduler/{project_id}/undo",
    response_model=GenericResponse[Dict[str, Any]],
)
async def undo_schedule(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    undo_redo_service: UndoRedoService = Depends(get_undo_redo_service),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
):
    """Undo last schedule change and persist restored state."""
    tasks = await undo_redo_service.undo(
        project_id, user["organisation_id"], user["user_id"]
    )
    if tasks is not None:
        # Persist restored state — use raw save to avoid snapshot capture loop
        await scheduler_service.save_schedule_raw(
            project_id, user["organisation_id"], user["user_id"], {"tasks": tasks}
        )

    stack_info = await undo_redo_service.get_stack_info(
        project_id, user["organisation_id"]
    )
    return GenericResponse(
        data={"tasks": tasks, "stack_info": stack_info},
        message="Schedule undone successfully",
    )


@router.post(
    "/scheduler/{project_id}/redo",
    response_model=GenericResponse[Dict[str, Any]],
)
async def redo_schedule(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    undo_redo_service: UndoRedoService = Depends(get_undo_redo_service),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
):
    """Redo a previously undone schedule change."""
    tasks = await undo_redo_service.redo(
        project_id, user["organisation_id"], user["user_id"]
    )
    if tasks is not None:
        await scheduler_service.save_schedule_raw(
            project_id, user["organisation_id"], user["user_id"], {"tasks": tasks}
        )

    stack_info = await undo_redo_service.get_stack_info(
        project_id, user["organisation_id"]
    )
    return GenericResponse(
        data={"tasks": tasks, "stack_info": stack_info},
        message="Schedule redone successfully",
    )


@router.post(
    "/scheduler/{project_id}/history/{change_id}/restore",
    response_model=GenericResponse[Dict[str, Any]],
)
async def restore_to_version(
    project_id: str,
    change_id: str,
    user: dict = Depends(get_authenticated_user),
    undo_redo_service: UndoRedoService = Depends(get_undo_redo_service),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
):
    """Restore schedule to a specific history point."""
    tasks = await undo_redo_service.restore_to(
        project_id, user["organisation_id"], user["user_id"], change_id
    )
    await scheduler_service.save_schedule_raw(
        project_id, user["organisation_id"], user["user_id"], {"tasks": tasks}
    )
    return GenericResponse(
        data={"tasks": tasks},
        message="Schedule restored successfully",
    )
