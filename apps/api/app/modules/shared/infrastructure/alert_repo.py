from typing import Any, Dict, List

from pydantic import BaseModel
from pymongo import ASCENDING

from .base_repository import BaseRepository


class AlertModel(BaseModel):
    # Minimal model for repository
    organisation_id: str
    alert_type: str
    severity: str


class AlertRepository(BaseRepository[AlertModel]):
    def __init__(self, db):
        super().__init__(db, "system_alerts", AlertModel)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("organisation_id", ASCENDING), ("resolved", ASCENDING)]
        )
        await self.collection.create_index([("alert_type", ASCENDING)])

    async def list_active_alerts(self, organisation_id: str) -> List[Dict[str, Any]]:
        query = {"organisation_id": organisation_id, "resolved": False}
        return await self.list(query, sort=[("detected_at", -1)])
