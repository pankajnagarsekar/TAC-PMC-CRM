from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.schemas.vendor import Vendor, VendorCreate, VendorUpdate
from app.core.utils import serialize_doc

class VendorService:
    def __init__(self, db, audit_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker

    async def list_vendors(self, user: dict, active_only: bool = True) -> List[Dict[str, Any]]:
        query = {"organisation_id": user["organisation_id"]}
        if active_only:
            query["active_status"] = True
        vendors = await self.db.vendors.find(query).to_list(length=100)
        return [serialize_doc(v) for v in vendors]

    async def create_vendor(self, user: dict, vendor_data: VendorCreate) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        
        vendor_dict = vendor_data.dict()
        vendor_dict["organisation_id"] = user["organisation_id"]
        vendor_dict["active_status"] = True
        vendor_dict["created_at"] = datetime.now(timezone.utc)
        vendor_dict["updated_at"] = datetime.now(timezone.utc)

        result = await self.db.vendors.insert_one(vendor_dict)
        vendor_id = str(result.inserted_id)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="VENDOR_MANAGEMENT",
            entity_type="VENDOR",
            entity_id=vendor_id,
            action_type="CREATE",
            user_id=user["user_id"],
            new_value=serialize_doc(vendor_dict)
        )
        vendor_dict["_id"] = result.inserted_id
        return serialize_doc(vendor_dict)

    async def get_vendor(self, user: dict, vendor_id: str) -> Dict[str, Any]:
        vendor = await self.db.vendors.find_one({"_id": ObjectId(vendor_id), "organisation_id": user["organisation_id"]})
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return serialize_doc(vendor)

    async def update_vendor(self, user: dict, vendor_id: str, vendor_update: VendorUpdate) -> Dict[str, Any]:
        existing = await self.db.vendors.find_one({"_id": ObjectId(vendor_id), "organisation_id": user["organisation_id"]})
        if not existing:
            raise HTTPException(status_code=404, detail="Vendor not found")

        update_data = vendor_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)

        result = await self.db.vendors.find_one_and_update(
            {"_id": ObjectId(vendor_id)},
            {"$set": update_data},
            return_document=True
        )

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="VENDOR_MANAGEMENT",
            entity_type="VENDOR",
            entity_id=vendor_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            old_value=serialize_doc(existing),
            new_value=serialize_doc(result)
        )
        return serialize_doc(result)

    async def delete_vendor(self, user: dict, vendor_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        
        has_wos = await self.db.work_orders.find_one({"vendor_id": vendor_id})
        if has_wos:
            raise HTTPException(status_code=400, detail="Cannot delete vendor with associated work orders")

        existing = await self.db.vendors.find_one({"_id": ObjectId(vendor_id), "organisation_id": user["organisation_id"]})
        if not existing:
            raise HTTPException(status_code=404, detail="Vendor not found")

        await self.db.vendors.update_one(
            {"_id": ObjectId(vendor_id)},
            {"$set": {"active_status": False, "updated_at": datetime.now(timezone.utc)}}
        )

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="VENDOR_MANAGEMENT",
            entity_type="VENDOR",
            entity_id=vendor_id,
            action_type="SOFT_DELETE",
            user_id=user["user_id"],
            old_value=serialize_doc(existing),
            new_value={"active_status": False}
        )
        return {"status": "success"}

    async def get_ledger(self, user: dict, vendor_id: str) -> List[Dict[str, Any]]:
        vendor = await self.db.vendors.find_one({"_id": ObjectId(vendor_id), "organisation_id": user["organisation_id"]})
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        entries = await self.db.vendor_ledger.find({"vendor_id": vendor_id}).sort("created_at", -1).to_list(length=500)
        return [serialize_doc(e) for e in entries]
