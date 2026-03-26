from fastapi import APIRouter, Depends, Body
from typing import List, Any
from app.core.dependencies import get_authenticated_user
from app.core.deps import get_project_service
from app.services.project_service import ProjectService
from app.schemas.project import Project, ProjectUpdate
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
    project_service: ProjectService = Depends(get_project_service)
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
    budget_data: dict = Body(...),
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Create or update a budget allocation for a project category."""
    result = await project_service.create_or_update_project_budget(user, project_id, budget_data)
    return GenericResponse(data=result, message="Budget updated successfully")
