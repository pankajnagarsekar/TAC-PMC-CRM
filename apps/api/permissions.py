from fastapi import HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from auth import get_current_user
import logging

logger = logging.getLogger(__name__)


class PermissionChecker:
    """
    Permission enforcement middleware for Phase 1.
    RULES:
    1. User must be authenticated
    2. User must have active_status = TRUE
    3. For project-specific operations, user_project_map entry must exist
    4. Role-based permissions apply
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_authenticated_user(
        self, current_user: dict = Depends(get_current_user)
    ):
        """Get and validate authenticated user"""
        user_id = current_user.get("user_id")

        # Fetch user from database
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format"
            )
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Check active status
        if not user.get("active_status", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Convert _id to user_id for consistency
        user["user_id"] = str(user.pop("_id"))
        return user

    async def check_project_access(
        self, user: dict, project_id: str, require_write: bool = False
    ):
        """
        Check if user has access to a specific project.
        Args:
            user: User dict from get_authenticated_user
            project_id: Project ID to check access for
            require_write: If True, check for write access; else check for read access
        """
        # Admins have automatic access to all projects
        if user.get("role") == "Admin":
            return True

        # First check if project is in user's assigned_projects
        assigned_projects = user.get("assigned_projects", [])
        if project_id in assigned_projects:
            return True

        # Supervisors with assigned projects have full access
        # Handle both ObjectId and string project IDs
        try:
            if isinstance(project_id, str) and ObjectId.is_valid(project_id):
                project_query_id = ObjectId(project_id)
            else:
                project_query_id = project_id
        except Exception:
            project_query_id = project_id

        try:
            if isinstance(user["user_id"], str) and ObjectId.is_valid(user["user_id"]):
                user_query_id = ObjectId(user["user_id"])
            else:
                user_query_id = user["user_id"]
        except Exception:
            user_query_id = user["user_id"]

        # Check user_project_map as fallback
        mapping = await self.db.user_project_map.find_one({
            "user_id": user_query_id,
            "project_id": project_query_id
        })

        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to this project"
            )

        # Check access type
        if require_write and not mapping.get("write_access", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have write access to this project"
            )

        if not mapping.get("read_access", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have read access to this project"
            )

        return True

    async def check_admin_role(self, user: dict):
        """Check if user has Admin role"""
        if user.get("role") != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required for this operation"
            )
        return True

    async def verify_project_organisation(
        self, project_id: str, organisation_id: str
    ):
        """Verify that project belongs to the user's organisation"""
        query_id = project_id
        if isinstance(project_id, str) and ObjectId.is_valid(project_id):
            query_id = ObjectId(project_id)
        
        project = await self.db.projects.find_one({"_id": query_id})
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        if project.get("organisation_id") != organisation_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project does not belong to your organisation"
            )
        return True

    # =========================================================================
    # ROLE-BASED ENFORCEMENT (Phase 6.3 - Security Hardening)
    # =========================================================================

    async def check_web_crm_access(self, user: dict):
        """
        Block Supervisor from ALL Web CRM routes.
        Per spec 6.3.3: Supervisor blocked from Web CRM routes.
        """
        if user.get("role") == "Supervisor":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supervisors cannot access Web CRM"
            )
        return True

    async def check_client_readonly(self, user: dict):
        """
        Block Client from any write operations.
        Per spec 6.3.3: Client cannot access create/update/delete.
        """
        if user.get("role") == "Client":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Client role is read-only"
            )
        return True

    async def check_client_project_access(self, user: dict, project_id: str):
        """
        Client can only access THEIR assigned projects.
        Uses user_project_map to verify client-project assignment.
        """
        if user.get("role") != "Client":
            return True  # Not a client, skip this check

        # Handle ObjectId conversion
        try:
            user_query_id = ObjectId(user["user_id"]) if isinstance(user["user_id"], str) and ObjectId.is_valid(user["user_id"]) else user["user_id"]
        except Exception:
            user_query_id = user["user_id"]

        try:
            project_query_id = ObjectId(project_id) if isinstance(project_id, str) and ObjectId.is_valid(project_id) else project_id
        except Exception:
            project_query_id = project_id

        # Check if client has mapping to this project
        mapping = await self.db.user_project_map.find_one({
            "user_id": user_query_id,
            "project_id": project_query_id
        })

        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Client not authorized for this project"
            )

        return True

    async def check_write_access_with_role(self, user: dict, project_id: str = None):
        """
        Check write access with role enforcement:
        - Admin: Full write access
        - Client: BLOCKED from writes (read-only)
        - Supervisor: BLOCKED from Web CRM entirely
        """
        # Block Supervisor from Web CRM
        await self.check_web_crm_access(user)

        # Block Client from writes
        await self.check_client_readonly(user)

        # If project_id provided, also check project access
        if project_id:
            await self.check_project_access(user, project_id, require_write=True)

        return True
