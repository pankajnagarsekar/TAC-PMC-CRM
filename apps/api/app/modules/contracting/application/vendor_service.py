from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException
import logging

from ..infrastructure.repository import VendorRepository, WorkOrderRepository, LedgerRepository
from ..schemas.dto import Vendor, VendorCreate, VendorUpdate

logger = logging.getLogger(__name__)

class VendorService:
    """
    Sovereign Vendor Logic for Contracting Context.
    Enforces uniqueness constraints and organizational scoping.
    """
    def __init__(self, db, audit_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.vendor_repo = VendorRepository(db)
        self.wo_repo = WorkOrderRepository(db)
        self.ledger_repo = LedgerRepository(db)

    async def list_vendors(self, user: dict, active_only: bool = True) -> List[Dict[str, Any]]:
        query = {"organisation_id": user["organisation_id"]}
        if active_only: query["active_status"] = True
        return await self.vendor_repo.list(query)

    async def create_vendor(self, user: dict, vendor_data: VendorCreate) -> Dict[str, Any]:
        """Admin-initiated vendor creation with uniqueness check."""
        await self.permission_checker.check_admin_role(user)
        
        existing_name = await self.vendor_repo.get_by_name(vendor_data.name, user["organisation_id"])
        if existing_name:
            raise HTTPException(status_code=400, detail="VENDOR_ALREADY_EXISTS: Name must be unique within organisation.")

        vendor_dict = vendor_data.dict()
        vendor_dict["organisation_id"] = user["organisation_id"]
        vendor_dict["active_status"] = True
        
        new_vendor = await self.vendor_repo.create(vendor_dict)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="VENDOR_MANAGEMENT",
            entity_type="VENDOR", entity_id=new_vendor["id"],
            action_type="CREATE", user_id=user["user_id"], new_value=new_vendor
        )
        return new_vendor

    async def get_vendor(self, user: dict, vendor_id: str) -> Dict[str, Any]:
        vendor = await self.vendor_repo.get_by_id(vendor_id, organisation_id=user["organisation_id"])
        if not vendor: raise HTTPException(status_code=404, detail="Vendor not found")
        return vendor

    async def update_vendor(self, user: dict, vendor_id: str, vendor_update: VendorUpdate) -> Dict[str, Any]:
        """Vendor update with name uniqueness check."""
        existing = await self.vendor_repo.get_by_id(vendor_id, organisation_id=user["organisation_id"])
        if not existing: raise HTTPException(status_code=404, detail="Vendor not found")

        update_data = vendor_update.dict(exclude_unset=True)
        
        if "name" in update_data and update_data["name"] != existing["name"]:
            duplicate = await self.vendor_repo.get_by_name(update_data["name"], user["organisation_id"])
            if duplicate:
                raise HTTPException(status_code=400, detail="VENDOR_NAME_CONFLICT: Another vendor already uses this name.")

        updated_vendor = await self.vendor_repo.update(vendor_id, update_data, organisation_id=user["organisation_id"])

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="VENDOR_MANAGEMENT",
            entity_type="VENDOR", entity_id=vendor_id,
            action_type="UPDATE", user_id=user["user_id"],
            old_value=existing, new_value=updated_vendor
        )
        return updated_vendor

    async def delete_vendor(self, user: dict, vendor_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        
        # Hard check for associations
        has_wos = await self.wo_repo.find_one({"vendor_id": vendor_id})
        if has_wos:
            raise HTTPException(status_code=400, detail="DELETION_BLOCKED: Vendor has active work orders.")

        existing = await self.vendor_repo.get_by_id(vendor_id, organisation_id=user["organisation_id"])
        if not existing: raise HTTPException(status_code=404, detail="Vendor not found")

        await self.vendor_repo.update(vendor_id, {"active_status": False}, organisation_id=user["organisation_id"])

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="VENDOR_MANAGEMENT",
            entity_type="VENDOR", entity_id=vendor_id,
            action_type="SOFT_DELETE", user_id=user["user_id"],
            old_value=existing, new_value={"active_status": False}
        )
        return {"status": "success"}

    async def get_ledger(self, user: dict, vendor_id: str) -> List[Dict[str, Any]]:
        vendor = await self.vendor_repo.get_by_id(vendor_id, organisation_id=user["organisation_id"])
        if not vendor: raise HTTPException(status_code=404, detail="Vendor not found")

        return await self.ledger_repo.list({"vendor_id": vendor_id}, sort=[("created_at", -1)], limit=500)
