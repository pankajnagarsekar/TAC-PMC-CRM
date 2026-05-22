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

FINANCIAL_AUDIT_ENTITY_TYPES = [
    "WORK_ORDER",
    "PAYMENT_CERTIFICATE",
    "PROJECT_CATEGORY",
    "RETENTION_RELEASE",
    "PETTY_CASH_ALERT",
    "BUDGET_REVISION",
    "BUDGET",
    "EVM_BASELINE"
]


class AuditService:
    """Service for immutable audit logging"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.audit_repo = AuditRepository(db)

    def enforce_financial_delete_guard(
        self,
        entity_type: str,
        action_type: str,
        old_value: Optional[Dict[str, Any]] = None
    ):
        """
        ARCHITECTURAL GUARD: Prevent DELETE operations on final financial entities.
        Allows deletion of 'Draft' entities to support record purging (Track I3).
        """
        if action_type == "DELETE" and entity_type in FINANCIAL_ENTITY_TYPES:
            # Allow deletion if it's clearly a Draft (Point 75, Track I3)
            if old_value and old_value.get("status") == "Draft":
                return

            from ..domain.exceptions import FinancialIntegrityError
            raise FinancialIntegrityError(
                f"ARCHITECTURAL GUARD: Cannot DELETE {entity_type} in its current state. "
                "Financial entities are immutable once finalized."
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
        # Support both old_value/new_value and old_value_json/new_value_json kwargs
        effective_old = old_value or old_value_json
        effective_new = new_value or new_value_json

        self.enforce_financial_delete_guard(entity_type, action_type, effective_old)

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

    async def log_financial_event(
        self,
        organisation_id: str,
        entity_type: str,
        entity_id: str,
        action_type: str,
        user_id: str,
        project_id: str,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session=None,
    ):
        """
        Specialized helper for logging financial events with mandatory project_id.
        """
        if entity_type not in FINANCIAL_AUDIT_ENTITY_TYPES:
            logger.warning(f"Logging financial event for untracked entity type: {entity_type}")

        await self.log_action(
            organisation_id=organisation_id,
            module_name="FINANCIAL_MANAGEMENT",
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            user_id=user_id,
            project_id=project_id,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata,
            session=session
        )

    @staticmethod
    def get_entity_type_options() -> List[str]:
        """Return all supported entity types for filtering."""
        # Combine base types and financial types
        base_types = ["TASK", "WORKER_LOG", "CASH_TRANSACTION", "DPR", "CODE_MASTER"]
        return sorted(list(set(base_types + FINANCIAL_AUDIT_ENTITY_TYPES)))

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

        logs = await self.audit_repo.list(query, sort=[("timestamp", -1)], limit=limit)

        # --- Enrich: batch-lookup user names ---
        user_ids = list({log.get("user_id") for log in logs if log.get("user_id")})
        user_map: Dict[str, str] = {}
        if user_ids:
            try:
                users = await self.db["users"].find(
                    {"_id": {"$in": [ObjectId(uid) for uid in user_ids if ObjectId.is_valid(uid)]}},
                    {"_id": 1, "name": 1},
                ).to_list(length=len(user_ids))
                user_map = {str(u["_id"]): u.get("name", "") for u in users}
            except Exception:
                pass

        # --- Enrich: batch-lookup project names (BUG-007) ---
        project_ids = list({log.get("project_id") for log in logs if log.get("project_id")})
        project_map: Dict[str, str] = {}
        if project_ids:
            try:
                # Projects might be referenced by string ID or ObjectId
                p_filter = {
                    "$or": [
                        {"project_id": {"$in": project_ids}},
                        {"_id": {"$in": [ObjectId(pid) for pid in project_ids if ObjectId.is_valid(pid)]}}
                    ]
                }
                projects = await self.db["projects"].find(
                    p_filter,
                    {"_id": 1, "project_id": 1, "project_name": 1},
                ).to_list(length=len(project_ids) * 2)

                for p in projects:
                    p_name = p.get("project_name") or p.get("name", "")
                    # Map both ObjectId string and project_id string
                    project_map[str(p["_id"])] = p_name
                    if p.get("project_id"):
                        project_map[p["project_id"]] = p_name
            except Exception:
                pass

        # --- Normalize field names for frontend ---
        result = []
        for log in logs:
            log["log_id"] = str(log.get("id") or log.get("_id") or "")
            log["created_at"] = log.get("timestamp") or log.get("created_at")
            log["previous_state"] = log.get("old_value_json") or log.get("old_value")
            if "new_value_json" in log and "new_value" not in log:
                log["new_value"] = log["new_value_json"]

            uid = str(log.get("user_id", ""))
            log["user_name"] = user_map.get(uid, "System")

            pid = str(log.get("project_id", ""))
            if pid and pid != "None":
                log["project_name"] = project_map.get(pid, "Unknown Project")
            else:
                log["project_name"] = "Global"

            result.append(log)

        return result
