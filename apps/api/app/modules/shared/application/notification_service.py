from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from ..domain.schemas import NotificationCreate
from ..infrastructure.notification_repo import NotificationRepository

class NotificationService:
    def __init__(self, db):
        self.db = db
        self.notif_repo = NotificationRepository(db)

    async def create_notification(self, user: dict, notification_data: NotificationCreate) -> Dict[str, Any]:
        notification_doc = notification_data.dict()
        notification_doc["organisation_id"] = user["organisation_id"]
        notification_doc["sender_id"] = user["user_id"]
        notification_doc["sender_name"] = user.get("name", "System")
        notification_doc["is_read"] = False
        notification_doc["created_at"] = datetime.now(timezone.utc)

        result = await self.notif_repo.create(notification_doc)
        return {
            "notification_id": result["id"],
            "status": "created"
        }

    async def get_notifications(self, user: dict, limit: int = 50, unread_only: bool = False) -> Dict[str, Any]:
        query = {
            "organisation_id": user["organisation_id"],
            "$or": [
                {"recipient_role": user["role"].lower()},
                {"recipient_user_id": user["user_id"]}
            ]
        }
        if unread_only:
            query["is_read"] = False

        notifications = await self.notif_repo.list(query, sort=[("created_at", -1)], limit=limit)

        unread_count = await self.notif_repo.count_documents({
            "organisation_id": user["organisation_id"],
            "$or": [
                {"recipient_role": user["role"].lower()},
                {"recipient_user_id": user["user_id"]}
            ],
            "is_read": False
        })

        return {
            "notifications": notifications,
            "unread_count": unread_count,
            "total": len(notifications)
        }

    async def mark_read(self, user: dict, notification_id: str) -> Dict[str, Any]:
        result = await self.notif_repo.update(
            notification_id,
            {"is_read": True, "read_at": datetime.now(timezone.utc)},
            organisation_id=user["organisation_id"]
        )
        if not result:
            from app.modules.shared.domain.exceptions import NotFoundError
            raise NotFoundError("Notification", notification_id)
        return {"status": "marked_read"}

    async def mark_all_read(self, user: dict) -> Dict[str, Any]:
        query = {
            "organisation_id": user["organisation_id"],
            "$or": [
                {"recipient_role": user["role"].lower()},
                {"recipient_user_id": user["user_id"]}
            ],
            "is_read": False
        }
        result = await self.notif_repo.update_many(
            query,
            {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}}
        )
        return {"status": "success", "marked_count": result}
