from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from app.core.dependencies import get_authenticated_user, get_db
from app.modules.shared.domain.schemas import GenericResponse
from ..application.portfolio_service import PortfolioService

router = APIRouter()

async def get_portfolio_service(db = Depends(get_db)) -> PortfolioService:
    return PortfolioService(db)

@router.get("/summary", response_model=GenericResponse[Dict[str, Any]])
async def get_portfolio_summary(
    user: dict = Depends(get_authenticated_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """Aggregated financial and task KPIs across all projects."""
    data = await service.get_summary(user["organisation_id"])
    return GenericResponse(data=data)

@router.get("/resource-heatmap", response_model=GenericResponse[List[Dict[str, Any]]])
async def get_resource_heatmap(
    user: dict = Depends(get_authenticated_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """Task distribution and utilization heatmap across resources."""
    data = await service.get_resource_heatmap(user["organisation_id"])
    return GenericResponse(data=data)

@router.get("/milestones", response_model=GenericResponse[List[Dict[str, Any]]])
async def get_portfolio_milestones(
    user: dict = Depends(get_authenticated_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """Upcoming and recently completed milestones across all projects."""
    data = await service.get_milestones(user["organisation_id"])
    return GenericResponse(data=data)
