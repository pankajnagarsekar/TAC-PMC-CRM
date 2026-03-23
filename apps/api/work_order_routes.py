from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from core.database import get_db, db_manager
from core.utils import serialize_doc
import traceback
from auth import get_current_user
from models import WorkOrderCreate, WorkOrder, WorkOrderUpdate
from work_order_service import WorkOrderService
from permissions import PermissionChecker
from core.rate_limit import limiter
from fastapi import Request
from fastapi.responses import StreamingResponse
from core.pdf_service import pdf_generator

router = APIRouter(prefix="/api/work-orders", tags=["Work Orders"])
project_scoped_router = APIRouter(prefix="/api/projects", tags=["Work Orders"])


# Used strictly for organization-scoped global lists, e.g. "All WOs"
@router.get("", response_model=dict)
async def list_work_orders(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    cursor: Optional[str] = Query(None, description="ISO timestamp for cursor"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    query = {"organisation_id": user["organisation_id"]}
    if project_id:
        await checker.check_project_access(user, project_id)
        query["project_id"] = project_id

    if cursor:
        try:
            parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
            query["created_at"] = {"$lt": parsed_cursor}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format")

    wos = await db.work_orders.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)

    next_cursor = None
    if len(wos) == limit:
        last_wo = wos[-1]
        ts = last_wo.get("created_at")
        if isinstance(ts, datetime):
            next_cursor = ts.isoformat()

    from core.utils import serialize_doc
    return {
        "items": [serialize_doc(wo) for wo in wos],
        "next_cursor": next_cursor
    }


@project_scoped_router.get("/{project_id}/work-orders", response_model=dict)
async def list_work_orders_by_project(
    project_id: str,
    cursor: Optional[str] = Query(None, description="ISO timestamp for cursor"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Canonical project-scoped endpoint that mirrors /api/work-orders?project_id=...
    return await list_work_orders(
        project_id=project_id,
        cursor=cursor,
        limit=limit,
        db=db,
        current_user=current_user
    )


@router.post("/{project_id}", response_model=dict)
@limiter.limit("5/minute")
async def create_work_order(
    request: Request,
    project_id: str,
    wo_data: WorkOrderCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from server import audit_service, financial_service

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    await checker.check_project_access(user, project_id, require_write=True)

    # Lazy instantiate the service
    wo_service = WorkOrderService(db, audit_service, financial_service)

    # Pass down the structured Pydantic data
    wo_dict = wo_data.model_dump()

    # Execute the rigorous transaction
    result = await wo_service.create_work_order(wo_dict, user, project_id)
    return result


@project_scoped_router.post("/{project_id}/work-orders", response_model=dict)
@limiter.limit("5/minute")
async def create_work_order_by_project(
    request: Request,
    project_id: str,
    wo_data: WorkOrderCreate,
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from server import audit_service, financial_service

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    await checker.check_project_access(user, project_id, require_write=True)

    wo_service = WorkOrderService(db, audit_service, financial_service)
    wo_dict = wo_data.model_dump()
    if idempotency_key:
        wo_dict["idempotency_key"] = idempotency_key

    result = await wo_service.create_work_order(wo_dict, user, project_id)
    return result


@router.get("/{wo_id}", response_model=WorkOrder)
async def get_work_order(
    wo_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(wo_id):
        raise HTTPException(status_code=400, detail="Invalid WO ID format")

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    wo = await db.work_orders.find_one({
        "_id": ObjectId(wo_id),
        "organisation_id": user["organisation_id"]
    })
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    await checker.check_project_access(user, wo["project_id"])
    from core.utils import serialize_doc
    return serialize_doc(wo)


@router.patch("/{wo_id}/status")
@limiter.limit("10/minute")
async def update_work_order_status(
    request: Request,
    wo_id: str,
    status: str = Query(..., description="New status (Draft, Pending, Completed, Closed, Cancelled)"),
    expected_version: int = Query(..., description="The version of the document to update"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from server import audit_service

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    valid_statuses = ["Draft", "Pending", "Completed", "Closed", "Cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    if not ObjectId.is_valid(wo_id):
        raise HTTPException(status_code=400, detail="Invalid WO ID format")

    wo = await db.work_orders.find_one({
        "_id": ObjectId(wo_id),
        "organisation_id": user["organisation_id"]
    })
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    await checker.check_project_access(user, wo["project_id"], require_write=True)

    current_version = wo.get("version", 1)
    if current_version != expected_version:
        raise HTTPException(status_code=409, detail={
            "error": "concurrency_conflict",
            "message": "Record was modified in another session. Please refresh."
        })

    old_status = wo.get("status")

    # State Machine Rules (Tech Arch §6.1)
    # Allowed transitions:
    # - Draft → Pending
    # - Pending → Completed
    # - Completed → Closed
    # - Draft|Pending|Completed → Cancelled (only if no PCs exist)

    # Rule 1: Cannot change status from Closed
    if old_status == "Closed":
        raise HTTPException(status_code=400, detail="Cannot change status of a Closed Work Order")

    # Rule 2: Define valid next status based on current
    valid_transitions = {
        "Draft": ["Pending", "Cancelled"],
        "Pending": ["Completed", "Cancelled"],
        "Completed": ["Closed", "Cancelled"],
        "Cancelled": []
    }

    if status not in valid_transitions.get(old_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{old_status}' to '{status}'. Allowed: {valid_transitions.get(old_status, [])}"
        )

    # Rule 3: Cancellation requires no active PCs
    if status == "Cancelled":
        pcs = await db.payment_certificates.find_one({
            "work_order_id": wo_id,
            "status": {"$ne": "Cancelled"}
        })
        if pcs:
            raise HTTPException(status_code=400, detail="Cannot cancel Work Order with active Payment Certificates")

    await db.work_orders.update_one(
        {"_id": ObjectId(wo_id)},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}, "$inc": {"version": 1}}
    )

    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="WORK_ORDERS",
        entity_type="WORK_ORDER",
        entity_id=wo_id,
        action_type="UPDATE_STATUS",
        user_id=user["user_id"],
        project_id=wo.get("project_id"),
        old_value={"status": old_status},
        new_value={"status": status}
    )

    return {"status": "success"}


@router.put("/{wo_id}", response_model=dict)
@limiter.limit("5/minute")
async def update_work_order(
    request: Request,
    wo_id: str,
    wo_data: WorkOrderUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from server import audit_service, financial_service

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    wo_service = WorkOrderService(db, audit_service, financial_service)
    result = await wo_service.update_work_order(wo_id, wo_data.model_dump(exclude_none=True), user)
    return result


@router.delete("/{wo_id}")
async def delete_work_order(
    wo_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from server import audit_service, financial_service

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    wo_service = WorkOrderService(db, audit_service, financial_service)
    result = await wo_service.delete_work_order(wo_id, user)
    return result


@router.get("/{wo_id}/export")
async def export_work_order_pdf(
    wo_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        if not ObjectId.is_valid(wo_id):
            raise HTTPException(status_code=400, detail="Invalid WO ID format")

        checker = PermissionChecker(db)
        user = await checker.get_authenticated_user(current_user)

        wo = await db.work_orders.find_one({
            "_id": ObjectId(wo_id),
            "organisation_id": user["organisation_id"]
        })
        if not wo:
            raise HTTPException(status_code=404, detail="Work Order not found")

        await checker.check_project_access(user, wo["project_id"])

        # Fetch settings for logo and company info
        settings = await db.global_settings.find_one({"organisation_id": user["organisation_id"]})
        if not settings:
            settings = {}

        # Fetch vendor info
        vendor_id = wo.get("vendor_id")
        vendor = None
        if vendor_id and ObjectId.is_valid(vendor_id):
            vendor = await db.vendors.find_one({"_id": ObjectId(vendor_id)})

        pdf_bytes = pdf_generator.generate_work_order_pdf(
            serialize_doc(wo),
            serialize_doc(settings),
            serialize_doc(vendor) if vendor else None
        )

        filename = pdf_generator.get_wo_filename(wo.get("wo_ref", wo_id))

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")
