from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from typing import Optional, List

from app.core.dependencies import get_auth_service, get_current_user, get_authenticated_user, get_user_service, get_settings_service
from ..application.auth_service import AuthService
from ..application.user_service import UserService
from ..application.settings_service import SettingsService
from ..schemas.dto import Token, LoginRequest, RefreshTokenRequest, UserResponse, UserCreateAdmin, GlobalSettings
from app.modules.shared.domain.schemas import GenericResponse

# Create one router for the Identity Context
router = APIRouter(tags=["Identity"])

# ... (rest of endpoints)

@router.get("/settings/", response_model=GenericResponse[GlobalSettings])
async def get_settings(
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    """Fetch organisational settings."""
    settings = await settings_service.get_settings(user)
    return GenericResponse(data=settings)

@router.put("/settings/", response_model=GenericResponse[dict])
async def update_settings(
    settings_data: dict,
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    """Update organisational settings (Admin only)."""
    result = await settings_service.update_settings(user, settings_data)
    return GenericResponse(data=result, message="Settings updated successfully")

# --- AUTH ENPOINTS ---

@router.post("/auth/login", response_model=GenericResponse[Token])
async def login(
    login_data: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """User login to get access and refresh tokens."""
    token = await auth_service.login(login_data)
    return GenericResponse(data=token, message="Login successful")

@router.post("/auth/refresh", response_model=GenericResponse[Token])
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using a valid refresh token."""
    token = await auth_service.refresh_token(refresh_data.refresh_token)
    return GenericResponse(data=token, message="Token refreshed")

@router.post("/auth/logout", response_model=GenericResponse[dict])
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    user_payload: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user and revoke tokens."""
    result = await auth_service.logout(user_payload, refresh_token)
    response.delete_cookie(key="refresh_token")
    return GenericResponse(data=result, message="Logged out successfully")

# --- USER ENDPOINTS ---

@router.get("/users/", response_model=GenericResponse[List[UserResponse]])
async def list_users(
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """List all users in the organisation (Admin only in service)."""
    users = await user_service.list_users(user["organisation_id"])
    return GenericResponse(data=users)

@router.post("/users/admin-create", response_model=GenericResponse[UserResponse])
async def create_user_admin(
    user_data: UserCreateAdmin,
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """Admin creates a new user."""
    new_user = await user_service.create_user_admin(user, user_data)
    return GenericResponse(data=new_user, message="User created successfully")

@router.delete("/users/{user_id}", response_model=GenericResponse[dict])
async def deactivate_user(
    user_id: str,
    user: dict = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service)
):
    """Admin deactivates a user."""
    result = await user_service.deactivate_user(user, user_id)
    return GenericResponse(data=result, message="User deactivated successfully")
