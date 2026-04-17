import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import Decimal128, ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..infrastructure.audit_repo import AuditRepository

logger = logging.getLogger(__name__)

# ARCHITECTURAL GUARD: Financial entity types that CANNOT be deleted
FINANCIAL_ENTITY_TYPES = [
    "WORK_ORDER",
    "PAYMENT_CERTIFICATE",
    "PAYMENT",
    "RETENTION_RELEASE",
]


class AuditService:
    """Service for immutable audit logging"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.audit_repo = AuditRepository(db)

    def enforce_financial_delete_guard(self, entity_type: str, action_type: str):
        """ARCHITECTURAL GUARD: Prevent DELETE operations on financial entities."""
        if action_type == "DELETE" and entity_type in FINANCIAL_ENTITY_TYPES:
            # We raise a generic Exception or we could import the DomainException here
            from ..domain.exceptions import FinancialIntegrityError

            raise FinancialIntegrityError(
                f"ARCHITECTURAL GUARD: Cannot DELETE {entity_type}. Financial entities are immutable."
            )

    @staticmethod
    def _sanitize_for_audit(value: Any) -> Any:
        """Recursively convert BSON types to JSON-safe primitives for audit storage."""
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, Decimal128):
            return float(value.to_decimal())
        if isinstance(value, dict):
            return {k: AuditService._sanitize_for_audit(v) for k, v in value.items()}
        if isinstance(value, list):
            return [AuditService._sanitize_for_audit(i) for i in value]
        return value

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
        old_value_json: Optional[Dict[str, Any]] = None,
        new_value_json: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session=None,
    ):
        """Log an action to audit trail (INSERT ONLY)."""
        self.enforce_financial_delete_guard(entity_type, action_type)

        # Support both old_value/new_value and old_value_json/new_value_json kwargs
        effective_old = old_value or old_value_json
        effective_new = new_value or new_value_json

        try:
            audit_entry = {
                "organisation_id": organisation_id,
                "project_id": project_id,
                "module_name": module_name,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "action_type": action_type,
                "old_value_json": self._sanitize_for_audit(effective_old),
                "new_value_json": self._sanitize_for_audit(effective_new),
                "metadata": self._sanitize_for_audit(metadata),
                "user_id": str(user_id),
                "timestamp": datetime.now(timezone.utc),
            }

            await self.audit_repo.create(audit_entry, session=session)
        except Exception as exc:
            logger.error("AuditService.log_action failed: %s", exc, exc_info=True)

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
        cursor: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs (READ ONLY)"""
        query = {"organisation_id": organisation_id}

        if entity_type:
            query["entity_type"] = entity_type
        if entity_id:
            query["entity_id"] = entity_id
        if project_id:
            query["project_id"] = project_id
        if action_type:
            query["action_type"] = action_type
        if user_id:
            query["user_id"] = user_id

        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            query["timestamp"] = date_filter

        if cursor:
            if "timestamp" not in query:
                query["timestamp"] = {}
            query["timestamp"]["$lt"] = cursor

        return await self.audit_repo.list(query, sort=[("timestamp", -1)], limit=limit)
