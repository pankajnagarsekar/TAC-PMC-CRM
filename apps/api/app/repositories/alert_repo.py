from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from .base_repo import BaseRepository

class AlertRepository(BaseRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "alerts")

    async def list_active_alerts(self, organisation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.list(
            {"organisation_id": organisation_id, "resolved": False},
            limit=limit,
            sort=[("detected_at", -1)]
        )
