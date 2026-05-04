import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.core.pdf_service import pdf_generator
from app.core.time import now as ts_now
from app.core.utils import serialize_doc

# Note: UserRepository still in Identity context
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.shared.domain.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.modules.shared.domain.state_machine import StateMachine

from ..domain.models import DailyProgressReport, WorkerLog
from ..infrastructure.repository import (
    AttendanceRepository,
    DPRRepository,
    SiteOverheadRepository,
    VoiceLogRepository,
    WorkerLogRepository,
)
from ..schemas.dto import (
    DPRImage,
    SiteOverheadCreate,
    WorkersDailyLogCreate,
)

logger = logging.getLogger(__name__)


class SiteService:
    """
    Sovereign Site Operations Orchestrator.
    Enforces DPR status transitions via StateMachine and manages field data.
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
            try:
                user_id = doc.get(field)
                if user_id:
                    u = await self.user_repo.get_by_id(user_id)
                    if u:
                        doc[f"{field}_name"] = (
                            u.get("name")
                            or u.get("full_name")
                            or u.get("email", "").split("@")[0]
                        )
                    else:
                        doc[f"{field}_name"] = "Unknown"
                else:
                    doc[f"{field}_name"] = "N/A"
            except Exception as e:
                logger.warning(f"Failed to enrich user name for field {field}: {e}")
        return doc

    async def create_dpr(
        self, user: dict, project_id: str, dpr_data: dict
    ) -> Dict[str, Any]:
        """Create a daily progress report with immutable snapshot requirements."""
        await self.permission_checker.check_project_access(
            user, project_id, require_write=True
        )

        dpr_date = dpr_data.get("dpr_date") or ts_now()
        existing = await self.dpr_repo.find_one(
            {"project_id": project_id, "dpr_date": dpr_date}
        )

        if existing:
            return {
                "exists": True,
                "dpr_id": str(existing["id"]),
                "message": "DPR already exists for this date",
            }

        dpr_doc = {
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "supervisor_id": user["user_id"],
            "dpr_date": dpr_date,
            "progress_notes": dpr_data.get("progress_notes"),
            "weather_conditions": dpr_data.get("weather_conditions", "Normal"),
            "status": "Draft",
            "image_count": 0,
            "images": [],
            "created_at": ts_now(),
            "updated_at": ts_now(),
            "version": 1,
        }

        new_dpr = await self.dpr_repo.create(dpr_doc)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="DPR",
            entity_id=new_dpr["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=project_id,
            new_value=new_dpr,
        )
        return new_dpr

    async def submit_dpr(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        """Finalize DPR, generate PDF and create immutable snapshot."""
        dpr = await self.dpr_repo.get_by_id(dpr_id)
        if not dpr:
            raise NotFoundError("DPR", dpr_id)

        dpr_model = DailyProgressReport(dpr)
        dpr_model.validate_for_submission()

        snapshot_data = await self._build_dpr_snapshot_data(dpr)

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
                images=dpr.get("images", []),
            )
            file_name = pdf_generator.get_filename(
                snapshot_data["project"].get("project_code", "DPR"), dpr.get("dpr_date")
            )
            pdf_checksum = hashlib.sha256(pdf_bytes).hexdigest()
            file_size_kb = len(pdf_bytes) / 1024
        except Exception as e:
            logger.error(f"PDF_FAILURE: {e}")

        snapshot = await self.snapshot_service.create_snapshot(
            entity_type="DPR",
            entity_id=dpr_id,
            data=snapshot_data,
            organisation_id=user["organisation_id"],
            user_id=user["user_id"],
        )

        update_data = {
            "status": "Submitted",
            "locked_flag": True,
            "locked_snapshot_version": snapshot.get("version", 1),
            "submitted_at": ts_now(),
            "updated_at": ts_now(),
            "file_name": file_name,
            "file_size_kb": round(file_size_kb, 2),
            "pdf_checksum": pdf_checksum,
        }

        await self.dpr_repo.update(dpr_id, update_data)

        # Return PDF data as base64 for mobile apps to download/share immediately
        import base64
        return {
            "status": "Submitted",
            "snapshot_version": snapshot.get("version"),
            "file_name": file_name,
            "pdf_data": base64.b64encode(pdf_bytes).decode('utf-8') if pdf_bytes else None
        }

    async def approve_dpr(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        """Admin approval of a submitted DPR."""
        dpr = await self.dpr_repo.get_by_id(dpr_id)
        if not dpr:
            raise NotFoundError("DPR", dpr_id)

        StateMachine.validate_transition("DPR", dpr.get("status", "Draft"), "Approved")
        await self.permission_checker.check_project_access(
            user, dpr["project_id"], require_write=True
        )
        await self.permission_checker.check_admin_role(user)

        update_data = {
            "status": "Approved",
            "approved_by": user["user_id"],
            "approved_at": ts_now(),
            "updated_at": ts_now(),
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
            new_value=update_data,
        )
        return result

    async def reject_dpr(self, user: dict, dpr_id: str, reason: str) -> Dict[str, Any]:
        """Admin rejection of a submitted DPR (unlocks for editing)."""
        dpr = await self.dpr_repo.get_by_id(dpr_id)
        if not dpr:
            raise NotFoundError("DPR", dpr_id)

        StateMachine.validate_transition("DPR", dpr.get("status", "Draft"), "Rejected")
        await self.permission_checker.check_project_access(
            user, dpr["project_id"], require_write=True
        )
        await self.permission_checker.check_admin_role(user)

        update_data = {
            "status": "Rejected",
            "rejection_reason": reason,
            "rejected_by": user["user_id"],
            "rejected_at": ts_now(),
            "locked_flag": False,
            "updated_at": ts_now(),
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
            new_value=update_data,
        )
        return result

    async def delete_dpr(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        """Delete a DPR draft."""
        dpr = await self.dpr_repo.get_by_id(dpr_id)
        if not dpr:
            raise NotFoundError("DPR", dpr_id)

        await self.permission_checker.check_project_access(
            user, dpr["project_id"], require_write=True
        )
        if dpr.get("status") not in ["Draft", "Rejected"]:
            raise ValidationError(f"Cannot delete DPR in status {dpr.get('status')}")

        await self.dpr_repo.delete_by_id(dpr_id)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="DPR",
            entity_id=dpr_id,
            action_type="DELETE",
            user_id=user["user_id"],
            project_id=dpr["project_id"],
            old_value=dpr,
        )
        return {"status": "deleted"}

    async def list_site_logs(
        self, user: dict, project_id: str, limit: int = 100, filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Fetch multiple worker logs for a project with user name enrichment and filtering."""
        await self.permission_checker.check_project_access(user, project_id)
        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}

        if filters:
            if filters.get("date"):
                query["date"] = filters["date"]
            elif filters.get("date_range"):
                start, end = filters["date_range"]
                query["date"] = {"$gte": start, "$lte": end}

            if filters.get("vendor_id"):
                query["entries.vendor_id"] = filters["vendor_id"]

        logs = await self.worker_log_repo.list(
            query,
            limit=limit,
            sort=[("date", -1)],
        )
        return [await self._enrich_with_user_names(log, ["supervisor_id"]) for log in logs]

    async def list_project_dprs(
        self, user: dict, project_id: str, limit: int = 100, filters: dict = None
    ) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}

        if filters:
            if filters.get("date_range"):
                start, end = filters["date_range"]
                query["dpr_date"] = {"$gte": start, "$lte": end}

        dprs = await self.dpr_repo.list(
            query,
            limit=limit,
            sort=[("dpr_date", -1)],
        )

        # Map 'images' to 'photos' for Web/Mobile Parity in List View (BUG-02)
        # and enrich with user names (BUG-11)
        enriched_dprs = []
        for dpr in dprs:
            images = dpr.get("images", [])
            dpr["photos"] = [img.get("image_data") for img in images if img.get("image_data")]

            # Supervisor name is the primary author in mobile list
            enriched = await self._enrich_with_user_names(dpr, ["supervisor_id", "created_by"])
            enriched_dprs.append(enriched)

        return enriched_dprs

    async def get_dpr_detail(self, user: dict, dpr_id: str) -> Dict[str, Any]:
        """Fetch full DPR details with photo-log mapping and worker counts."""
        try:
            dpr = await self.dpr_repo.get_by_id(dpr_id)
            if not dpr:
                raise NotFoundError("DPR", dpr_id)

            await self.permission_checker.check_project_access(user, dpr["project_id"])

            # 1. Map 'images' (objects) to 'photos' (strings) for Web Parity (BUG-02)
            images = dpr.get("images", [])
            dpr["photos"] = [img.get("image_data") for img in images if img.get("image_data")]

            # 3. Enrich with user names and project name for mobile parity
            dpr = await self._enrich_with_user_names(dpr, ["supervisor_id", "created_by"])
            project = await self.project_repo.get_by_id(dpr["project_id"])
            if project:
                dpr["project_name"] = project.get("project_name")

            # 2. Enrich with related worker data for the same date
            worker_log = await self.worker_log_repo.find_one({
                "project_id": dpr["project_id"],
                "date": dpr.get("dpr_date")
            })
            if worker_log:
                dpr["manpower_count"] = worker_log.get("total_workers", 0)
                dpr["worker_entries"] = worker_log.get("entries", [])

            return await self._enrich_with_user_names(
                dpr, ["approved_by", "rejected_by", "supervisor_id", "created_by"]
            )
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error fetching DPR detail: {e}")
            raise ValidationError(f"Failed to load DPR details: {str(e)}")

    async def get_dpr_pdf(self, user: dict, dpr_id: str) -> bytes:
        """Generate/Retrieve PDF for a DPR."""
        try:
            dpr = await self.dpr_repo.get_by_id(dpr_id)
            if not dpr:
                raise NotFoundError("DPR", dpr_id)

            await self.permission_checker.check_project_access(user, dpr["project_id"])

            snapshot_data = await self._build_dpr_snapshot_data(dpr)

            pdf_bytes = pdf_generator.generate_pdf(
                project_data=snapshot_data["project"],
                dpr_data={
                    "dpr_date": dpr.get("dpr_date"),
                    "progress_notes": dpr.get("progress_notes", ""),
                    "supervisor_name": dpr.get("supervisor_id_name", "Supervisor"),
                },
                worker_log=snapshot_data["worker_log"],
                images=dpr.get("images", []),
            )
            if not pdf_bytes:
                raise ValidationError("Failed to generate PDF content")
            return pdf_bytes
        except Exception as e:
            logger.error(f"PDF_GENERATION_FAILURE: {e}")
            raise ValidationError(f"Failed to generate DPR PDF: {str(e)}")

    async def list_project_attendance(
        self, user: dict, project_id: str, limit: int = 100, filters: dict = None
    ) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}

        if filters:
            if filters.get("date"):
                query["date"] = filters["date"]
            if filters.get("date_range"):
                start, end = filters["date_range"]
                # Filter by the 'date' field which is YYYY-MM-DD
                query["date"] = {"$gte": start, "$lte": end}
            if filters.get("search"):
                # Rough search by user name (if stored in record)
                query["user_name"] = {"$regex": filters["search"], "$options": "i"}

        records = await self.attendance_repo.list(
            query, limit=limit, sort=[("date", -1), ("check_in_timestamp", -1)]
        )

        # Enrich with user names for mobile parity (BUG-11)
        # We map supervisor_id to supervisor_name for mobile UI compatibility
        enriched = []
        for rec in records:
            e = await self._enrich_with_user_names(rec, ["supervisor_id", "user_id"])
            # Ensure supervisor_name is populated for mobile UI fallback
            if "supervisor_id_name" in e:
                e["supervisor_name"] = e["supervisor_id_name"]
            elif "user_id_name" in e:
                e["supervisor_name"] = e["user_id_name"]
            enriched.append(e)

        return enriched

    async def get_today_attendance(
        self, user: dict, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Check if supervisor has checked in today for this project."""
        await self.permission_checker.check_project_access(user, project_id)
        today = ts_now().strftime("%Y-%m-%d")

        # Search for record by supervisor, project and date prefix
        query = {
            "project_id": project_id,
            "supervisor_id": user["user_id"],
            "date": today,
        }
        record = await self.attendance_repo.find_one(query)
        if record:
            return await self._enrich_with_user_names(record, ["supervisor_id"])
        return None

    async def list_project_voice_logs(
        self, user: dict, project_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        logs = await self.voice_log_repo.list(
            {"project_id": project_id}, limit=limit, sort=[("created_at", -1)]
        )
        for log in logs:
            await self._enrich_with_user_names(log, ["supervisor_id"])
        return logs

    async def create_voice_log(self, user: dict, log_data: dict) -> Dict[str, Any]:
        project_id = log_data.get("project_id")
        if not project_id:
            raise ValidationError("project_id is required")
        await self.permission_checker.check_project_access(
            user, project_id, require_write=True
        )

        doc = {
            "project_id": project_id,
            "supervisor_id": user["user_id"],
            "transcription": log_data.get("transcription", ""),
            "audio_url": log_data.get("audio_url", ""),
            "created_at": ts_now(),
        }
        return await self.voice_log_repo.create(doc)

    async def record_attendance(
        self, user: dict, project_id: str, attendance_data: List[dict]
    ) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(
            user, project_id, require_write=True
        )
        results = []
        for entry in attendance_data:
            entry.update(
                {
                    "project_id": project_id,
                    "organisation_id": user["organisation_id"],
                    "recorded_by": user["user_id"],
                }
            )
            res = await self.attendance_repo.create(entry)
            results.append(res)
        return {"status": "success", "count": len(results)}

    async def check_in(self, user: dict, project_id: str, data: dict) -> Dict[str, Any]:
        """Record current supervisor check-in."""
        await self.permission_checker.check_project_access(
            user, project_id, require_write=True
        )

        today = ts_now().strftime("%Y-%m-%d")
        existing = await self.attendance_repo.find_one(
            {"project_id": project_id, "supervisor_id": user["user_id"], "date": today}
        )

        if existing:
            raise ValidationError(f"Already checked in today at {existing.get('check_in_time')}")

        doc = {
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "supervisor_id": user["user_id"],
            "date": today,
            "check_in_time": ts_now().strftime("%I:%M %p"),
            "check_in_timestamp": ts_now(),
            "gps_lat": data.get("gps_lat"),
            "gps_long": data.get("gps_long"),
            "selfie_image_id": data.get("selfie_image_id"),
            "status": "checked_in",
            "verified_by_admin": False,
            "created_at": ts_now(),
        }

        return await self.attendance_repo.create(doc)

    async def check_out(self, user: dict, project_id: str, data: dict) -> Dict[str, Any]:
        """Record current supervisor check-out."""
        await self.permission_checker.check_project_access(
            user, project_id, require_write=True
        )

        today = ts_now().strftime("%Y-%m-%d")
        existing = await self.attendance_repo.find_one(
            {"project_id": project_id, "supervisor_id": user["user_id"], "date": today}
        )

        if not existing:
            raise ValidationError("No check-in record found for today")

        if existing.get("status") == "checked_out":
            raise ValidationError("Already checked out today")

        out_time = ts_now()
        in_time = existing.get("check_in_timestamp")

        total_hours = 0
        if in_time:
            # Handle both datetime objects and string timestamps if any
            if isinstance(in_time, str):
                from dateutil import parser
                in_time = parser.parse(in_time)

            if in_time.tzinfo is None:
                in_time = in_time.replace(tzinfo=timezone.utc)

            delta = out_time - in_time
            total_hours = round(delta.total_seconds() / 3600.0, 2)

        update_data = {
            "check_out_time": out_time.strftime("%I:%M %p"),
            "check_out_timestamp": out_time,
            "total_hours": total_hours,
            "status": "checked_out",
            "updated_at": ts_now(),
        }

        result = await self.attendance_repo.update(existing["id"], update_data)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="ATTENDANCE",
            entity_id=existing["id"],
            action_type="CHECK_OUT",
            user_id=user["user_id"],
            project_id=project_id,
            new_value=update_data
        )
        return result

    async def add_dpr_image(
        self, user: dict, dpr_id: str, image_data: DPRImage
    ) -> Dict[str, Any]:
        dpr = await self.dpr_repo.get_by_id(dpr_id)
        if not dpr:
            raise NotFoundError("DPR", dpr_id)

        await self.permission_checker.check_project_access(
            user, dpr["project_id"], require_write=True
        )
        dpr_model = DailyProgressReport(dpr)
        dpr_model.can_modify()

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
            "uploaded_at": ts_now(),
        }

        await self.dpr_repo.update_one(
            {"_id": ObjectId(dpr_id)},
            {
                "$push": {"images": image_doc},
                "$inc": {"image_count": 1},
                "$set": {"updated_at": ts_now()},
            },
        )
        return {
            "image_id": image_doc["image_id"],
            "status": "added",
            "message": "Image added to DPR",
        }

    async def update_image_caption(
        self, user: dict, dpr_id: str, image_id: str, caption: str
    ) -> Dict[str, Any]:
        dpr = await self.dpr_repo.get_by_id(dpr_id)
        if not dpr:
            raise NotFoundError("DPR", dpr_id)

        await self.permission_checker.check_project_access(
            user, dpr["project_id"], require_write=True
        )
        dpr_model = DailyProgressReport(dpr)
        dpr_model.can_modify()

        result = await self.db.dpr.update_one(
            {"_id": ObjectId(dpr_id), "images.image_id": image_id},
            {"$set": {"images.$.caption": caption, "updated_at": ts_now()}},
        )
        if result.modified_count == 0:
            raise NotFoundError("DPR Image", image_id)
        return {"status": "updated", "message": "Caption updated successfully"}

    async def verify_attendance(self, user: dict, log_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_admin_role(user)
        existing = await self.attendance_repo.get_by_id(log_id)
        if not existing:
            raise NotFoundError("Attendance record", log_id)

        await self.permission_checker.check_project_access(
            user, existing["project_id"], require_write=True
        )
        update_data = {
            "verified_by_admin": True,
            "verified_at": ts_now(),
            "verified_user_id": user["user_id"],
        }
        await self.attendance_repo.update(log_id, update_data)
        return {"status": "verified"}

    async def list_site_overheads(
        self, user: dict, project_id: str
    ) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        return await self.site_overhead_repo.list({"project_id": project_id})

    async def update_site_overhead(
        self, user: dict, entry_id: str, overhead_data: Any  # SiteOverheadUpdate
    ) -> Dict[str, Any]:
        """Update site overhead with optimistic locking."""
        existing = await self.site_overhead_repo.get_by_id(entry_id)
        if not existing:
            raise NotFoundError("Site overhead", entry_id)

        await self.permission_checker.check_project_access(
            user, existing.get("project_id"), require_write=True
        )
        await self.permission_checker.check_admin_role(user)

        # Optimistic Locking check (BUG-31 context)
        incoming_version = getattr(overhead_data, "version", None)
        if incoming_version is not None and incoming_version != existing.get("version", 1):
            from app.modules.shared.domain.exceptions import ValidationError
            raise ValidationError(f"Version conflict. Expected {existing.get('version')}, got {incoming_version}")

        update_dict = {k: v for k, v in overhead_data.model_dump().items() if v is not None}
        update_dict["updated_at"] = ts_now()
        update_dict["version"] = existing.get("version", 1) + 1

        result = await self.site_overhead_repo.update(entry_id, update_dict)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="SITE_OVERHEAD",
            entity_id=entry_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            project_id=existing.get("project_id"),
            old_value=existing,
            new_value=result,
        )
        return result

    async def delete_dpr_image(self, user: dict, dpr_id: str, image_id: str) -> Dict[str, Any]:
        """Remove an image from a DPR."""
        dpr = await self.dpr_repo.get_by_id(dpr_id)
        if not dpr:
            raise NotFoundError("DPR", dpr_id)

        await self.permission_checker.check_project_access(
            user, dpr["project_id"], require_write=True
        )

        # Enforce StateMachine rules
        dpr_model = DailyProgressReport(dpr)
        dpr_model.can_modify()

        # MongoDB $pull operation
        result = await self.dpr_repo.update_one(
            {"_id": ObjectId(dpr_id)},
            {
                "$pull": {"images": {"image_id": image_id}},
                "$inc": {"image_count": -1},
                "$set": {"updated_at": ts_now()}
            }
        )

        if result.modified_count == 0:
            raise NotFoundError("DPR Image", image_id)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="DPR",
            entity_id=dpr_id,
            action_type="DELETE_IMAGE",
            user_id=user["user_id"],
            project_id=dpr["project_id"],
            metadata={"image_id": image_id}
        )

        return {"status": "deleted", "image_id": image_id}

    async def create_site_overhead(
        self, user: dict, overhead_data: SiteOverheadCreate
    ) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(
            user, overhead_data.project_id, require_write=True
        )
        await self.permission_checker.check_admin_role(user)

        doc = overhead_data.model_dump()
        doc.update(
            {
                "organisation_id": user["organisation_id"],
                "created_by": user["user_id"],
                "created_at": ts_now(),
            }
        )
        result = await self.site_overhead_repo.create(doc)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="SITE_OVERHEAD",
            entity_id=result["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=overhead_data.project_id,
            new_value=doc,
        )
        return result

    async def update_worker_log(
        self, user: dict, log_id: str, log_data: Any  # WorkersDailyLogUpdate
    ) -> Dict[str, Any]:
        """Partial update of a worker log."""
        existing = await self.worker_log_repo.get_by_id(log_id)
        if not existing:
            raise NotFoundError("Worker log", log_id)

        await self.permission_checker.check_project_access(
            user, existing.get("project_id"), require_write=True
        )

        update_dict = {k: v for k, v in log_data.model_dump().items() if v is not None}

        # Recalculate totals if entries or workers changed
        if "entries" in update_dict or "workers" in update_dict:
            entries = update_dict.get("entries") or existing.get("entries", [])
            workers = update_dict.get("workers") or existing.get("workers", [])

            # Using model logic to calculate totals
            totals = WorkerLog.calculate_totals(entries, workers)
            update_dict["total_workers"] = totals["total_workers"]
            update_dict["total_hours"] = totals["total_hours"]

        update_dict["updated_at"] = ts_now()

        result = await self.worker_log_repo.update(log_id, update_dict)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="WORKER_LOG",
            entity_id=log_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            project_id=existing.get("project_id"),
            old_value=existing,
            new_value=result,
        )
        return result

    async def create_worker_log(
        self, user: dict, log_data: WorkersDailyLogCreate
    ) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(
            user, log_data.project_id, require_write=True
        )

        existing = await self.worker_log_repo.find_one(
            {
                "project_id": log_data.project_id,
                "date": log_data.date,
                "supervisor_id": user["user_id"],
            }
        )

        totals = WorkerLog.calculate_totals(log_data.entries, log_data.workers)
        total_workers = totals["total_workers"]
        total_hours = totals["total_hours"]

        log_dict = log_data.model_dump()
        log_dict.update(
            {
                "total_workers": int(log_data.total_workers or total_workers),
                "total_hours": float(total_hours),
                "status": "Submitted",
                "updated_at": ts_now(),
            }
        )

        if existing:
            result = await self.worker_log_repo.update(existing["id"], log_dict)
            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="SITE_OPERATIONS",
                entity_type="WORKER_LOG",
                entity_id=str(existing["id"]),
                action_type="UPDATE",
                user_id=user["user_id"],
                project_id=log_data.project_id,
                old_value=existing,
                new_value=result,
            )
            return result

        log_dict.update(
            {
                "organisation_id": user["organisation_id"],
                "supervisor_id": user["user_id"],
                "supervisor_name": user.get("name")
                or user.get("email", "").split("@")[0],
                "created_at": ts_now(),
            }
        )
        result = await self.worker_log_repo.create(log_dict)
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SITE_OPERATIONS",
            entity_type="WORKER_LOG",
            entity_id=result["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=log_data.project_id,
            new_value=result,
        )
        return result

    async def _build_dpr_snapshot_data(self, dpr: dict) -> Dict[str, Any]:
        project_id = dpr.get("project_id")
        project = None

        if project_id:
            # 1. Try finding by _id (standard)
            try:
                query = {"_id": ObjectId(project_id)} if ObjectId.is_valid(project_id) else {"_id": project_id}
                project = await self.db.projects.find_one(query)
            except Exception:
                project = None

            # 2. Fallback to project_id field (legacy/internal)
            if not project:
                project = await self.db.projects.find_one({"project_id": project_id})

        project = serialize_doc(project) or {
            "project_name": "Unknown Project",
            "project_code": "N/A"
        }

        dpr_date = dpr.get("dpr_date")
        date_str = (
            dpr_date.strftime("%Y-%m-%d")
            if isinstance(dpr_date, datetime)
            else str(dpr_date).split("T")[0]
        )

        # Real-time weather integration (Mock for now, but scalable)
        weather = dpr.get("weather_conditions") or "Normal (28°C, Clear)"
        if not dpr.get("weather_conditions"):
            # If not set, we could potentially fetch from a service here
            # For now, we'll keep the default or use a deterministic mock
            pass

        # Ensure project_id is handled consistently in worker log query
        log_query = {"date": date_str}
        if project_id:
            if ObjectId.is_valid(project_id):
                log_query["$or"] = [{"project_id": project_id}, {"project_id": ObjectId(project_id)}]
            else:
                log_query["project_id"] = project_id

        worker_log = await self.worker_log_repo.find_one(log_query)

        return {
            "dpr": {**dpr, "weather_conditions": weather},
            "project": project,
            "worker_log": worker_log,
            "snapshot_timestamp": ts_now().isoformat(),
        }
