from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_user_service
from app.services.user_service import UserService
from app.schemas.user import UserResponse, UserCreateAdmin
from app.schemas.auth import Token, LoginRequest

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=List[UserResponse])
async def list_users(
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """List all users in the organisation (Admin only in service)."""
    return await user_service.list_users(user["organisation_id"])

@router.post("/admin-create", response_model=UserResponse)
async def create_user_admin(
    user_data: UserCreateAdmin,
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """Admin creates a new user."""
    return await user_service.create_user_admin(user, user_data)

@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """Admin deactivates a user."""
    return await user_service.deactivate_user(user, user_id)
