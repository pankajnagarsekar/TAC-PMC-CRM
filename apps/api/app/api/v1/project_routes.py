from fastapi import APIRouter, Depends, Body, status
from typing import List, Any
from app.core.dependencies import get_authenticated_user, get_project_service, verify_nonce
from app.services.project_service import ProjectService
from app.schemas.project import Project, ProjectUpdate, ProjectCreate, ProjectBudgetCreate
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/", response_model=GenericResponse[List[Project]])
async def list_projects(
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Fetch all projects for the user's organisation."""
    projects = await project_service.list_projects(user)
    return GenericResponse(data=projects)

@router.post("/", response_model=GenericResponse[Project], status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
    nonce: str = Depends(verify_nonce)
):
    """
    Fixed CR-13: Added project creation endpoint.
    Initializes a new project within the user's organisation.
    """
    project = await project_service.create_project(user, project_data)
    return GenericResponse(data=project, message="Project initialized successfully")

@router.get("/{project_id}", response_model=GenericResponse[Project])
async def get_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Fetch details for a single project."""
    project = await project_service.get_project(user, project_id)
    return GenericResponse(data=project)

@router.put("/{project_id}", response_model=GenericResponse[Project])
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

@router.get("/{project_id}/budgets", response_model=GenericResponse[List[Any]])
async def get_project_budgets(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Get all budgets for a project."""
    budgets = await project_service.get_project_budgets(user, project_id)
    return GenericResponse(data=budgets)

@router.post("/{project_id}/budgets", response_model=GenericResponse[Any])
async def create_or_update_project_budget(
    project_id: str,
    budget_data: ProjectBudgetCreate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
    nonce: str = Depends(verify_nonce)
):
    """Create or update a budget allocation for a project category."""
    # Fixed CR-12: Added typed request body with Pydantic validation
    result = await project_service.create_or_update_project_budget(user, project_id, budget_data.dict())
    return GenericResponse(data=result, message="Budget updated successfully")

@router.delete("/{project_id}", response_model=GenericResponse[dict])
async def delete_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Soft delete project and cascade to related entities."""
    await project_service.delete_project(user, project_id)
    return GenericResponse(data={"status": "deleted"}, message="Project and all related data soft-deleted successfully")
