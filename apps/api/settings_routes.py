import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime

from core.database import get_db
from auth import get_current_user
from permissions import PermissionChecker
from models import GlobalSettings, ClientPermissions, CodeMaster, CodeMasterCreate, CodeMasterUpdate
from core.utils import serialize_doc, serialize_list

# Using prefix /api to accommodate both /settings and /codes
settings_router = APIRouter(prefix="/api", tags=["Settings & Categories"])

@settings_router.get("/settings", response_model=GlobalSettings)
async def get_global_settings(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get global system settings and company profile"""
    checker = PermissionChecker(db)
    try:
        user = await checker.get_authenticated_user(current_user)
        settings = await db.global_settings.find_one({"organisation_id": user["organisation_id"]})
        if not settings:
            # Return default structure if not initialized
            return {
                "organisation_id": user["organisation_id"],
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
        
        # Ensure robust serialization for Decimal128 and ObjectId
        return serialize_doc(settings)
    except HTTPException:
        # Re-raise HTTP exceptions (from get_authenticated_user)
        raise
    except Exception as e:
        logging.error(f"Error in get_global_settings: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )

@settings_router.put("/settings")
async def update_global_settings(
    settings_data: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update global system settings (Admin only)"""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_admin_role(user)
    
    # Remove _id if present to avoid immutable field error
    settings_data.pop("_id", None)
    settings_data["updated_at"] = datetime.utcnow()
    settings_data["organisation_id"] = user["organisation_id"]
    
    await db.global_settings.update_one(
        {"organisation_id": user["organisation_id"]},
        {"$set": settings_data},
        upsert=True
    )
    return {"status": "success", "message": "Settings updated"}

@settings_router.get("/codes", response_model=List[CodeMaster])
async def list_categories(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all budget categories for the organisation"""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    
    categories = await db.code_master.find({
        "organisation_id": user["organisation_id"],
        "active_status": True
    }).to_list(length=500)
    
    return serialize_list(categories)

@settings_router.post("/codes", status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CodeMasterCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new budget category"""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_admin_role(user)
    
    doc = category_data.dict()
    doc["organisation_id"] = user["organisation_id"]
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    doc["active_status"] = True
    
    result = await db.code_master.insert_one(doc)
    return {"id": str(result.inserted_id), "status": "created"}

@settings_router.put("/codes/{code_id}")
async def update_category(
    code_id: str,
    category_data: CodeMasterUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a budget category"""
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_admin_role(user)
    
    update_data = {k: v for k, v in category_data.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.code_master.update_one(
        {"_id": ObjectId(code_id), "organisation_id": user["organisation_id"]},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
        
    return {"status": "updated"}

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
