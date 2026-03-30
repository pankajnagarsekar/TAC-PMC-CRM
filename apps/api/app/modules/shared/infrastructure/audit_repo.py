from pymongo import ASCENDING

from app.modules.shared.domain.schemas import AuditLog
from app.modules.shared.infrastructure.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db):
        super().__init__(db, "audit_logs", AuditLog)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("user_id", ASCENDING)])
        await self.collection.create_index([("entity_id", ASCENDING)])
        await self.collection.create_index([("organisation_id", ASCENDING)])
        await self.collection.create_index([("timestamp", ASCENDING)])
