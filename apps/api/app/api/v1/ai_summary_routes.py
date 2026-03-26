from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_ai_summary_service
from app.services.ai_summary_service import AISummaryService

router = APIRouter(prefix="/projects", tags=["AI Summary"])

@router.get("/{project_id}/ai-summary")
async def get_ai_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    ai_service: AISummaryService = Depends(get_ai_summary_service)
):
    return await ai_service.get_latest(user, project_id)

@router.post("/{project_id}/ai-summary/refresh")
async def refresh_ai_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    ai_service: AISummaryService = Depends(get_ai_summary_service)
):
    return await ai_service.refresh_summary(user, project_id)
