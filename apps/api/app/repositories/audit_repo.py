from app.repositories.base_repo import BaseRepository
from app.schemas.audit_notification import AuditLog, Notification
 
class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db):
        super().__init__(db, "audit_logs", AuditLog)

class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db):
        super().__init__(db, "notifications", Notification)
