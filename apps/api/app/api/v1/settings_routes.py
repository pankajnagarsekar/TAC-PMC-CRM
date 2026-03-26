from fastapi import APIRouter, Depends, status
from typing import List, Dict, Any

from app.core.dependencies import get_authenticated_user, get_settings_service
from app.services.settings_service import SettingsService
from app.schemas.settings_ai import GlobalSettings, CodeMaster, CodeMasterCreate
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/", response_model=GenericResponse[GlobalSettings])
async def get_settings(
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    settings = await settings_service.get_settings(user)
    return GenericResponse(data=settings)

@router.put("/", response_model=GenericResponse[dict])
async def update_settings(
    settings_data: Dict[str, Any],
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    result = await settings_service.update_settings(user, settings_data)
    return GenericResponse(data=result, message="Settings updated successfully")

@router.get("/codes", response_model=GenericResponse[List[CodeMaster]])
async def list_categories(
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    categories = await settings_service.list_categories(user)
    return GenericResponse(data=categories)

@router.post("/codes", response_model=GenericResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CodeMasterCreate,
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    result = await settings_service.create_category(user, category_data)
    return GenericResponse(data=result, message="Category created successfully")
