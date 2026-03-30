from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..infrastructure.repository import TimelineRepository


class TimelineService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.timeline_repo = TimelineRepository(db)

    async def log_event(
        self,
        organisation_id: str,
        project_id: str,
        event_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session=None,
    ) -> Dict[str, Any]:
        """Log an event to the project timeline."""
        event_doc = {
            "organisation_id": organisation_id,
            "project_id": project_id,
            "event_type": event_type,
            "message": message,
            "data": data,
            "user_id": user_id or "SYSTEM",
            "timestamp": datetime.now(timezone.utc),
        }
        return await self.timeline_repo.create(event_doc, session=session)

    async def list_project_timeline(
        self, organisation_id: str, project_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List events for a specific project."""
        return await self.timeline_repo.list_project_timeline(
            project_id, organisation_id, limit
        )
