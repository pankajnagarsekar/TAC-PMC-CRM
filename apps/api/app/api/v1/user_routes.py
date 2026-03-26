from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.core.dependencies import get_authenticated_user, get_user_service
from app.services.user_service import UserService
from app.schemas.user import UserResponse, UserCreateAdmin
from app.schemas.auth import Token, LoginRequest
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=GenericResponse[List[UserResponse]])
async def list_users(
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """List all users in the organisation (Admin only in service)."""
    users = await user_service.list_users(user["organisation_id"])
    return GenericResponse(data=users)

@router.post("/admin-create", response_model=GenericResponse[UserResponse])
async def create_user_admin(
    user_data: UserCreateAdmin,
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """Admin creates a new user."""
    new_user = await user_service.create_user_admin(user, user_data)
    return GenericResponse(data=new_user, message="User created successfully")

@router.delete("/{user_id}", response_model=GenericResponse[dict])
async def deactivate_user(
    user_id: str,
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """Admin deactivates a user."""
    result = await user_service.deactivate_user(user, user_id)
    return GenericResponse(data=result, message="User deactivated successfully")
