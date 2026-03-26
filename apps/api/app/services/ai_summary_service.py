import os
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException

from app.core.ai_summary_service import AISummaryService as CoreAISummaryService

logger = logging.getLogger(__name__)

class AISummaryService:
    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker
        self.core_service = CoreAISummaryService(db=db, api_key=os.environ.get("OPENAI_API_KEY"))

    async def get_latest(self, user: dict, project_id: str) -> Optional[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        summary = await self.core_service.get_latest(project_id)
        if not summary:
            raise HTTPException(status_code=404, detail="No AI summary found.")
        return summary

    async def refresh_summary(self, user: dict, project_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        try:
            return await self.core_service.generate_and_store(
                project_id=project_id,
                organisation_id=user["organisation_id"],
                triggered_by="manual"
            )
        except Exception as e:
            logger.error(f"AI Summary failed: {e}")
            raise HTTPException(status_code=500, detail="Generation failed.")
