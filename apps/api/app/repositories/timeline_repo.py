from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from .base_repo import BaseRepository

class TimelineRepository(BaseRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "timeline")

    async def list_project_timeline(self, project_id: str, organisation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.list(
            {"project_id": project_id, "organisation_id": organisation_id},
            limit=limit,
            sort=[("timestamp", -1)]
        )
