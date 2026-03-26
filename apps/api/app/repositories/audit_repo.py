from app.repositories.base_repo import BaseRepository
from app.schemas.audit_notification import AuditLog
from pymongo import ASCENDING

class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db):
        super().__init__(db, "audit_logs", AuditLog)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        # Fixed CR-22: Audit indexes
        await self.collection.create_index([("user_id", ASCENDING)])
        await self.collection.create_index([("ref_id", ASCENDING)])

# Fixed CR-09: Removed duplicate NotificationRepository.
# It is now exclusively defined in notification_repo.py.
