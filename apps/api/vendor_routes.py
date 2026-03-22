from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.database import get_db
from auth import get_current_user
from models import Vendor, VendorCreate, VendorUpdate, UserResponse, AuditLog
from audit_service import AuditService
from permissions import PermissionChecker

router = APIRouter(prefix="/api/vendors", tags=["Vendors"])


def serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_doc(item) if isinstance(item, dict) else str(item)
                if isinstance(item, ObjectId) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


@router.get("", response_model=List[Vendor])
async def list_vendors(
    active_only: bool = True,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    query = {"organisation_id": user["organisation_id"]}
    if active_only:
        query["active_status"] = True
    vendors = await db.vendors.find(query).to_list(length=100)
    return [serialize_doc(v) for v in vendors]


@router.post("", response_model=Vendor)
async def create_vendor(
    vendor_data: VendorCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new vendor. Admin only."""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)
    await checker.check_admin_role(user)

    vendor_dict = vendor_data.model_dump()
    vendor_dict["organisation_id"] = user["organisation_id"]
    vendor_dict["active_status"] = True
    vendor_dict["created_at"] = datetime.now(timezone.utc)
    vendor_dict["updated_at"] = datetime.now(timezone.utc)

    result = await db.vendors.insert_one(vendor_dict)
    vendor_dict["_id"] = result.inserted_id

    # Audit log with FULL JSON snapshot
    audit_service = AuditService(db)
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="VENDOR_MANAGEMENT",
        entity_type="VENDOR",
        entity_id=str(result.inserted_id),
        action_type="CREATE",
        user_id=user["user_id"],
        new_value=serialize_doc(vendor_dict)  # FULL JSON snapshot per spec 6.1.2
    )

    return serialize_doc(vendor_dict)


@router.get("/{vendor_id}", response_model=Vendor)
async def get_vendor(
    vendor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a single vendor by ID."""
    if not ObjectId.is_valid(vendor_id):
        raise HTTPException(status_code=400, detail="Invalid vendor ID")

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    vendor = await db.vendors.find_one({
        "_id": ObjectId(vendor_id),
        "organisation_id": user["organisation_id"]
    })
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return serialize_doc(vendor)


@router.put("/{vendor_id}", response_model=Vendor)
async def update_vendor(
    vendor_id: str,
    vendor_update: VendorUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a vendor."""
    if not ObjectId.is_valid(vendor_id):
        raise HTTPException(status_code=400, detail="Invalid vendor ID")

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    # Get current state for audit
    existing = await db.vendors.find_one({
        "_id": ObjectId(vendor_id),
        "organisation_id": user["organisation_id"]
    })
    if not existing:
        raise HTTPException(status_code=404, detail="Vendor not found")

    update_data = vendor_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc)

    result = await db.vendors.find_one_and_update(
        {"_id": ObjectId(vendor_id), "organisation_id": user["organisation_id"]},
        {"$set": update_data},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Audit log with FULL JSON snapshots
    audit_service = AuditService(db)
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="VENDOR_MANAGEMENT",
        entity_type="VENDOR",
        entity_id=vendor_id,
        action_type="UPDATE",
        user_id=user["user_id"],
        old_value=serialize_doc(existing),  # FULL JSON snapshot per spec 6.1.2
        new_value=serialize_doc(result)  # FULL JSON snapshot per spec 6.1.2
    )

    return serialize_doc(result)


@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Soft delete a vendor (set active_status=False). Admin only."""
    if not ObjectId.is_valid(vendor_id):
        raise HTTPException(status_code=400, detail="Invalid vendor ID")

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)
    await checker.check_admin_role(user)

    # Get current state for audit BEFORE deletion
    existing = await db.vendors.find_one({
        "_id": ObjectId(vendor_id),
        "organisation_id": user["organisation_id"]
    })
    if not existing:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Check if vendor has ANY work orders
    has_wos = await db.work_orders.find_one({"vendor_id": vendor_id})
    if has_wos:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete vendor with associated work orders"
        )

    result = await db.vendors.update_one(
        {"_id": ObjectId(vendor_id), "organisation_id": user["organisation_id"]},
        {"$set": {"active_status": False, "updated_at": datetime.now(timezone.utc)}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Audit log for deletion with FULL JSON snapshot
    audit_service = AuditService(db)
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="VENDOR_MANAGEMENT",
        entity_type="VENDOR",
        entity_id=vendor_id,
        action_type="SOFT_DELETE",
        user_id=user["user_id"],
        old_value=serialize_doc(existing),  # FULL JSON snapshot per spec 6.1.2
        new_value={"active_status": False, "deleted_at": datetime.now(timezone.utc).isoformat()}
    )

    return {"status": "success", "message": "Vendor deleted"}


@router.get("/{vendor_id}/ledger", response_model=List[dict])
async def get_vendor_ledger(
    vendor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get the complete ledger for a specific vendor across all projects."""
    if not ObjectId.is_valid(vendor_id):
        raise HTTPException(status_code=400, detail="Invalid vendor ID")

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Verify vendor exists in this org
    vendor = await db.vendors.find_one({
        "_id": ObjectId(vendor_id),
        "organisation_id": user["organisation_id"]
    })
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    entries = await db.vendor_ledger.find({
        "vendor_id": vendor_id
    }).sort("created_at", -1).to_list(length=500)

    return [serialize_doc(e) for e in entries]
