from fastapi import APIRouter, Depends, Body
from typing import List

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_project_service
from app.services.project_service import ProjectService
from app.schemas.project import Project, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/", response_model=List[Project])
async def list_projects(
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Fetch all projects for the user's organisation."""
    return await project_service.list_projects(user)

@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Fetch details for a single project."""
    return await project_service.get_project(user, project_id)

@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Update project details."""
    return await project_service.update_project(user, project_id, project_data)

@router.get("/{project_id}/budgets")
async def get_project_budgets(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Get all budgets for a project."""
    return await project_service.get_project_budgets(user, project_id)

@router.post("/{project_id}/budgets")
async def create_or_update_project_budget(
    project_id: str,
    budget_data: dict = Body(...),
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Create or update a budget allocation for a project category."""
    return await project_service.create_or_update_project_budget(user, project_id, budget_data)
