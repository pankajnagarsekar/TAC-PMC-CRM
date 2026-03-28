from typing import Dict, Any, Optional
from app.modules.shared.infrastructure.base_repository import BaseRepository
from app.core.time import now

class ProjectStatsRepository(BaseRepository[Any]):
    """
    Read Model Repository for Project-level statistics.
    Provides optimized access for dashboards and reporting.
    """
    def __init__(self, db):
        super().__init__(db, "project_stats", Any)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", 1)], unique=True)

    async def refresh_stats(self, project_id: str, stats: Dict[str, Any], session=None):
        """Standard update-or-insert for project stats read-model."""
        doc = {
            "project_id": project_id,
            **stats,
            "last_updated": now()
        }
        return await self.update_one(
            {"project_id": project_id},
            {"$set": doc},
            upsert=True,
            session=session
        )

    async def get_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"project_id": project_id})
