from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

from app.repositories.user_repo import UserProjectMapRepository

logger = logging.getLogger(__name__)

class PermissionChecker:
    """
    Sovereign Logic for project and role-based access control. (Point 17, 89)
    Isolates transition and access rules from the DI layer.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.map_repo = UserProjectMapRepository(db)

    @staticmethod
    async def validate_active_user(user: dict):
        """Fixed CR-23: Unified active-status check logic."""
        if not user:
            raise HTTPException(status_code=401, detail="INVALID_SESSION: User record not found.")
        if not user.get("active_status", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="ACCESS_DENIED: Account is inactive. Contact Administrator."
            )
        return True

    async def check_project_access(
        self,
        user: dict, 
        project_id: str, 
        require_write: bool = False
    ):
        """Verify user has clearance for a specific project."""
        await self.validate_active_user(user)
        
        if user.get("role") == "Admin":
            return True

        mapping = await self.map_repo.get_mapping(user["user_id"], project_id)

        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="ACCESS_DENIED: User not cleared for this project."
            )

        if require_write and not mapping.get("write_access", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="ACCESS_DENIED: Write permission required."
            )

        return True

    @staticmethod
    async def check_admin_role(user: dict):
        """Block non-admin operations."""
        if user.get("role") != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="PERMISSION_ERROR: Administrative role required."
            )
        return True

    async def check_write_access_with_role(self, user: dict, project_id: str = None):
        """
        Hard role enforcement with project context:
        - Supervisor: BLOCKED from Web CRM
        - Client: Read-only
        """
        role = user.get("role")
        if role == "Supervisor":
             raise HTTPException(status_code=403, detail="ENVIRONMENT_ERROR: Supervisors restricted to Mobile.")
        
        if role == "Client":
            raise HTTPException(status_code=403, detail="DOMAIN_ERROR: Client role is strictly read-only.")

        if project_id:
            await self.check_project_access(user, project_id, require_write=True)

        return True

    @staticmethod
    async def check_web_crm_access(user: dict):
        """Verify role is permitted for web operations."""
        if user.get("role") == "Supervisor":
            raise HTTPException(status_code=403, detail="ACCESS_DENIED: Supervisor must use Mobile interface.")
        return True

    @staticmethod
    async def check_client_readonly(user: dict):
        """Immediate rejection of client write attempts."""
        if user.get("role") == "Client":
            raise HTTPException(status_code=403, detail="ACCESS_DENIED: Client role is read-only.")
        return True
