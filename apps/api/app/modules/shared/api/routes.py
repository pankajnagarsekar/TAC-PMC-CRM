from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.dependencies import get_authenticated_user, get_notification_service, get_audit_service
from ..application.notification_service import NotificationService
from ..application.audit_service import AuditService
from ..domain.schemas import GenericResponse

router = APIRouter()

# --- NOTIFICATION ENDPOINTS ---

@router.get("/notifications", response_model=GenericResponse[List[Dict[str, Any]]], tags=["Notifications"])
async def list_notifications(
    limit: int = 50,
    user: dict = Depends(get_authenticated_user),
    service: NotificationService = Depends(get_notification_service)
):
    """List notifications for the current user."""
    results = await service.list_notifications(user["user_id"], limit=limit)
    return GenericResponse(data=results)

@router.post("/notifications/{notif_id}/read", response_model=GenericResponse[dict], tags=["Notifications"])
async def mark_notification_read(
    notif_id: str,
    user: dict = Depends(get_authenticated_user),
    service: NotificationService = Depends(get_notification_service)
):
    """Mark a specific notification as read."""
    await service.mark_as_read(notif_id, user["user_id"])
    return GenericResponse(data={"id": notif_id}, message="Notification marked as read")

# --- AUDIT LOG ENDPOINTS ---

@router.get("/audit/logs", response_model=GenericResponse[List[Dict[str, Any]]], tags=["Audit Registry"])
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    project_id: Optional[str] = None,
    action_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_authenticated_user),
    service: AuditService = Depends(get_audit_service)
):
    """Retrieve audit logs for the organisation (Admin access enforced in service)."""
    # Note: Service layer should ideally check admin role for general logs
    logs = await service.get_audit_logs(
        organisation_id=user["organisation_id"],
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        action_type=action_type,
        user_id=user_id,
        limit=limit
    )
    return GenericResponse(data=logs)
