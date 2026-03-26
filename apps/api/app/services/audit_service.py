from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
import logging

from app.repositories.audit_repo import AuditRepository

logger = logging.getLogger(__name__)

# ARCHITECTURAL GUARD: Financial entity types that CANNOT be deleted
FINANCIAL_ENTITY_TYPES = [
    "WORK_ORDER",
    "PAYMENT_CERTIFICATE",
    "PAYMENT",
    "RETENTION_RELEASE"
]

class AuditService:
    """Service for immutable audit logging"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.audit_repo = AuditRepository(db)

    def enforce_financial_delete_guard(self, entity_type: str, action_type: str):
        """ARCHITECTURAL GUARD: Prevent DELETE operations on financial entities."""
        if action_type == "DELETE" and entity_type in FINANCIAL_ENTITY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"ARCHITECTURAL GUARD: Cannot DELETE {entity_type}. Financial entities are immutable."
            )

    async def log_action(
        self,
        organisation_id: str,
        module_name: str,
        entity_type: str,
        entity_id: str,
        action_type: str,
        user_id: str,
        project_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        session=None
    ):
        """Log an action to audit trail (INSERT ONLY)."""
        self.enforce_financial_delete_guard(entity_type, action_type)

        try:
            audit_entry = {
                "organisation_id": organisation_id,
                "project_id": project_id,
                "module_name": module_name,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action_type": action_type,
                "old_value_json": old_value,
                "new_value_json": new_value,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc)
            }

            await self.audit_repo.create(audit_entry, session=session)
            logger.info(f"Audit log created: {action_type} on {entity_type}:{entity_id} by user:{user_id}")
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")

    async def get_audit_logs(
        self,
        organisation_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        project_id: Optional[str] = None,
        action_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        cursor: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs (READ ONLY)"""
        query = {"organisation_id": organisation_id}

        if entity_type: query["entity_type"] = entity_type
        if entity_id: query["entity_id"] = entity_id
        if project_id: query["project_id"] = project_id
        if action_type: query["action_type"] = action_type
        if user_id: query["user_id"] = user_id
        
        if start_date or end_date:
            date_filter = {}
            if start_date: date_filter["$gte"] = start_date
            if end_date: date_filter["$lte"] = end_date
            query["timestamp"] = date_filter
            
        if cursor:
            if "timestamp" not in query: query["timestamp"] = {}
            query["timestamp"]["$lt"] = cursor

        return await self.audit_repo.list(query, sort=[("timestamp", -1)], limit=limit)
