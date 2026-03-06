from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional, Union
from datetime import datetime
from auth import get_current_user
from core.database import db_manager
from audit_service import AuditService
from models import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

@router.get("/", response_model=dict)
async def list_audit_logs(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    cursor: Optional[str] = Query(None, description="ISO timestamp for cursor-based pagination"),
    current_user: dict = Depends(get_current_user)
):
    """
    List audit logs with filtering.
    Only accessible by Admin.
    """
    if current_user.get("role") != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can view audit logs"
        )
    
    db = db_manager.db
    audit_service = AuditService(db)
    
    parsed_cursor = None
    if cursor:
        try:
            parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format. Use ISO format.")

    logs = await audit_service.get_audit_logs(
        organisation_id=current_user["organisation_id"],
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        limit=limit,
        cursor=parsed_cursor
    )
    
    next_cursor = None
    if logs and len(logs) == limit:
        # Assumes logs are sorted DESC by timestamp
        last_log = logs[-1]
        if "timestamp" in last_log:
            ts = last_log["timestamp"]
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()
            else:
                next_cursor = str(ts)

    return {
        "items": logs,
        "next_cursor": next_cursor
    }
