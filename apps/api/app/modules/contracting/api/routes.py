from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import (
    get_authenticated_user,
    get_vendor_service,
    get_work_order_service,
    verify_nonce,
)
from app.modules.shared.domain.schemas import GenericResponse

from ..application.vendor_service import VendorService
from ..application.work_order_service import WorkOrderService
from ..schemas.dto import (
    Vendor,
    VendorCreate,
    VendorUpdate,
    WorkOrder,
    WorkOrderCreate,
    WorkOrderUpdate,
)

# Create one router for the Contracting Context
router = APIRouter()

# --- VENDOR ENDPOINTS ---


@router.get("/vendors/", response_model=GenericResponse[List[Vendor]], tags=["Vendors"])
async def list_vendors(
    active_only: bool = Query(True),
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    vendors = await vendor_service.list_vendors(user, active_only)
    return GenericResponse(data=vendors)


@router.post(
    "/vendors/",
    response_model=GenericResponse[Vendor],
    status_code=status.HTTP_201_CREATED,
    tags=["Vendors"],
)
async def create_vendor(
    vendor_data: VendorCreate,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    vendor = await vendor_service.create_vendor(user, vendor_data)
    return GenericResponse(data=vendor, message="Vendor created successfully")


@router.get(
    "/vendors/{vendor_id}", response_model=GenericResponse[Vendor], tags=["Vendors"]
)
async def get_vendor(
    vendor_id: str,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    vendor = await vendor_service.get_vendor(user, vendor_id)
    return GenericResponse(data=vendor)


@router.put(
    "/vendors/{vendor_id}", response_model=GenericResponse[Vendor], tags=["Vendors"]
)
async def update_vendor(
    vendor_id: str,
    vendor_update: VendorUpdate,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    vendor = await vendor_service.update_vendor(user, vendor_id, vendor_update)
    return GenericResponse(data=vendor, message="Vendor updated successfully")


@router.delete(
    "/vendors/{vendor_id}", response_model=GenericResponse[dict], tags=["Vendors"]
)
async def delete_vendor(
    vendor_id: str,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    result = await vendor_service.delete_vendor(user, vendor_id)
    return GenericResponse(data=result, message="Vendor deleted successfully")


@router.get(
    "/vendors/{vendor_id}/ledger",
    response_model=GenericResponse[List[Dict[str, Any]]],
    tags=["Vendors"],
)
async def get_vendor_ledger(
    vendor_id: str,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    entries = await vendor_service.get_ledger(user, vendor_id)
    return GenericResponse(data=entries)


# --- WORK ORDER ENDPOINTS ---


@router.get(
    "/work-orders/",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Work Orders"],
)
async def list_work_orders(
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
):
    """List work orders with optional project filter."""
    result = await wo_service.list_work_orders(user, project_id, limit, cursor)
    return GenericResponse(data=result)


@router.post(
    "/work-orders/{project_id}",
    response_model=GenericResponse[WorkOrder],
    status_code=status.HTTP_201_CREATED,
    tags=["Work Orders"],
)
async def create_work_order(
    project_id: str,
    wo_data: WorkOrderCreate,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
    nonce: str = Depends(verify_nonce),
):
    """Create a new work order for a project."""
    new_wo = await wo_service.create_work_order(user, project_id, wo_data)
    return GenericResponse(data=new_wo, message="Work order created successfully")


@router.patch(
    "/work-orders/{wo_id}",
    response_model=GenericResponse[WorkOrder],
    tags=["Work Orders"],
)
async def update_work_order(
    wo_id: str,
    wo_data: WorkOrderUpdate,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
    nonce: str = Depends(verify_nonce),
):
    """Update an existing work order."""
    # Fixed argument order bug from legacy routes
    result = await wo_service.update_work_order(user, wo_id, wo_data)
    return GenericResponse(data=result)
