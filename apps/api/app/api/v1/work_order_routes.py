from fastapi import APIRouter, Depends, Query, status, Body
from typing import Optional, List, Dict, Any

from app.core.dependencies import get_authenticated_user, get_work_order_service, verify_nonce
from app.services.work_order_service import WorkOrderService
from app.schemas.financial import WorkOrder, WorkOrderCreate, WorkOrderUpdate
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])

@router.get("/", response_model=GenericResponse[Dict[str, Any]])
async def list_work_orders(
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service)
):
    """List work orders with optional project filter."""
    result = await wo_service.list_work_orders(user, project_id, limit, cursor)
    return GenericResponse(data=result)

@router.post("/{project_id}", response_model=GenericResponse[WorkOrder], status_code=status.HTTP_201_CREATED)
async def create_work_order(
    project_id: str,
    wo_data: WorkOrderCreate,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
    nonce: str = Depends(verify_nonce)
):
    """Create a new work order for a project."""
    new_wo = await wo_service.create_work_order(user, project_id, wo_data)
    return GenericResponse(data=new_wo, message="Work order created successfully")

@router.patch("/{wo_id}", response_model=GenericResponse[WorkOrder])
async def update_work_order(
    wo_id: str,
    wo_data: WorkOrderUpdate, # Fixed CR-24: Using formal schema for optimistic locking support
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
    nonce: str = Depends(verify_nonce)
):
    """Update an existing work order."""
    # Fixed CR-24: Using .dict() with exclude_unset for clean partial updates
    result = await wo_service.update_work_order(wo_id, wo_data.dict(exclude_unset=True), user)
    return GenericResponse(data=result)
