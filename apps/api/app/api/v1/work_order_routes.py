from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List, Dict, Any

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_work_order_service
from app.services.work_order_service import WorkOrderService
from app.schemas.financial import WorkOrder, WorkOrderCreate

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])

@router.get("/")
async def list_work_orders(
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service)
):
    """List work orders with optional project filter."""
    return await wo_service.list_work_orders(user, project_id, limit, cursor)

@router.post("/{project_id}", response_model=WorkOrder, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    project_id: str,
    wo_data: WorkOrderCreate,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service)
):
    """Create a new work order for a project."""
    return await wo_service.create_work_order(user, project_id, wo_data)
