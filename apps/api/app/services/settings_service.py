from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.schemas.settings_ai import GlobalSettings, CodeMaster, CodeMasterCreate, CodeMasterUpdate
from app.core.utils import serialize_doc

class SettingsService:
    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker

    async def get_settings(self, user: dict) -> Dict[str, Any]:
        settings = await self.db.global_settings.find_one({"organisation_id": user["organisation_id"]})
        if not settings:
            return {
                "organisation_id": user["organisation_id"],
                "cgst_percentage": 9.0,
                "sgst_percentage": 9.0,
                "retention_percentage": 5.0,
                "currency": "INR",
                "currency_symbol": "₹",
                "company_profile": {"name": "TAC PMC", "address": "", "registration_no": "", "contact_email": ""}
            }
        return serialize_doc(settings)

    async def update_settings(self, user: dict, settings_data: dict) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        settings_data.pop("_id", None)
        settings_data["updated_at"] = datetime.now(timezone.utc)
        settings_data["organisation_id"] = user["organisation_id"]
        
        await self.db.global_settings.update_one(
            {"organisation_id": user["organisation_id"]},
            {"$set": settings_data},
            upsert=True
        )
        return {"status": "success"}

    async def list_categories(self, user: dict) -> List[Dict[str, Any]]:
        categories = await self.db.code_master.find({
            "organisation_id": user["organisation_id"],
            "active_status": True
        }).to_list(length=500)
        return [serialize_doc(c) for c in categories]

    async def create_category(self, user: dict, category_data: CodeMasterCreate) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        doc = category_data.dict()
        doc["organisation_id"] = user["organisation_id"]
        doc["created_at"] = datetime.now(timezone.utc)
        doc["updated_at"] = datetime.now(timezone.utc)
        doc["active_status"] = True
        
        result = await self.db.code_master.insert_one(doc)
        return {"id": str(result.inserted_id), "status": "created"}
