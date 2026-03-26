from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_audit_service
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    project_id: Optional[str] = None,
    action_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(100, le=500),
    user: dict = Depends(get_authenticated_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    return await audit_service.get_audit_logs(
        organisation_id=user["organisation_id"],
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        action_type=action_type,
        user_id=user_id,
        limit=limit
    )
