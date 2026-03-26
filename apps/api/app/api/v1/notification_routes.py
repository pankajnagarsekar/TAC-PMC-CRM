from fastapi import APIRouter, Depends, Query
from typing import Dict, Any

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_notification_service
from app.services.notification_service import NotificationService
from app.schemas.audit_notification import NotificationCreate
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=GenericResponse[Dict[str, Any]])
async def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    user: dict = Depends(get_authenticated_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    notifs = await notification_service.get_notifications(user, limit, unread_only)
    return GenericResponse(data=notifs)

@router.post("/{notification_id}/read", response_model=GenericResponse[dict])
async def mark_read(
    notification_id: str,
    user: dict = Depends(get_authenticated_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    result = await notification_service.mark_read(user, notification_id)
    return GenericResponse(data=result, message="Notification marked as read")

@router.post("/mark-all-read", response_model=GenericResponse[dict])
async def mark_all_read(
    user: dict = Depends(get_authenticated_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    result = await notification_service.mark_all_read(user)
    return GenericResponse(data=result, message="All notifications marked as read")
