from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
import logging
import hashlib
import base64

from app.schemas.site import WorkersDailyLog, WorkersDailyLogCreate, WorkersDailyLogUpdate, DPRImage, SiteOverheadCreate, SiteOverheadUpdate
from app.repositories.site_repo import WorkerLogRepository, DPRRepository, AttendanceRepository, VoiceLogRepository, SiteOverheadRepository
from app.repositories.user_repo import UserRepository
from app.core.config import settings
from app.core.pdf_service import pdf_generator
from app.domain.state_machine import StateMachine
from app.core.time import now as ts_now

logger = logging.getLogger(__name__)

class SiteService:
    """
    Sovereign Site Operations Orchestrator (Point 1, 31, 87, 94).
    Enforces DPR status transitions via StateMachine.
    """
    def __init__(self, db, audit_service, permission_checker, snapshot_service):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.snapshot_service = snapshot_service
        self.worker_log_repo = WorkerLogRepository(db)
        self.dpr_repo = DPRRepository(db)
        self.attendance_repo = AttendanceRepository(db)
        self.voice_log_repo = VoiceLogRepository(db)
        self.site_overhead_repo = SiteOverheadRepository(db)
        self.user_repo = UserRepository(db)

    async def _enrich_with_user_names(self, doc: dict, fields: List[str]) -> dict:
        for field in fields:
            user_id = doc.get(field)
            if user_id:
                u = await self.user_repo.get_by_id(user_id)
                if u:
                    doc[f"{field}_name"] = u.get("name") or u.get("full_name") or u.get("email", "").split("@")[0]
        return doc

    async def create_dpr(self, user: dict, project_id: str, dpr_data: dict) -> Dict[str, Any]:
        """Create a daily progress report with immutable snapshot requirements."""
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        
        dpr_date = dpr_data.get("dpr_date")
        existing = await self.dpr_repo.find_one({"project_id": project_id, "dpr_date": dpr_date})
        
        if existing:
            return {"exists": True, "dpr_id": existing["id"], "message": "DPR already exists for this date"}

        dpr_doc = {
            **dpr_data,
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "supervisor_id": user["user_id"],
            "status": "Draft",
            "created_at": ts_now(),
            "version": 1
        }
        
        new_dpr = await self.dpr_repo.create(dpr_doc)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="SITE_OPERATIONS",
            entity_type="DPR", entity_id=new_dpr["id"],
            action_type="CREATE", user_id=user["user_id"], project_id=project_id,
            new_value=new_dpr
        )
        return new_dpr

    async def submit_dpr(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        """Fixed CR-20: Integrated StateMachine for DPR submission."""
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr: raise HTTPException(status_code=404, detail="DPR not found")
        
        # TRANSITION VALIDATION
        StateMachine.validate_transition("DPR", dpr.get("status", "Draft"), "Submitted")
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)

        image_count = dpr.get("image_count", 0)
        if image_count < 4:
            raise HTTPException(status_code=400, detail=f"DPR requires minimum 4 images. Current: {image_count}")

        snapshot_data = await self._build_dpr_snapshot_data(dpr)
        
        # PDF Generation
        pdf_bytes = None
        file_name = f"DPR_{dpr_id}.pdf"
        pdf_checksum = None
        file_size_kb = 0
        try:
            pdf_bytes = pdf_generator.generate_pdf(
                project_data=snapshot_data["project"],
                dpr_data={
                    "dpr_date": dpr.get("dpr_date"),
                    "progress_notes": dpr.get("progress_notes", ""),
                    "supervisor_name": user.get("name", "Supervisor"),
                },
                worker_log=snapshot_data["worker_log"],
                images=dpr.get("images", [])
            )
            file_name = pdf_generator.get_filename(snapshot_data["project"].get("project_code", "DPR"), dpr.get("dpr_date"))
            pdf_checksum = hashlib.sha256(pdf_bytes).hexdigest()
            file_size_kb = len(pdf_bytes) / 1024
        except Exception as e:
            logger.error(f"PDF_FAILURE: {e}")

        # Create immutable snapshot
        snapshot = await self.snapshot_service.create_snapshot(
            entity_type="DPR", entity_id=dpr_id, data=snapshot_data,
            organisation_id=user["organisation_id"], pdf_bytes=pdf_bytes, user_id=user["user_id"]
        )

        update_data = {
            "status": "Submitted",
            "locked_flag": True,
            "locked_snapshot_version": snapshot.get("version", 1),
            "submitted_at": ts_now(),
            "updated_at": ts_now(),
            "file_name": file_name,
            "file_size_kb": round(file_size_kb, 2),
            "pdf_checksum": pdf_checksum
        }
        
        await self.dpr_repo.update(dpr_id, update_data)
        return {"status": "Submitted", "snapshot_version": snapshot.get("version"), "file_name": file_name}

    async def approve_dpr(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        """Fixed CR-20: Integrated StateMachine for DPR approval."""
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr: raise HTTPException(status_code=404, detail="DPR not found")
        
        StateMachine.validate_transition("DPR", dpr.get("status", "Draft"), "Approved")
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)
        await self.permission_checker.check_admin_role(user)

        update_data = {
            "status": "Approved",
            "approved_by": user["user_id"],
            "approved_at": ts_now(),
            "updated_at": ts_now()
        }
        
        result = await self.dpr_repo.update(dpr_id, update_data)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="SITE_OPERATIONS",
            entity_type="DPR", entity_id=dpr_id,
            action_type="APPROVE", user_id=user["user_id"], project_id=dpr["project_id"],
            new_value=update_data
        )
        return result

    async def reject_dpr(self, user: dict, dpr_id: str, reason: str) -> Dict[str, Any]:
        """Fixed CR-20: Integrated StateMachine for DPR rejection."""
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr: raise HTTPException(status_code=404, detail="DPR not found")
        
        StateMachine.validate_transition("DPR", dpr.get("status", "Draft"), "Rejected")
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)
        await self.permission_checker.check_admin_role(user)

        update_data = {
            "status": "Rejected",
            "rejection_reason": reason,
            "rejected_by": user["user_id"],
            "rejected_at": ts_now(),
            "locked_flag": False, # UNLOCK on rejection for editing
            "updated_at": ts_now()
        }
        
        result = await self.dpr_repo.update(dpr_id, update_data)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="SITE_OPERATIONS",
            entity_type="DPR", entity_id=dpr_id,
            action_type="REJECT", user_id=user["user_id"], project_id=dpr["project_id"],
            new_value=update_data
        )
        return result

    async def list_site_logs(self, user: dict, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        return await self.worker_log_repo.list({
            "project_id": project_id, "organisation_id": user["organisation_id"]
        }, limit=limit, sort=[("date", -1)])

    async def list_project_dprs(self, user: dict, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        return await self.dpr_repo.list({
            "project_id": project_id, "organisation_id": user["organisation_id"]
        }, limit=limit, sort=[("date", -1)])

    async def get_dpr_detail(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr: raise HTTPException(status_code=404, detail="DPR not found")
        await self.permission_checker.check_project_access(user, dpr["project_id"])
        return await self._enrich_with_user_names(dpr, ["approved_by", "rejected_by", "supervisor_id"])

    async def list_project_attendance(self, user: dict, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        return await self.attendance_repo.list({
            "project_id": project_id, "organisation_id": user["organisation_id"]
        }, limit=limit, sort=[("check_in_time", -1)])

    async def list_project_voice_logs(self, user: dict, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        logs = await self.voice_log_repo.list({"project_id": project_id}, limit=limit, sort=[("created_at", -1)])
        for log in logs: await self._enrich_with_user_names(log, ["supervisor_id"])
        return logs

    async def record_attendance(self, user: dict, project_id: str, attendance_data: List[dict]) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        results = []
        for entry in attendance_data:
            entry.update({"project_id": project_id, "organisation_id": user["organisation_id"], "recorded_by": user["user_id"]})
            res = await self.attendance_repo.create(entry)
            results.append(res)
        return {"status": "success", "count": len(results)}

    async def add_dpr_image(self, user: dict, dpr_id: str, image_data: DPRImage) -> Dict[str, Any]:
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr: raise HTTPException(status_code=404, detail="DPR not found")
        
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)
        # Point 87: Data Freeze check
        StateMachine.check_modification_allowed("DPR", dpr.get("status", "Draft"))

        compressed_data = image_data.image_data
        estimated_size_kb = len(compressed_data) * 0.75 / 1024

        image_doc = {
            "image_id": str(ObjectId()), "image_data": compressed_data, "caption": image_data.caption,
            "activity_code": image_data.activity_code, "aspect_ratio": "9:16", "size_kb": estimated_size_kb,
            "uploaded_by": user["user_id"], "uploaded_at": ts_now()
        }

        await self.dpr_repo.update(dpr_id, {
            "$push": {"images": image_doc}, "$inc": {"image_count": 1}, "$set": {"updated_at": ts_now()}
        })
        return {"image_id": image_doc["image_id"], "status": "added", "message": "Image added to DPR"}

    async def update_image_caption(self, user: dict, dpr_id: str, image_id: str, caption: str) -> Dict[str, Any]:
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr: raise HTTPException(status_code=404, detail="DPR not found")
        
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)
        StateMachine.check_modification_allowed("DPR", dpr.get("status", "Draft"))

        result = await self.db.dpr.update_one(
            {"_id": ObjectId(dpr_id), "images.image_id": image_id},
            {"$set": {"images.$.caption": caption, "updated_at": ts_now()}}
        )
        if result.modified_count == 0: raise HTTPException(status_code=404, detail="Image not found in DPR")
        return {"status": "updated", "message": "Caption updated successfully"}

    async def verify_attendance(self, user: dict, log_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        existing = await self.attendance_repo.get(log_id)
        if not existing: raise HTTPException(status_code=404, detail="Attendance record not found")
        
        await self.permission_checker.check_project_access(user, existing["project_id"], require_write=True)
        update_data = {"verified_by_admin": True, "verified_at": ts_now(), "verified_user_id": user["user_id"]}
        await self.attendance_repo.update(log_id, update_data)
        return {"status": "verified"}

    async def list_site_overheads(self, user: dict, project_id: str) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        return await self.site_overhead_repo.list({"project_id": project_id})

    async def create_site_overhead(self, user: dict, overhead_data: SiteOverheadCreate) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, overhead_data.project_id, require_write=True)
        await self.permission_checker.check_admin_role(user)

        doc = overhead_data.model_dump()
        doc.update({"organisation_id": user["organisation_id"], "created_by": user["user_id"], "created_at": ts_now()})
        result = await self.site_overhead_repo.create(doc)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="SITE_OPERATIONS",
            entity_type="SITE_OVERHEAD", entity_id=result["id"],
            action_type="CREATE", user_id=user["user_id"], project_id=overhead_data.project_id,
            new_value=doc
        )
        return result

    async def create_worker_log(self, user: dict, log_data: WorkersDailyLogCreate) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, log_data.project_id, require_write=True)
        
        existing = await self.worker_log_repo.find_one({
            "project_id": log_data.project_id, "date": log_data.date, "supervisor_id": user["user_id"]
        })

        # Totals computation
        total_workers = sum(e.workers_count for e in log_data.entries) if log_data.entries else len(log_data.workers or [])
        total_hours = sum(w.hours_worked for w in log_data.workers) if log_data.workers else 0

        log_dict = log_data.model_dump()
        log_dict.update({
            "total_workers": log_data.total_workers or total_workers,
            "total_hours": total_hours, "status": "Submitted", "updated_at": ts_now()
        })

        if existing:
            return await self.worker_log_repo.update(existing["id"], log_dict)

        log_dict.update({
            "organisation_id": user["organisation_id"], "supervisor_id": user["user_id"],
            "supervisor_name": user.get("name") or user.get("email", "").split("@")[0],
            "created_at": ts_now()
        })
        return await self.worker_log_repo.create(log_dict)

    async def _build_dpr_snapshot_data(self, dpr: dict) -> Dict[str, Any]:
        project = await self.db.projects.find_one({"project_id": dpr.get("project_id")})
        from app.core.utils import serialize_doc
        project = serialize_doc(project)
        
        dpr_date = dpr.get("dpr_date")
        date_str = dpr_date.strftime("%Y-%m-%d") if isinstance(dpr_date, datetime) else str(dpr_date).split("T")[0]

        worker_log = await self.worker_log_repo.find_one({"project_id": dpr.get("project_id"), "date": date_str})
        
        return {
            "dpr": dpr, "project": project, "worker_log": worker_log,
            "snapshot_timestamp": ts_now().isoformat()
        }
