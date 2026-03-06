from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime

from core.database import get_db
from auth import get_current_user
from permissions import PermissionChecker

settings_router = APIRouter(prefix="/api/settings", tags=["Settings"])

@settings_router.get("")
async def get_global_settings(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get global system settings and company profile"""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    settings = await db.global_settings.find_one({"organisation_id": user["organisation_id"]})
    if not settings:
        # Return default structure if not initialized
        return {
            "cgst_percentage": 9.0,
            "sgst_percentage": 9.0,
            "retention_percentage": 5.0,
            "currency": "INR",
            "currency_symbol": "₹",
            "company_profile": {
                "name": "TAC PMC",
                "address": "",
                "registration_no": "",
                "contact_email": ""
            }
        }
    
    # Remove MongoDB internal fields
    if "_id" in settings:
        settings["_id"] = str(settings["_id"])
    return settings

@settings_router.put("")
async def update_global_settings(
    settings_data: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update global system settings (Admin only)"""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_admin_role(user)
    
    settings_data["updated_at"] = datetime.utcnow()
    settings_data["organisation_id"] = user["organisation_id"]
    
    await db.global_settings.update_one(
        {"organisation_id": user["organisation_id"]},
        {"$set": settings_data},
        upsert=True
    )
    return {"status": "success", "message": "Settings updated"}

@settings_router.get("/client-permissions")
async def get_client_permissions(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get standalone client permission board"""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    settings = await db.global_settings.find_one({"organisation_id": user["organisation_id"]}, {"client_permissions": 1})
    if not settings or "client_permissions" not in settings:
        return {
            "can_view_dpr": True,
            "can_view_financials": False,
            "can_view_reports": True
        }
    return settings["client_permissions"]

@settings_router.patch("/client-permissions")
async def update_client_permissions(
    permissions: Dict[str, bool],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update client permission board (Admin only)"""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_admin_role(user)
    
    await db.global_settings.update_one(
        {"organisation_id": user["organisation_id"]},
        {"$set": {"client_permissions": permissions}},
        upsert=True
    )
    return {"status": "success", "message": "Permissions updated"}
