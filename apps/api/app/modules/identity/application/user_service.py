import logging
from typing import Any, Dict, List

from ..domain.models import User as UserModel
from ..infrastructure.repository import UserRepository
from ..schemas.dto import UserCreateAdmin

# Note: Use AuthService for password hashing

from app.modules.shared.domain.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db, audit_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.user_repo = UserRepository(db)

    async def list_users(self, organisation_id: str) -> List[Dict[str, Any]]:
        return await self.user_repo.list({"organisation_id": organisation_id})

    async def create_user_admin(
        self, user, user_data: UserCreateAdmin
    ) -> Dict[str, Any]:
        """Business logic for admin-initiated user creation"""
        await self.permission_checker.check_admin_role(user)

        # Check if email exists
        existing = await self.user_repo.get_by_email(user_data.email)
        if existing:
            raise ValidationError("Email already registered")

        # Circular import protection
        from .auth_service import AuthService

        auth_service = AuthService(self.db)

        user_dict = user_data.dict()
        user_dict["hashed_password"] = auth_service.hash_password(
            user_dict.pop("password")
        )
        user_dict["organisation_id"] = user["organisation_id"]
        user_dict["active_status"] = True

        new_user = await self.user_repo.create(user_dict)

        # Audit log
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="USER_MANAGEMENT",
            entity_type="USER",
            entity_id=new_user["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            new_value={"email": user_data.email, "role": user_data.role},
        )

        return new_user

    async def deactivate_user(self, user, target_user_id: str) -> Dict[str, Any]:
        """Business logic for deactivating a user"""
        await self.permission_checker.check_admin_role(user)

        # Get old value for audit
        old_user = await self.user_repo.get_by_id(
            target_user_id, organisation_id=user["organisation_id"]
        )
        if not old_user:
            raise NotFoundError("User", target_user_id)

        user_model = UserModel(old_user)
        user_model.validate_for_deactivation(user["user_id"])

        await self.user_repo.update(
            target_user_id,
            {"active_status": False},
            organisation_id=user["organisation_id"],
        )

        # Audit log
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="USER_MANAGEMENT",
            entity_type="USER",
            entity_id=target_user_id,
            action_type="DEACTIVATE",
            user_id=user["user_id"],
            old_value={"active_status": old_user.get("active_status")},
            new_value={"active_status": False},
        )

        return {"message": "User deactivated successfully"}
