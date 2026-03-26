from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from typing import Optional

from app.core.dependencies import get_current_user
from app.core.deps import get_auth_service
from app.services.auth_service import AuthService
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=GenericResponse[Token])
async def login(
    login_data: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """User login to get access and refresh tokens."""
    token = await auth_service.login(login_data)
    
    # Set refresh token in cookie (legacy compatibility or enhanced security)
    # We'll stick to returning it in the body for now as per Token schema,
    # but also set cookie if needed by frontend.
    return GenericResponse(data=token, message="Login successful")

@router.post("/refresh", response_model=GenericResponse[Token])
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using a valid refresh token."""
    token = await auth_service.refresh_token(refresh_data.refresh_token)
    return GenericResponse(data=token, message="Token refreshed")

@router.post("/logout", response_model=GenericResponse[dict])
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
