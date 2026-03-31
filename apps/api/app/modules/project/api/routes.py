from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import (
    get_authenticated_user,
    get_client_service,
    get_project_service,
    get_scheduler_service,
    get_ai_service,
    verify_nonce,
)
from app.modules.reporting.application.ai_service import AIService
from app.modules.shared.domain.schemas import GenericResponse

from ..application.client_service import ClientService
from ..application.project_service import ProjectService
from ..application.scheduler_service import SchedulerService
from ..schemas.dto import (
    Client,
    ClientCreate,
    Project,
    ProjectBudgetCreate,
    ProjectCreate,
    ProjectUpdate,
)
from ..schemas.scheduler import (
    ScheduleCalculateRequest,
    ScheduleResponse,
    ScheduleSaveRequest,
)

router = APIRouter()

# --- PROJECT ENDPOINTS ---


@router.get(
    "/projects/", response_model=GenericResponse[List[Project]], tags=["Projects"]
)
async def list_projects(
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Fetch all projects accessible to the user (Point 17, 115)."""
    projects = await project_service.list_projects(user)
    return GenericResponse(data=projects)


@router.post(
    "/projects/",
    response_model=GenericResponse[Project],
    status_code=status.HTTP_201_CREATED,
    tags=["Projects"],
)
async def create_project(
    project_data: ProjectCreate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
    nonce: str = Depends(verify_nonce),
):
    """Authoritative project creation (Point 75)."""
    project = await project_service.create_project(user, project_data)
    return GenericResponse(data=project, message="Project created successfully")


@router.get(
    "/projects/{project_id}", response_model=GenericResponse[Project], tags=["Projects"]
)
async def get_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Fetch details for a single project."""
    project = await project_service.get_project(user, project_id)
    return GenericResponse(data=project)


@router.put(
    "/projects/{project_id}", response_model=GenericResponse[Project], tags=["Projects"]
)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Update project metadata."""
    project = await project_service.update_project(user, project_id, project_update)
    return GenericResponse(data=project, message="Project updated successfully")


@router.delete(
    "/projects/{project_id}", response_model=GenericResponse[dict], tags=["Projects"]
)
async def delete_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Soft-delete a project (authoritative Point 87)."""
    result = await project_service.delete_project(user, project_id)
    return GenericResponse(data=result, message="Project deleted successfully")


# --- CLIENT ENDPOINTS ---


@router.get("/clients/", response_model=GenericResponse[List[Client]], tags=["Clients"])
async def list_clients(
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service),
):
    """List all clients within the organisation."""
    clients = await client_service.list_clients(user)
    return GenericResponse(data=clients)


@router.post(
    "/clients/",
    response_model=GenericResponse[Client],
    status_code=status.HTTP_201_CREATED,
    tags=["Clients"],
)
async def create_client(
    client_data: ClientCreate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service),
):
    """Add a new client to the organisation."""
    client = await client_service.create_client(user, client_data)
    return GenericResponse(data=client, message="Client added successfully")


# --- BUDGET ENDPOINTS ---


@router.post(
    "/projects/{project_id}/budgets",
    response_model=GenericResponse[dict],
    tags=["Budgets"],
)
async def create_category_budget(
    project_id: str,
    budget_data: ProjectBudgetCreate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Define budget for a specific category within a project."""
    budget = await project_service.create_category_budget(user, project_id, budget_data)
    return GenericResponse(data=budget, message="Category budget created")


# --- SCHEDULER ENDPOINTS ---


@router.post(
    "/projects/{project_id}/calculate-schedule",
    response_model=GenericResponse[ScheduleResponse],
    tags=["Scheduler"],
)
async def calculate_schedule(
    project_id: str,
    request: ScheduleCalculateRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Trigger schedule recalculation logic."""
    task_dicts = [task.dict() for task in request.tasks]
    result = await service.calculate_schedule(
        project_id, task_dicts, request.project_start
    )
    return GenericResponse(data=result)


@router.post(
    "/scheduler/{project_id}/calculate",
    response_model=GenericResponse[ScheduleResponse],
    tags=["Scheduler"],
)
async def calculate_schedule_legacy(
    project_id: str,
    request: ScheduleCalculateRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Trigger schedule recalculation logic (legacy path)."""
    task_dicts = [task.dict() for task in request.tasks]
    result = await service.calculate_schedule(
        project_id, task_dicts, request.project_start
    )
    return GenericResponse(data=result)


@router.post(
    "/projects/{project_id}/save-schedule",
    response_model=GenericResponse[dict],
    tags=["Scheduler"],
)
async def save_schedule(
    project_id: str,
    request: ScheduleSaveRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Persist calculated schedule to the database."""
    result = await service.save_schedule(
        project_id,
        user["organisation_id"],
        user["user_id"],
        request.dict(),
    )
    return GenericResponse(data=result, message="Schedule saved successfully")


@router.get(
    "/projects/{project_id}/load-schedule",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Scheduler"],
)
async def load_schedule(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Retrieve the current project schedule."""
    result = await service.load_schedule(project_id, user["organisation_id"])
    return GenericResponse(data=result)


@router.get(
    "/projects/{project_id}/baseline/compare",
    response_model=GenericResponse[List[Dict[str, Any]]],
    tags=["Scheduler"],
)
async def compare_baselines(
    project_id: str,
    baseline_a: int = Query(1),
    baseline_b: int = Query(None),
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Compare two baselines."""
    result = await service.compare_baselines(project_id, baseline_a, baseline_b)
    return GenericResponse(data=result)



@router.post(
    "/scheduler/{project_id}/migrate",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Scheduler"],
)
async def migrate_legacy_schedule(
    project_id: str,
    dry_run: bool = Query(True),
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Migrate legacy payment schedule data to the new PPM scheduler (authoritative)."""
    # Note: SchedulerService needs to implement migrate_legacy_data
    # For now, we stub it or point to a script if available
    if hasattr(service, "migrate_legacy_data"):
        result = await service.migrate_legacy_data(
            project_id, user["organisation_id"], dry_run
        )
        return GenericResponse(data=result)

    return GenericResponse(
        success=False,
        message="Migration service not fully implemented in this context.",
    )


@router.post(
    "/projects/{project_id}/tasks/{task_id}/mom-extract",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Scheduler"],
)
async def task_mom_extract(
    project_id: str,
    task_id: str,
    data: Dict[str, Any],
    user: dict = Depends(get_authenticated_user),
    ai_service: AIService = Depends(get_ai_service),
):
    """Analyze meeting notes to extract action items and duration suggestions for a specific task."""
    result = await ai_service.extract_mom(
        project_id, task_id, data.get("raw_notes", "")
    )
    return GenericResponse(data=result)
