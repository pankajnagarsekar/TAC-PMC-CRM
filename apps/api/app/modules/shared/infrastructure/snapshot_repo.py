from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.shared.infrastructure.base_repository import BaseRepository
from app.modules.shared.domain.schemas import Snapshot

class SnapshotRepository(BaseRepository[Snapshot]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "snapshots", Snapshot)

    async def get_latest_by_entity(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot for an entity."""
        return await self.find_one(
            {"entity_type": entity_type, "entity_id": entity_id},
            sort=[("version", -1)]
        )

    async def get_all_versions(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """List all versions of an entity snapshot."""
        return await self.list(
            {"entity_type": entity_type, "entity_id": entity_id},
            sort=[("version", -1)]
        )

    async def get_by_checksum(self, checksum: str) -> Optional[Dict[str, Any]]:
        """Look up a snapshot by its content checksum."""
        return await self.find_one({"data_checksum": checksum})

    async def mark_previous_not_latest(self, entity_type: str, entity_id: str, session=None):
        """Standard update to ensure only one snapshot is marked as 'latest'."""
        await self.collection.update_many(
            {"entity_type": entity_type, "entity_id": entity_id, "is_latest": True},
            {"$set": {"is_latest": False}},
            session=session
        )
