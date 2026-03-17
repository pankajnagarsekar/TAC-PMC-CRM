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
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g., WORK_ORDER, PAYMENT_CERTIFICATE)"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type (CREATE, UPDATE, DELETE, APPROVE, REJECT)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    limit: int = Query(100, ge=1, le=500),
    cursor: Optional[str] = Query(None, description="ISO timestamp for cursor-based pagination"),
    current_user: dict = Depends(get_current_user)
):
    """
    List audit logs with filtering.
    Only accessible by Admin.
    Supports filters: entity_type, entity_id, project_id, action_type, user_id, start_date, end_date
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
    
    parsed_start_date = None
    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
    
    parsed_end_date = None
    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")

    logs = await audit_service.get_audit_logs(
        organisation_id=current_user["organisation_id"],
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        action_type=action_type,
        user_id=user_id,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
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
