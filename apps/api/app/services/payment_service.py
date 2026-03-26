from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.schemas.financial import PaymentCertificate, PaymentCertificateCreate
from app.core.utils import serialize_doc

class PaymentService:
    def __init__(self, db, audit_service):
        self.db = db
        self.audit_service = audit_service

    async def list_payment_certificates(self, user: dict, project_id: str, limit: int, cursor: Optional[str]) -> Dict[str, Any]:
        # Check project access
        project = await self.db.projects.find_one({"_id": ObjectId(project_id), "organisation_id": user["organisation_id"]})
        if not project:
            project = await self.db.projects.find_one({"project_id": project_id, "organisation_id": user["organisation_id"]})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
        if cursor:
            try:
                parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
                query["created_at"] = {"$lt": parsed_cursor}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid cursor format")

        cursor_obj = self.db.payment_certificates.find(query).sort("created_at", -1).limit(limit)
        docs = await cursor_obj.to_list(length=limit)

        next_cursor = None
        if len(docs) == limit:
            last_doc = docs[-1]
            ts = last_doc.get("created_at")
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()

        return {
            "items": [serialize_doc(c) for c in docs],
            "next_cursor": next_cursor
        }

    async def create_payment_certificate(self, user: dict, pc_data: PaymentCertificateCreate) -> Dict[str, Any]:
        pc_dict = pc_data.dict()
        pc_dict["organisation_id"] = user["organisation_id"]
        pc_dict["created_at"] = datetime.now(timezone.utc)
        pc_dict["status"] = "Draft"

        result = await self.db.payment_certificates.insert_one(pc_dict)
        pc_id = str(result.inserted_id)

        # Audit
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="PAYMENT_CERTIFICATES",
            entity_type="PAYMENT_CERTIFICATE",
            entity_id=pc_id,
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=pc_data.project_id,
            new_value={"total_amount": pc_data.total_amount, "vendor": pc_data.vendor_name}
        )
        
        pc_dict["_id"] = result.inserted_id
        return serialize_doc(pc_dict)
