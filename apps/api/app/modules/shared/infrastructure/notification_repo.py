from app.modules.shared.infrastructure.base_repository import BaseRepository
from app.modules.shared.domain.schemas import Notification
from pymongo import ASCENDING

class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db):
        super().__init__(db, "notifications", Notification)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("recipient_user_id", ASCENDING)])
        await self.collection.create_index([("organisation_id", ASCENDING)])
        await self.collection.create_index([("is_read", ASCENDING)])
        await self.collection.create_index([("created_at", ASCENDING)])
