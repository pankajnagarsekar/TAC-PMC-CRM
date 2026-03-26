from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
import logging

from app.schemas.settings_ai import GlobalSettings
from app.repositories.settings_repo import SettingsRepository
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)

class SettingsService:
    """
    Sovereign Settings Controller (Point 1).
    Manages organizational configuration and profile data.
    """
    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker
        self.settings_repo = SettingsRepository(db)

    async def get_settings(self, user: dict) -> Dict[str, Any]:
        """Fetch settings for organisation with default fallback."""
        settings = await self.settings_repo.find_one({"organisation_id": user["organisation_id"]})
        if not settings:
            return {
                "organisation_id": user["organisation_id"],
                "cgst_percentage": 9.0,
                "sgst_percentage": 9.0,
                "retention_percentage": 5.0,
                "currency": "INR",
                "currency_symbol": "₹",
                "company_profile": {
                    "name": "TAC PMC", 
                    "address": "Default Address", 
                    "registration_no": "", 
                    "contact_email": ""
                }
            }
        return settings

    async def update_settings(self, user: dict, settings_data: dict) -> Dict[str, Any]:
        """Atomic update of global settings."""
        await self.permission_checker.check_admin_role(user)
        
        # Sanitize
        payload = {k: v for k, v in settings_data.items() if k not in ("id", "_id", "organisation_id")}
        
        existing = await self.settings_repo.find_one({"organisation_id": user["organisation_id"]})
        if existing:
            await self.settings_repo.update(existing["id"], payload)
        else:
            payload["organisation_id"] = user["organisation_id"]
            await self.settings_repo.create(payload)
            
        return {"status": "success"}

    # NOTE: list_categories and create_category removed here (Fixed CR-08/28).
    # Those operations are now handled by MasterDataService.
