from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
import logging
import hashlib
import base64

from app.schemas.site import WorkersDailyLog, WorkersDailyLogCreate, WorkersDailyLogUpdate, DPRImage, SiteOverheadCreate, SiteOverheadUpdate
from app.repositories.site_repo import WorkerLogRepository
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)

from app.repositories.site_repo import WorkerLogRepository, DPRRepository, AttendanceRepository, VoiceLogRepository, SiteOverheadRepository
from app.repositories.user_repo import UserRepository
from app.core.config import settings
from app.core.pdf_service import pdf_generator

class SiteService:
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
                user = await self.user_repo.get_by_user_id(user_id)
                if user:
                    doc[f"{field}_name"] = user.get("name") or user.get("full_name") or user.get("email", "").split("@")[0]
        return doc

    async def create_dpr(self, user: dict, project_id: str, dpr_data: dict) -> Dict[str, Any]:
        """Create a daily progress report with immutable snapshot requirements."""
        # Security Check
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        
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
        
        # Snapshot: Capture immutable state
        await self.snapshot_service.create_snapshot(
            entity_type="DPR",
            entity_id=new_dpr["id"],
            organisation_id=user["organisation_id"],
            user_id=user["user_id"],
            project_id=project_id,
            data=new_dpr
        )

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
        # Security Check
        await self.permission_checker.check_project_access(user, project_id)
        
        return await self.worker_log_repo.list({
            "project_id": project_id,
            "organisation_id": user["organisation_id"]
        }, limit=limit, sort=[("date", -1)])

    async def list_project_dprs(self, user: dict, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        # Security Check
        await self.permission_checker.check_project_access(user, project_id)
        
        return await self.dpr_repo.list({
            "project_id": project_id,
            "organisation_id": user["organisation_id"]
        }, limit=limit, sort=[("date", -1)])

    async def get_dpr_detail(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr:
            raise HTTPException(status_code=404, detail="DPR not found")
        await self.permission_checker.check_project_access(user, dpr["project_id"])
        return await self._enrich_with_user_names(dpr, ["approved_by", "rejected_by", "created_by"])

    async def approve_dpr(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr:
            raise HTTPException(status_code=404, detail="DPR not found")
        
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)
        await self.permission_checker.check_admin_role(user)

        update_data = {
            "status": "APPROVED",
            "approved_by": user["user_id"],
            "approved_at": datetime.now(timezone.utc)
        }
        
        result = await self.dpr_repo.update(dpr_id, update_data)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="DPR",
            entity_id=dpr_id,
            action_type="APPROVE",
            user_id=user["user_id"],
            project_id=dpr["project_id"],
            new_value=update_data
        )
        return result

    async def list_project_attendance(self, user: dict, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.attendance_repo.list({
            "project_id": project_id,
            "organisation_id": user["organisation_id"]
        }, limit=limit, sort=[("check_in_time", -1)])

    async def list_project_voice_logs(self, user: dict, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        logs = await self.voice_log_repo.list({
            "project_id": project_id
        }, limit=limit, sort=[("created_at", -1)])
        
        for log in logs:
            await self._enrich_with_user_names(log, ["supervisor_id"])
        return logs

    async def record_attendance(self, user: dict, project_id: str, attendance_data: List[dict]) -> Dict[str, Any]:
        """Batch record worker attendance."""
        # Security Check
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        
        results = []
        for entry in attendance_data:
            entry["project_id"] = project_id
            entry["organisation_id"] = user["organisation_id"]
            entry["recorded_by"] = user["user_id"]
            res = await self.attendance_repo.create(entry)
            results.append(res)
            
        return {"status": "success", "count": len(results)}

    async def add_dpr_image(self, user: dict, dpr_id: str, image_data: DPRImage) -> Dict[str, Any]:
        """Add an image to a DPR report."""
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr:
            raise HTTPException(status_code=404, detail="DPR not found")
        
        # Security Check
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)
        
        if dpr.get("locked_flag") and user.get("role") != "Admin":
            raise HTTPException(status_code=400, detail="DPR is locked and cannot be modified")

        # Estimate compressed size (base64 is ~33% larger than binary)
        compressed_data = image_data.image_data
        estimated_size_kb = len(compressed_data) * 0.75 / 1024

        image_doc = {
            "image_id": str(ObjectId()),
            "image_data": compressed_data,
            "caption": image_data.caption,
            "activity_code": image_data.activity_code,
            "aspect_ratio": "9:16",
            "size_kb": estimated_size_kb,
            "uploaded_by": user["user_id"],
            "uploaded_at": datetime.now(timezone.utc)
        }

        # Update DPR via Repo
        await self.dpr_repo.update(dpr_id, {
            "$push": {"images": image_doc},
            "$inc": {"image_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        })

        return {
            "image_id": image_doc["image_id"],
            "size_kb": round(estimated_size_kb, 2),
            "status": "added",
            "message": "Image added to DPR"
        }

    async def update_image_caption(self, user: dict, dpr_id: str, image_id: str, caption: str) -> Dict[str, Any]:
        """Update the caption for a specific image in a DPR."""
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr:
            raise HTTPException(status_code=404, detail="DPR not found")
        
        # Security Check
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)
        
        if dpr.get("locked_flag") and user.get("role") != "Admin":
            raise HTTPException(status_code=400, detail="DPR is locked and cannot be modified")

        # Use raw db collection for $ matching update if repo doesn't support it directly
        # or implement a specialized method in DPRRepository
        result = await self.db.dpr.update_one(
            {
                "_id": ObjectId(dpr_id),
                "images.image_id": image_id
            },
            {
                "$set": {
                    "images.$.caption": caption,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Image not found in DPR")

        return {"status": "updated", "message": "Caption updated successfully"}

    async def reject_dpr(self, user: dict, dpr_id: str, reason: str) -> Dict[str, Any]:
        """Reject a DPR report."""
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr:
            raise HTTPException(status_code=404, detail="DPR not found")
        
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)
        await self.permission_checker.check_admin_role(user)

        update_data = {
            "status": "REJECTED",
            "rejection_reason": reason,
            "rejected_by": user["user_id"],
            "rejected_at": datetime.now(timezone.utc)
        }
        
        result = await self.dpr_repo.update(dpr_id, update_data)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="DPR",
            entity_id=dpr_id,
            action_type="REJECT",
            user_id=user["user_id"],
            project_id=dpr["project_id"],
            new_value=update_data
        )
        return result

    async def verify_attendance(self, user: dict, log_id: str) -> Dict[str, Any]:
        """Verify an attendance record."""
        await self.permission_checker.check_admin_role(user)

        existing = await self.attendance_repo.get(log_id)
        if not existing:
             # Fallback check in worker logs repo if needed, but repo only handles one collection.
             # In DDD we should probably have strict separation. 
             # For now let's use attendance_repo.
             raise HTTPException(status_code=404, detail="Attendance record not found")
        
        await self.permission_checker.check_project_access(user, existing["project_id"], require_write=True)

        update_data = {
            "verified_by_admin": True,
            "verified_at": datetime.now(timezone.utc),
            "verified_user_id": user["user_id"]
        }
        
        result = await self.attendance_repo.update(log_id, update_data)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="ATTENDANCE",
            entity_id=log_id,
            action_type="VERIFY",
            user_id=user["user_id"],
            project_id=existing.get("project_id"),
            new_value=update_data
        )
        return {"status": "verified"}

    async def list_site_overheads(self, user: dict, project_id: str) -> List[Dict[str, Any]]:
        """List all site overhead entries for a project."""
        await self.permission_checker.check_project_access(user, project_id)
        return await self.site_overhead_repo.list({"project_id": project_id})

    async def create_site_overhead(self, user: dict, overhead_data: SiteOverheadCreate) -> Dict[str, Any]:
        """Create a new site overhead entry."""
        await self.permission_checker.check_project_access(user, overhead_data.project_id, require_write=True)
        await self.permission_checker.check_admin_role(user)

        doc = overhead_data.model_dump()
        doc["organisation_id"] = user["organisation_id"]
        doc["created_by"] = user["user_id"]
        doc["created_at"] = datetime.now(timezone.utc)

        result = await self.site_overhead_repo.create(doc)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="SITE_OVERHEAD",
            entity_id=result["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=overhead_data.project_id,
            new_value=doc
        )
        return result

    async def update_site_overhead(self, user: dict, entry_id: str, overhead_data: SiteOverheadUpdate) -> Dict[str, Any]:
        """Update a site overhead entry."""
        existing = await self.site_overhead_repo.get(entry_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Site overhead not found")
        
        await self.permission_checker.check_project_access(user, existing["project_id"], require_write=True)
        await self.permission_checker.check_admin_role(user)

        update_data = {k: v for k, v in overhead_data.model_dump().items() if v is not None}
        result = await self.site_overhead_repo.update(entry_id, update_data)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="SITE_OVERHEAD",
            entity_id=entry_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            project_id=existing["project_id"],
            new_value=update_data
        )
        return result

    async def create_worker_log(self, user: dict, log_data: WorkersDailyLogCreate) -> Dict[str, Any]:
        """Business logic for creating/updating a worker log"""
        # Security Check
        await self.permission_checker.check_project_access(user, log_data.project_id, require_write=True)

        # Check if log already exists for this date and project
        existing = await self.worker_log_repo.find_one({
            "project_id": log_data.project_id,
            "date": log_data.date,
            "supervisor_id": user["user_id"]
        })

        # Calculate totals
        if log_data.entries:
            total_workers = sum(e.workers_count for e in log_data.entries)
            entries_data = [e.model_dump() for e in log_data.entries]
        else:
            total_workers = len(log_data.workers) if log_data.workers else 0
            entries_data = []

        total_hours = sum(w.hours_worked for w in log_data.workers) if log_data.workers else 0

        if existing:
            # Update existing log
            update_dict = {
                "entries": entries_data,
                "workers": [w.model_dump() for w in log_data.workers] if log_data.workers else [],
                "total_workers": log_data.total_workers if log_data.total_workers else total_workers,
                "total_hours": total_hours,
                "weather": log_data.weather,
                "site_conditions": log_data.site_conditions,
                "remarks": log_data.remarks,
                "status": "Submitted",
                "updated_at": datetime.now(timezone.utc)
            }
            return await self.worker_log_repo.update(existing["id"], update_dict)

        log_dict = {
            "organisation_id": user["organisation_id"],
            "project_id": log_data.project_id,
            "date": log_data.date,
            "supervisor_id": user["user_id"],
            "supervisor_name": user.get("name") or user.get("email", "").split("@")[0],
            "entries": entries_data,
            "workers": [w.model_dump() for w in log_data.workers] if log_data.workers else [],
            "total_workers": log_data.total_workers if log_data.total_workers else total_workers,
            "total_hours": total_hours,
            "weather": log_data.weather,
            "site_conditions": log_data.site_conditions,
            "remarks": log_data.remarks,
            "status": "Submitted",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        return await self.worker_log_repo.create(log_dict)

    async def update_worker_log(self, user: dict, log_id: str, update_data: WorkersDailyLogUpdate) -> Dict[str, Any]:
        """Business logic for updating a specific worker log"""
        log = await self.worker_log_repo.get(log_id)
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker log not found")
        
        # Security Check
        await self.permission_checker.check_project_access(user, log["project_id"], require_write=True)

        # Prepare update
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        
        if update_data.workers is not None:
            update_dict["workers"] = [w.model_dump() for w in update_data.workers]
            update_dict["total_workers"] = len(update_data.workers)
            update_dict["total_hours"] = sum(w.hours_worked for w in update_data.workers)
        
        if update_data.entries is not None:
             update_dict["entries"] = [e.model_dump() for e in update_data.entries]
             update_dict["total_workers"] = sum(e.workers_count for e in update_data.entries)

        update_dict["updated_at"] = datetime.now(timezone.utc)

        return await self.worker_log_repo.update(log_id, update_dict)

    async def submit_dpr(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        """
        Submit DPR for review.
        - Requires minimum 4 images
        - Generates PDF via SnapshotService/PDFService
        - Creates immutable snapshot
        - Locks DPR
        - Sends notification
        """
        dpr = await self.dpr_repo.get(dpr_id)
        if not dpr:
            raise HTTPException(status_code=404, detail="DPR not found")
        
        await self.permission_checker.check_project_access(user, dpr["project_id"], require_write=True)

        if dpr.get("locked_flag"):
            raise HTTPException(status_code=400, detail="DPR is already submitted")

        image_count = dpr.get("image_count", 0)
        if image_count < 4:
            raise HTTPException(status_code=400, detail=f"DPR requires minimum 4 images. Current: {image_count}")

        # In a real DDD system, PDF generation might be its own service.
        # For now, let's assume we use components from the legacy system if needed, 
        # or just implement the core logic here.
        
        # Build Snapshot (This should be comprehensive)
        snapshot_data = await self._build_dpr_snapshot_data(dpr)
        
        # Prepare data for PDF
        project = snapshot_data["project"]
        worker_log = snapshot_data["worker_log"]
        images = dpr.get("images", [])
        
        dpr_data_for_pdf = {
            "dpr_date": dpr.get("date"),
            "progress_notes": dpr.get("progress_notes", ""),
            "voice_summary": dpr.get("voice_summary", ""),
            "weather_conditions": dpr.get("weather_conditions", "Normal"),
            "supervisor_name": user.get("name", "Supervisor"),
        }

        # Generate PDF
        try:
            pdf_bytes = pdf_generator.generate_pdf(
                project_data=project,
                dpr_data=dpr_data_for_pdf,
                worker_log=worker_log,
                images=images
            )
            file_name = pdf_generator.get_filename(project.get("project_code", "DPR"), dpr_data_for_pdf["dpr_date"])
            pdf_checksum = hashlib.sha256(pdf_bytes).hexdigest()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            file_size_kb = len(pdf_bytes) / 1024
        except Exception as e:
            self.logger.error(f"PDF generation failed: {e}")
            pdf_bytes = None
            pdf_checksum = None
            file_name = f"DPR_{dpr_id}.pdf"
            file_size_kb = 0

        # Create immutable snapshot
        snapshot = await self.snapshot_service.create_snapshot(
            entity_type="DPR",
            entity_id=dpr_id,
            data=snapshot_data,
            organisation_id=user["organisation_id"],
            pdf_bytes=pdf_bytes,
            user_id=user["user_id"]
        )

        # Lock DPR
        update_data = {
            "status": "submitted",
            "locked_flag": True,
            "locked_snapshot_version": snapshot.get("version", 1),
            "submitted_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "pdf_generated": pdf_bytes is not None,
            "file_name": file_name,
            "file_size_kb": round(file_size_kb, 2),
            "pdf_checksum": pdf_checksum
        }
        
        await self.dpr_repo.update(dpr_id, update_data)

        # Notify Admin
        notification_doc = {
            "organisation_id": user["organisation_id"],
            "recipient_role": "admin",
            "title": "New DPR Submitted",
            "message": f"{user.get('name', 'Supervisor')} submitted a DPR for {project.get('project_name', 'Unknown')} on {dpr.get('date')}",
            "notification_type": "dpr_submitted",
            "priority": "normal",
            "reference_type": "dpr",
            "reference_id": dpr_id,
            "project_id": dpr["project_id"],
            "sender_id": user["user_id"],
            "created_at": datetime.now(timezone.utc),
            "is_read": False
        }
        await self.db.notifications.insert_one(notification_doc)

        return {"status": "submitted", "snapshot_version": snapshot.get("version"), "file_name": file_name}

    async def _build_dpr_snapshot_data(self, dpr: dict) -> Dict[str, Any]:
        """Build a complete data structure for the DPR snapshot."""
        # Ported from build_dpr_snapshot in legacy
        project_id = dpr.get("project_id")
        project = await self.project_repo.get_by_id(project_id)
        
        # Get worker log
        dpr_date = dpr.get("date")
        if isinstance(dpr_date, datetime):
            date_str = dpr_date.strftime("%Y-%m-%d")
        else:
            date_str = str(dpr_date).split("T")[0]

        worker_log = await self.worker_log_repo.find_one({"project_id": project_id, "date": date_str})
        
        return {
            "dpr": dpr,
            "project": project,
            "worker_log": worker_log,
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat()
        }
