from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import hashlib
import json
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.snapshot_repo import SnapshotRepository
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)

class SnapshotService:
    REPORT_TYPES = [
        "FINANCIAL_SUMMARY",
        "WORK_ORDER_REGISTER",
        "PAYMENT_CERTIFICATE_REGISTER",
        "RETENTION_SUMMARY",
        "BUDGET_UTILIZATION",
        "DPR_DAILY",
        "PROGRESS_REPORT",
        "AUDIT_TRAIL"
    ]

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.snapshot_repo = SnapshotRepository(db)

    def _compute_checksum(self, data: Dict) -> str:
        """Compute SHA-256 checksum of data."""
        # Using a stable serialization for checksum consistency
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def create_snapshot(
        self,
        entity_type: str,
        entity_id: str,
        organisation_id: str,
        user_id: str,
        data: Dict[str, Any],
        project_id: Optional[str] = None,
        report_type: Optional[str] = None,
        session=None
    ) -> Dict[str, Any]:
        """
        Create an immutable snapshot of an entity or report.
        """
        # 1. Get next version
        latest = await self.snapshot_repo.get_latest_by_entity(entity_type, entity_id)
        version = (latest["version"] + 1) if latest else 1

        # 2. Compute checksum
        checksum = self._compute_checksum(data)

        # 3. Build snapshot doc
        snapshot_doc = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "organisation_id": organisation_id,
            "project_id": project_id,
            "report_type": report_type or entity_type,
            "version": version,
            "data_json": data,
            "data_checksum": checksum,
            "generated_by": user_id,
            "generated_at": datetime.now(timezone.utc),
            "is_latest": True,
            "immutable_flag": True
        }

        # 4. Mark previous not latest
        await self.snapshot_repo.mark_previous_not_latest(entity_type, entity_id, session=session)

        # 5. Insert
        return await self.snapshot_repo.create(snapshot_doc, session=session)

    async def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        return await self.snapshot_repo.get(snapshot_id)

    async def list_snapshots(self, organisation_id: str, project_id: Optional[str] = None, report_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {"organisation_id": organisation_id}
        if project_id:
            query["project_id"] = project_id
        if report_type:
            query["report_type"] = report_type
        
        return await self.snapshot_repo.list(query, sort=[("generated_at", -1)])
