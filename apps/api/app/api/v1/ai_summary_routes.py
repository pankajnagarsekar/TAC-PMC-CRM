from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_ai_summary_service
from app.services.ai_summary_service import AISummaryService
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/projects", tags=["AI Summary"])

@router.get("/{project_id}/ai-summary", response_model=GenericResponse[Dict[str, Any]])
async def get_ai_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    ai_service: AISummaryService = Depends(get_ai_summary_service)
):
    summary = await ai_service.get_latest(user, project_id)
    return GenericResponse(data=summary)

@router.post("/{project_id}/ai-summary/refresh", response_model=GenericResponse[Dict[str, Any]])
async def refresh_ai_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    ai_service: AISummaryService = Depends(get_ai_summary_service)
):
    summary = await ai_service.refresh_summary(user, project_id)
    return GenericResponse(data=summary, message="AI summary refreshed successfully")
