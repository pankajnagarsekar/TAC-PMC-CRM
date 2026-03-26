from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
import logging

from app.schemas.settings_ai import GlobalSettings, CodeMaster, CodeMasterCreate, CodeMasterUpdate
from app.repositories.settings_repo import SettingsRepository, CodeMasterRepository
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)

class SettingsService:
    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker
        self.settings_repo = SettingsRepository(db)
        self.code_master_repo = CodeMasterRepository(db)

    async def get_settings(self, user: dict) -> Dict[str, Any]:
        settings = await self.settings_repo.find_one({"organisation_id": user["organisation_id"]})
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
        return settings

    async def update_settings(self, user: dict, settings_data: dict) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        settings_data.pop("id", None)
        settings_data.pop("_id", None)
        settings_data["organisation_id"] = user["organisation_id"]
        
        await self.settings_repo.update_one(
            {"organisation_id": user["organisation_id"]},
            {"$set": settings_data}
        )
        return {"status": "success"}

    async def list_categories(self, user: dict) -> List[Dict[str, Any]]:
        return await self.code_master_repo.list({
            "organisation_id": user["organisation_id"],
            "active_status": True
        })

    async def create_category(self, user: dict, category_data: CodeMasterCreate) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        doc = category_data.dict()
        doc["organisation_id"] = user["organisation_id"]
        doc["active_status"] = True
        
        result = await self.code_master_repo.create(doc)
        return {"id": result["id"], "status": "created"}
