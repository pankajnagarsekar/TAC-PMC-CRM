from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
import logging

from app.schemas.site import WorkersDailyLog, WorkersDailyLogCreate, WorkersDailyLogUpdate
from app.repositories.site_repo import WorkerLogRepository
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)

from app.repositories.site_repo import WorkerLogRepository, DPRRepository, AttendanceRepository

class SiteService:
    def __init__(self, db, audit_service):
        self.db = db
        self.audit_service = audit_service
        self.worker_log_repo = WorkerLogRepository(db)
        self.dpr_repo = DPRRepository(db)
        self.attendance_repo = AttendanceRepository(db)

    async def create_dpr(self, user: dict, project_id: str, dpr_data: dict) -> Dict[str, Any]:
        """Create a daily progress report with immutable snapshot requirements."""
        dpr_date = dpr_data.get("dpr_date") # Expected ISO string or date
        
        # Check for existing
        existing = await self.dpr_repo.find_one({
            "project_id": project_id,
            "dpr_date": dpr_date
        })
        
        if existing:
            return {"exists": True, "dpr_id": existing["id"], "message": "DPR already exists for this date"}

        dpr_doc = {
            **dpr_data,
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "supervisor_id": user["user_id"],
            "status": "Submitted",
            "created_at": datetime.now(timezone.utc),
            "version": 1
        }
        
        new_dpr = await self.dpr_repo.create(dpr_doc)
        
        # Audit
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="DPR",
            entity_id=new_dpr["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=project_id,
            new_value=new_dpr
        )
        
        return new_dpr

    async def list_site_logs(self, user: dict, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.worker_log_repo.list({
            "project_id": project_id,
            "organisation_id": user["organisation_id"]
        }, limit=limit, sort=[("date", -1)])

    async def record_attendance(self, user: dict, project_id: str, attendance_data: List[dict]) -> Dict[str, Any]:
        """Batch record worker attendance."""
        results = []
        for entry in attendance_data:
            entry["project_id"] = project_id
            entry["organisation_id"] = user["organisation_id"]
            entry["recorded_by"] = user["user_id"]
            res = await self.attendance_repo.create(entry)
            results.append(res)
            
        return {"status": "success", "count": len(results)}
