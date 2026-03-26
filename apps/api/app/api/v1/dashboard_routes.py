from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.core.dependencies import get_authenticated_user, PermissionChecker
from app.core.deps import get_dashboard_service, get_permission_checker
from app.services.dashboard_service import DashboardService
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/projects", tags=["Dashboard Statistics"])

@router.get("/{project_id}/dashboard-stats", response_model=GenericResponse[Dict[str, Any]])
async def get_project_dashboard_stats(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    checker: PermissionChecker = Depends(get_permission_checker)
):
    """
    Returns aggregated statistics for the project dashboard.
    """
    await checker.check_project_access(user, project_id)
    
    stats = await dashboard_service.get_project_dashboard_stats(project_id, user["organisation_id"])
    return GenericResponse(data=stats)
