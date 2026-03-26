from app.repositories.base_repo import BaseRepository
from app.schemas.audit_notification import Notification
from pymongo import ASCENDING

class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db):
        super().__init__(db, "notifications", Notification)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        # Fixed CR-22: Notification efficient lookup
        await self.collection.create_index([("user_id", ASCENDING), ("read_status", ASCENDING)])
