from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base_repo import BaseRepository
from pydantic import BaseModel

class ProjectStats(BaseModel):
    project_id: str
    total_phases: int = 0
    active_items: int = 0
    master_budget: float = 0.0
    total_committed: float = 0.0
    variance: float = 0.0
    compliance_rate: float = 100.0
    last_updated: Any = None

class ProjectStatsRepository(BaseRepository[ProjectStats]):
    """
    Sovereign Read Model for high-performance dashboard access (Point 46, 58).
    Decouples expensive aggregations from the critical path.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "read_model_project_stats", ProjectStats)

    async def get_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"project_id": str(project_id)})

    async def refresh_stats(self, project_id: str, data: Dict[str, Any]):
        """Overwrite stats entry with fresh pre-aggregated data."""
        from datetime import datetime, timezone
        await self.collection.update_one(
            {"project_id": str(project_id)},
            {"$set": {**data, "last_updated": datetime.now(timezone.utc)}},
            upset=True
        )
