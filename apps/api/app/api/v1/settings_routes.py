from fastapi import APIRouter, Depends, status
from typing import List, Dict, Any

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_settings_service
from app.services.settings_service import SettingsService
from app.schemas.settings_ai import GlobalSettings, CodeMaster, CodeMasterCreate

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/", response_model=GlobalSettings)
async def get_settings(
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    return await settings_service.get_settings(user)

@router.put("/")
async def update_settings(
    settings_data: Dict[str, Any],
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    return await settings_service.update_settings(user, settings_data)

@router.get("/codes", response_model=List[CodeMaster])
async def list_categories(
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    return await settings_service.list_categories(user)

@router.post("/codes", status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CodeMasterCreate,
    user: dict = Depends(get_authenticated_user),
    settings_service: SettingsService = Depends(get_settings_service)
):
    return await settings_service.create_category(user, category_data)
