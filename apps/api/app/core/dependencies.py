from fastapi import HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional
import logging

from app.db.mongodb import get_db
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """
    Dependency to get current authenticated user from access token.
    Uses token revocation check.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = AuthService.decode_token(token, "access")
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        jti: str = payload.get("jti")
        
        if user_id is None or email is None:
            raise credentials_exception
            
        # Check revocation
        if jti and await AuthService.is_token_revoked(jti, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
            
        return payload
        
    except HTTPException as e:
        raise e
    except Exception:
        raise credentials_exception

async def get_authenticated_user(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """Get fully hydrated user from DB and validate active status."""
    user_id = current_user.get("user_id")

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.get("active_status", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Standardize _id
    user["user_id"] = str(user.pop("_id"))
    return user

class PermissionChecker:
    """
    Logic for project and role-based access control.
    """
    @staticmethod
    async def check_project_access(
        user: dict, 
        project_id: str, 
        db: AsyncIOMotorDatabase,
        require_write: bool = False
    ):
        if user.get("role") == "Admin":
            return True

        assigned_projects = user.get("assigned_projects", [])
        if project_id in assigned_projects:
            return True

        try:
            p_oid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
            u_oid = ObjectId(user["user_id"]) if ObjectId.is_valid(user["user_id"]) else user["user_id"]
        except:
            p_oid, u_oid = project_id, user["user_id"]

        mapping = await db.user_project_map.find_one({
            "user_id": u_oid,
            "project_id": p_oid
        })

        if not mapping:
            raise HTTPException(status_code=403, detail="User does not have access to this project")

        if require_write and not mapping.get("write_access", False):
            raise HTTPException(status_code=403, detail="User does not have write access to this project")

        return True

    @staticmethod
    async def check_admin_role(user: dict):
        if user.get("role") != "Admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        return True

    @staticmethod
    async def check_web_crm_access(user: dict):
        if user.get("role") == "Supervisor":
            raise HTTPException(status_code=403, detail="Supervisors cannot access Web CRM")
        return True

    @staticmethod
    async def check_client_readonly(user: dict):
        if user.get("role") == "Client":
            raise HTTPException(status_code=403, detail="Client role is read-only")
        return True
