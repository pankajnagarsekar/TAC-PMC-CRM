from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status

from app.schemas.site import WorkersDailyLog, WorkersDailyLogCreate, WorkersDailyLogUpdate
from app.core.utils import serialize_doc

class SiteService:
    def __init__(self, db, audit_service):
        self.db = db
        self.audit_service = audit_service

    async def create_worker_log(self, user: dict, log_data: WorkersDailyLogCreate) -> Dict[str, Any]:
        # Check for existing
        existing = await self.db.worker_logs.find_one({
            "project_id": log_data.project_id,
            "date": log_data.date,
            "supervisor_id": user["user_id"]
        })

        if log_data.entries:
            total_workers = sum(e.workers_count for e in log_data.entries)
            entries_data = [e.dict() for e in log_data.entries]
        else:
            total_workers = len(log_data.workers)
            entries_data = []

        total_hours = sum(w.hours_worked for w in log_data.workers) if log_data.workers else 0

        log_dict = log_data.dict()
        log_dict["organisation_id"] = user["organisation_id"]
        log_dict["supervisor_id"] = user["user_id"]
        log_dict["supervisor_name"] = user["name"]
        log_dict["total_workers"] = log_data.total_workers or total_workers
        log_dict["total_hours"] = total_hours
        log_dict["status"] = "submitted"
        log_dict["updated_at"] = datetime.now(timezone.utc)

        if existing:
            await self.db.worker_logs.update_one({"_id": existing["_id"]}, {"$set": log_dict})
            updated = await self.db.worker_logs.find_one({"_id": existing["_id"]})
            return serialize_doc(updated)

        log_dict["created_at"] = datetime.now(timezone.utc)
        result = await self.db.worker_logs.insert_one(log_dict)
        log_dict["_id"] = result.inserted_id
        return serialize_doc(log_dict)

    async def update_worker_log(self, user: dict, log_id: str, update_data: WorkersDailyLogUpdate) -> Dict[str, Any]:
        query = {"_id": ObjectId(log_id), "organisation_id": user["organisation_id"]}
        
        update_dict = {k: v for k, v in update_data.dict(exclude_unset=True).items() if v is not None}
        update_dict["updated_at"] = datetime.now(timezone.utc)

        result = await self.db.worker_logs.find_one_and_update(
            query,
            {"$set": update_dict},
            return_document=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Worker log not found")
        return serialize_doc(result)
