from fastapi import APIRouter, Depends, Query, status
from typing import List, Any, Dict, Optional

from app.core.dependencies import get_authenticated_user, get_project_service, get_client_service, get_scheduler_service, verify_nonce
from ..application.project_service import ProjectService
from ..application.client_service import ClientService
from ..application.scheduler_service import SchedulerService
from ..schemas.dto import Project, ProjectUpdate, ProjectCreate, ProjectBudgetCreate, Client, ClientCreate, ClientUpdate
from ..schemas.scheduler import ScheduleCalculateRequest, ScheduleSaveRequest, ScheduleResponse
from app.modules.shared.domain.schemas import GenericResponse

router = APIRouter()

# --- PROJECT ENDPOINTS ---

@router.get("/projects/", response_model=GenericResponse[List[Project]], tags=["Projects"])
async def list_projects(
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Fetch all projects for the user's organisation."""
    projects = await project_service.list_projects(user)
    return GenericResponse(data=projects)

@router.post("/projects/", response_model=GenericResponse[Project], status_code=status.HTTP_201_CREATED, tags=["Projects"])
async def create_project(
    project_data: ProjectCreate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
    nonce: str = Depends(verify_nonce)
):
    """Initializes a new project within the user's organisation."""
    project = await project_service.create_project(user, project_data)
    return GenericResponse(data=project, message="Project initialized successfully")

@router.get("/projects/{project_id}", response_model=GenericResponse[Project], tags=["Projects"])
async def get_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Fetch details for a single project."""
    project = await project_service.get_project(user, project_id)
    return GenericResponse(data=project)

@router.put("/projects/{project_id}", response_model=GenericResponse[Project], tags=["Projects"])
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
    nonce: str = Depends(verify_nonce)
):
    """Update project details."""
    project = await project_service.update_project(user, project_id, project_data)
    return GenericResponse(data=project, message="Project updated successfully")

@router.get("/projects/{project_id}/budgets", response_model=GenericResponse[List[Any]], tags=["Projects"])
async def get_project_budgets(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Get all budgets for a project."""
    budgets = await project_service.get_project_budgets(user, project_id)
    return GenericResponse(data=budgets)

@router.post("/projects/{project_id}/budgets", response_model=GenericResponse[Any], tags=["Projects"])
async def create_or_update_project_budget(
    project_id: str,
    budget_data: ProjectBudgetCreate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
    nonce: str = Depends(verify_nonce)
):
    """Create or update a budget allocation for a project category."""
    result = await project_service.create_or_update_project_budget(user, project_id, budget_data.dict())
    return GenericResponse(data=result, message="Budget updated successfully")

@router.delete("/projects/{project_id}", response_model=GenericResponse[dict], tags=["Projects"])
async def delete_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Soft delete project and cascade to related entities."""
    await project_service.delete_project(user, project_id)
    return GenericResponse(data={"status": "deleted"}, message="Project and all related data soft-deleted successfully")

# --- CLIENT ENDPOINTS ---

@router.get("/clients/", response_model=GenericResponse[List[Client]], tags=["Clients"])
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    clients = await client_service.list_clients(user["organisation_id"], skip, limit)
    return GenericResponse(data=clients)

@router.post("/clients/", response_model=GenericResponse[Client], status_code=status.HTTP_201_CREATED, tags=["Clients"])
async def create_client(
    client_data: ClientCreate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    client = await client_service.create_client(user, client_data)
    return GenericResponse(data=client, message="Client created successfully")

@router.get("/clients/{client_id}", response_model=GenericResponse[Client], tags=["Clients"])
async def get_client(
    client_id: str,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    client = await client_service.get_client(client_id, user["organisation_id"])
    return GenericResponse(data=client)

@router.put("/clients/{client_id}", response_model=GenericResponse[Client], tags=["Clients"])
async def update_client(
    client_id: str,
    client_data: ClientUpdate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    client = await client_service.update_client(user, client_id, client_data)
    return GenericResponse(data=client, message="Client updated successfully")

@router.delete("/clients/{client_id}", response_model=GenericResponse[dict], tags=["Clients"])
async def delete_client(
    client_id: str,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Delete a client (Admin only)."""
    await client_service.delete_client(user, client_id)
    return GenericResponse(data={"id": client_id}, message="Client deleted successfully")

# --- SCHEDULER ENDPOINTS ---

@router.post("/{project_id}/calculate-schedule", response_model=GenericResponse[ScheduleResponse], tags=["Scheduler"])
async def calculate_schedule(
    project_id: str,
    request: ScheduleCalculateRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    """Calculate project schedule using critical path method."""
    task_dicts = [task.dict() for task in request.tasks]
    results = await service.calculate_schedule(project_id, task_dicts, request.project_start)
    return GenericResponse(data=results)

@router.post("/{project_id}/save-schedule", response_model=GenericResponse[dict], tags=["Scheduler"])
async def save_schedule(
    project_id: str,
    request: ScheduleSaveRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    """Save calculated project schedule to database."""
    result = await service.save_schedule(project_id, user["organisation_id"], user["user_id"], request.dict())
    return GenericResponse(data=result, message="Schedule saved successfully")

@router.get("/{project_id}/load-schedule", response_model=GenericResponse[Dict[str, Any]], tags=["Scheduler"])
async def load_schedule(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service)
):
    """Load previously saved project schedule."""
    result = await service.load_schedule(project_id, user["organisation_id"])
    return GenericResponse(data=result)
