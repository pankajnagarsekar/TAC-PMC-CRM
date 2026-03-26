from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
import logging

from app.schemas.financial import PaymentCertificate, PaymentCertificateCreate
from app.repositories.financial_repo import PCRepository
from app.repositories.project_repo import ProjectRepository
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db, audit_service):
        self.db = db
        self.audit_service = audit_service
        self.pc_repo = PCRepository(db)
        self.project_repo = ProjectRepository(db)

    async def list_payment_certificates(self, user: dict, project_id: str, limit: int, cursor: Optional[str]) -> Dict[str, Any]:
        # Check project access
        project = await self.project_repo.get_by_id(project_id, organisation_id=user["organisation_id"])
        if not project:
            project = await self.project_repo.find_one({"project_id": project_id, "organisation_id": user["organisation_id"]})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
        if cursor:
            try:
                parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
                query["created_at"] = {"$lt": parsed_cursor}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid cursor format")

        docs = await self.pc_repo.list(query, sort=[("created_at", -1)], limit=limit)

        next_cursor = None
        if len(docs) == limit:
            last_doc = docs[-1]
            ts = last_doc.get("created_at")
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()
            elif isinstance(ts, str): # serialize_doc might have already stringified it
                next_cursor = ts

        return {
            "items": docs,
            "next_cursor": next_cursor
        }

    async def create_payment_certificate(self, user: dict, pc_data: PaymentCertificateCreate) -> Dict[str, Any]:
        pc_dict = pc_data.dict()
        pc_dict["organisation_id"] = user["organisation_id"]
        pc_dict["status"] = "Draft"

        new_pc = await self.pc_repo.create(pc_dict)

        # Audit
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="PAYMENT_CERTIFICATES",
            entity_type="PAYMENT_CERTIFICATE",
            entity_id=new_pc["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=pc_data.project_id,
            new_value=new_pc
        )
        
        return new_pc
