from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.schemas.audit_notification import Notification, NotificationCreate
from app.core.utils import serialize_doc

class NotificationService:
    def __init__(self, db):
        self.db = db

    async def create_notification(self, user: dict, notification_data: NotificationCreate) -> Dict[str, Any]:
        notification_doc = notification_data.dict()
        notification_doc["organisation_id"] = user["organisation_id"]
        notification_doc["sender_id"] = user["user_id"]
        notification_doc["sender_name"] = user.get("name", "System")
        notification_doc["is_read"] = False
        notification_doc["created_at"] = datetime.now(timezone.utc)

        result = await self.db.notifications.insert_one(notification_doc)
        return {
            "notification_id": str(result.inserted_id),
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

        cursor = self.db.notifications.find(query).sort("created_at", -1).limit(limit)
        notifications = await cursor.to_list(length=limit)

        unread_count = await self.db.notifications.count_documents({
            "organisation_id": user["organisation_id"],
            "$or": [
                {"recipient_role": user["role"].lower()},
                {"recipient_user_id": user["user_id"]}
            ],
            "is_read": False
        })

        return {
            "notifications": [serialize_doc(n) for n in notifications],
            "unread_count": unread_count,
            "total": len(notifications)
        }

    async def mark_read(self, user: dict, notification_id: str) -> Dict[str, Any]:
        result = await self.db.notifications.update_one(
            {
                "_id": ObjectId(notification_id),
                "organisation_id": user["organisation_id"]
            },
            {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"status": "marked_read"}

    async def mark_all_read(self, user: dict) -> Dict[str, Any]:
        result = await self.db.notifications.update_many(
            {
                "organisation_id": user["organisation_id"],
                "$or": [
                    {"recipient_role": user["role"].lower()},
                    {"recipient_user_id": user["user_id"]}
                ],
                "is_read": False
            },
            {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}}
        )
        return {"status": "success", "marked_count": result.modified_count}
