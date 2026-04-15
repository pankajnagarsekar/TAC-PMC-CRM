from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import (
    get_authenticated_user,
    get_vendor_service,
    get_work_order_service,
    get_contract_service,
    get_db,
    verify_nonce,
)
from app.modules.shared.domain.schemas import GenericResponse

from ..application.vendor_service import VendorService
from ..application.work_order_service import WorkOrderService
from ..application.contract_service import ContractService
from ..schemas.dto import (
    Vendor,
    VendorCreate,
    VendorUpdate,
    WorkOrder,
    WorkOrderCreate,
    WorkOrderUpdate,
    Contract,
    ContractCreate,
    ContractUpdate,
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
    limit: int = Query(50, ge=1, le=1000),
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
    result = await wo_service.update_work_order(user, wo_id, wo_data)
    return GenericResponse(data=result)


@router.get(
    "/work-orders/{wo_id}",
    response_model=GenericResponse[WorkOrder],
    tags=["Work Orders"],
)
async def get_work_order(
    wo_id: str,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
):
    """Get a specific work order by ID."""
    wo = await wo_service.get_work_order(user, wo_id)
    return GenericResponse(data=wo)


@router.get(
    "/work-orders/{wo_id}/export/excel",
    tags=["Work Orders"],
)
async def export_work_order_excel(
    wo_id: str,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
):
    from fastapi.responses import StreamingResponse
    import io
    from app.core.template_export_service import TemplateExportService
    from app.modules.identity.application.settings_service import SettingsService
    from app.core.dependencies import get_settings_service, get_vendor_service, get_db

    wo = await wo_service.get_work_order(user, wo_id)
    
    excel_bytes = TemplateExportService.export_work_order_exact(wo, fmt="excel")
    
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=WO_{wo_id}.xlsx"}
    )


@router.get(
    "/work-orders/{wo_id}/export/pdf",
    tags=["Work Orders"],
)
async def export_work_order_pdf(
    wo_id: str,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    from fastapi.responses import StreamingResponse
    import io
    from app.core.template_export_service import TemplateExportService
    from app.core.dependencies import get_db, get_settings_service

    wo = await wo_service.get_work_order(user, wo_id)
    
    # Bridge data for exact export
    vendor = await vendor_service.get_vendor(user, wo.get("vendor_id"))
    wo["vendor"] = vendor
    
    # Fetch Category (CodeMaster) info
    from app.modules.financial.application.master_data_service import MasterDataService
    db = await get_db()
    md_service = MasterDataService(db, None, None) # Minimal instantiation for code fetch
    category = await md_service.get_code_by_id(user, wo.get("category_id"))
    wo["category"] = category
    wo["code"] = category.get("code", "") if category else ""
    
    # Set default dates for template
    if "wo_date" not in wo:
        wo["wo_date"] = wo.get("created_at")
    
    # Get Company/Organisation details
    settings = await db.organisation_settings.find_one({"organisation_id": user["organisation_id"]})
    if settings and "company_profile" in settings:
        wo["company"] = settings["company_profile"]
    else:
        # Try finding the organisation name directly as a fallback
        from bson import ObjectId
        query = {"_id": ObjectId(user["organisation_id"])} if ObjectId.is_valid(user["organisation_id"]) else {"organisation_id": user["organisation_id"]}
        org = await db.organisations.find_one(query)
        wo["company"] = {"name": org.get("name") if org else "Third Angle Concepts (PMC)", "address": "Site Address"}
    
    pdf_bytes = TemplateExportService.export_work_order_exact(wo, fmt="pdf")
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=WO_{wo_id}.pdf"}
    )


@router.post("/work-orders/{wo_id}/submit", response_model=GenericResponse[WorkOrder], tags=["Work Orders"])
async def submit_work_order(
    wo_id: str,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
):
    """Transition WO from Draft to Pending."""
    result = await wo_service.submit_work_order(user, wo_id)
    return GenericResponse(data=result, message="Work order submitted for approval")


@router.post("/work-orders/{wo_id}/approve", response_model=GenericResponse[WorkOrder], tags=["Work Orders"])
async def approve_work_order(
    wo_id: str,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
):
    """Approve a pending WO (Admin only)."""
    from app.core.dependencies import get_permission_checker
    db = await get_db() if "get_db" in globals() else None # Fallback
    # Use injected db or similar. Better: use permission checker dependency if available in scope.
    # Actually get_authenticated_user already validated.
    # But C3 says Admin only.
    from app.core.permissions import PermissionChecker
    # We can use the one from dependencies or instantiate a new one with db
    # For now, simplistic check as per service
    result = await wo_service.approve_work_order(user, wo_id)
    return GenericResponse(data=result, message="Work order approved")


@router.post("/work-orders/{wo_id}/cancel", response_model=GenericResponse[WorkOrder], tags=["Work Orders"])
async def cancel_work_order(
    wo_id: str,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
):
    """Cancel a work order."""
    result = await wo_service.cancel_work_order(user, wo_id)
    return GenericResponse(data=result, message="Work order cancelled")


@router.delete("/work-orders/{wo_id}", response_model=GenericResponse[dict], tags=["Work Orders"])
async def delete_work_order(
    wo_id: str,
    user: dict = Depends(get_authenticated_user),
    wo_service: WorkOrderService = Depends(get_work_order_service),
):
    """Delete a draft work order (Track I3)."""
    success = await wo_service.delete_work_order(user, wo_id)
    if success:
        return GenericResponse(data={"deleted": True}, message="Work order deleted successfully")
    return GenericResponse(data={"deleted": False}, message="Failed to delete work order")


# --- CONTRACT ENDPOINTS ---

@router.post("/work-orders/{wo_id}/contract", response_model=GenericResponse[Contract], status_code=status.HTTP_201_CREATED, tags=["Contracts"])
async def create_contract(
    wo_id: str,
    contract_data: ContractCreate,
    user: dict = Depends(get_authenticated_user),
    contract_service: ContractService = Depends(get_contract_service),
):
    """Create a contract for an approved work order."""
    contract = await contract_service.create_contract(user, wo_id, contract_data)
    return GenericResponse(data=contract, message="Contract created successfully")


@router.get("/work-orders/{wo_id}/contract", response_model=GenericResponse[Contract], tags=["Contracts"])
async def get_contract_by_wo(
    wo_id: str,
    user: dict = Depends(get_authenticated_user),
    contract_service: ContractService = Depends(get_contract_service),
):
    """Get the contract associated with a work order."""
    contract = await contract_service.get_contract_by_wo(user, wo_id)
    return GenericResponse(data=contract)


@router.patch("/contracts/{contract_id}", response_model=GenericResponse[Contract], tags=["Contracts"])
async def update_contract(
    contract_id: str,
    contract_data: ContractUpdate,
    user: dict = Depends(get_authenticated_user),
    contract_service: ContractService = Depends(get_contract_service),
):
    """Update contract details."""
    updated = await contract_service.update_contract(user, contract_id, contract_data)
    return GenericResponse(data=updated, message="Contract updated successfully")

