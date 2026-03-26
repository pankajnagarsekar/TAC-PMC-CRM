from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base_repo import BaseRepository
from app.schemas.alert import Alert

class AlertRepository(BaseRepository[Alert]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "alerts", Alert)

    async def list_active_alerts(self, organisation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.list(
            {"organisation_id": organisation_id, "resolved": False},
            limit=limit,
            sort=[("detected_at", -1)]
        )

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("organisation_id", 1), ("resolved", 1)])
        await self.collection.create_index([("detected_at", -1)])
