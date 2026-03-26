from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
import logging

from app.repositories.user_repo import UserRepository
from app.schemas.user import User, UserCreateAdmin
from app.services.auth_service import AuthService
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db, audit_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.user_repo = UserRepository(db)

    async def list_users(self, organisation_id: str) -> List[Dict[str, Any]]:
        users = await self.db.users.find({"organisation_id": organisation_id}).to_list(length=100)
        return [serialize_doc(u) for u in users]

    async def create_user_admin(self, user, user_data: UserCreateAdmin) -> Dict[str, Any]:
        """Business logic for admin-initiated user creation"""
        await self.permission_checker.check_admin_role(user)

        # Check if email exists
        existing = await self.user_repo.get_by_email(user_data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_dict = user_data.dict()
        user_dict["hashed_password"] = AuthService.hash_password(user_dict.pop("password"))
        user_dict["organisation_id"] = user["organisation_id"]
        user_dict["active_status"] = True
        user_dict["created_at"] = datetime.now(timezone.utc)
        user_dict["updated_at"] = datetime.now(timezone.utc)

        result = await self.db.users.insert_one(user_dict)
        user_id = str(result.inserted_id)

        # Audit log
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="USER_MANAGEMENT",
            entity_type="USER",
            entity_id=user_id,
            action_type="CREATE",
            user_id=user["user_id"],
            new_value={"email": user_data.email, "role": user_data.role}
        )

        user_dict["_id"] = result.inserted_id
        return serialize_doc(user_dict)

    async def deactivate_user(self, user, target_user_id: str) -> Dict[str, Any]:
        """Business logic for deactivating a user"""
        await self.permission_checker.check_admin_role(user)

        if target_user_id == user["user_id"]:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

        result = await self.db.users.find_one_and_update(
            {"_id": ObjectId(target_user_id), "organisation_id": user["organisation_id"]},
            {"$set": {"active_status": False, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        # Audit log
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="USER_MANAGEMENT",
            entity_type="USER",
            entity_id=target_user_id,
            action_type="DEACTIVATE",
            user_id=user["user_id"]
        )

        return {"message": "User deactivated successfully"}
