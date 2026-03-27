from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from app.core.dependencies import PermissionChecker, get_authenticated_user, get_dashboard_service, get_permission_checker
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

@router.get("/{project_id}/financials", response_model=GenericResponse[List[Any]])
async def get_project_financials(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    checker: PermissionChecker = Depends(get_permission_checker)
):
    await checker.check_project_access(user, project_id)
    financials = await dashboard_service.get_financials(project_id)
    return GenericResponse(data=financials)

@router.get("/{project_id}/vendor-payables", response_model=GenericResponse[List[Any]])
async def get_project_vendor_payables(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    checker: PermissionChecker = Depends(get_permission_checker)
):
    await checker.check_project_access(user, project_id)
    payables = await dashboard_service.get_vendor_payables(project_id)
    return GenericResponse(data=payables)

