"""
AI Project Summary Routes — Phase 5 Feature

Endpoints:
- GET  /api/projects/{project_id}/ai-summary         → latest cached summary
- POST /api/projects/{project_id}/ai-summary/refresh  → trigger manual regeneration
"""

from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.database import get_db
from auth import get_current_user
from permissions import PermissionChecker
from core.ai_summary_service import AISummaryService
import os
import logging

logger = logging.getLogger(__name__)

ai_summary_router = APIRouter(prefix="/api/projects", tags=["AI Summary"])


def _get_service(db: AsyncIOMotorDatabase) -> AISummaryService:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    return AISummaryService(db=db, api_key=api_key)


@ai_summary_router.get("/{project_id}/ai-summary")
async def get_ai_summary(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns the latest AI-generated summary for the project.
    Returns 404 if no summary has been generated yet.
    Accessible by both Admin and Client roles.
    """
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_project_access(user, project_id)

    service = _get_service(db)
    summary = await service.get_latest(project_id)

    if not summary:
        raise HTTPException(
            status_code=404,
            detail="No AI summary found for this project. Trigger a refresh to generate one."
        )

    return summary


@ai_summary_router.post("/{project_id}/ai-summary/refresh")
async def refresh_ai_summary(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Triggers manual regeneration of the AI summary.
    Accessible by both Admin and Client roles.
    Uses upsert — always creates/updates today's summary.
    """
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_project_access(user, project_id)

    service = _get_service(db)

    try:
        result = await service.generate_and_store(
            project_id=project_id,
            organisation_id=user["organisation_id"],
            triggered_by="manual"
        )
        return result
    except Exception as e:
        logger.error(f"[AI:SUMMARY] Manual refresh failed for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")
