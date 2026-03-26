from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
import logging

from app.schemas.financial import PaymentCertificate, PaymentCertificateCreate
from app.repositories.financial_repo import PCRepository
from app.repositories.project_repo import ProjectRepository
from app.core.utils import serialize_doc
from app.core.financial_utils import to_d128, to_decimal

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db, audit_service, financial_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.financial_service = financial_service
        self.permission_checker = permission_checker
        self.pc_repo = PCRepository(db)
        self.project_repo = ProjectRepository(db)
        from app.repositories.financial_repo import SequenceRepository
        self.seq_repo = SequenceRepository(db)

    async def list_payment_certificates(self, user: dict, project_id: str, limit: int, cursor: Optional[str]) -> Dict[str, Any]:
        # Check project access
        project = await self.project_repo.get_by_id(project_id, organisation_id=user["organisation_id"])
        if not project:
            # Fallback for internal project_id vs _id
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
            elif isinstance(ts, str):
                next_cursor = ts

        return {
            "items": docs,
            "next_cursor": next_cursor
        }

    async def create_payment_certificate(self, user: dict, pc_data: PaymentCertificateCreate) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        idempotency_key = pc_data.idempotency_key
        project_id = pc_data.project_id
        
        # Security: Check project access
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        
        # Validate financial integrity (Parity with tech arch §6.4)
        await self.financial_service.validate_financial_document("PAYMENT_CERTIFICATE", pc_data.dict(), project_id)

        from app.db.mongodb import db_manager
        from decimal import Decimal
        from bson import Decimal128

        async with db_manager.transaction_session() as session:
            # 1. Idempotency
            if idempotency_key:
                from app.core.idempotency import get_recorded_operation
                recorded = await get_recorded_operation(self.db, session, idempotency_key)
                if recorded:
                    return recorded

            # 2. Calculate totals using utility
            subtotal = Decimal("0.0")
            line_items_bson = []
            for item in pc_data.line_items:
                qty = Decimal(str(item.qty))
                rate = Decimal(str(item.rate))
                item_total = self.financial_service.round_half_up(qty * rate)
                item.total = item_total
                subtotal += item_total
                line_items_bson.append(db_manager.to_bson(item.dict()))
            
            project = await self.project_repo.get_by_id(project_id, organisation_id=organisation_id, session=session)
            cgst_pct = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_pct = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")
            
            from app.core.financial_utils import calculate_pc_financials
            fin = calculate_pc_financials(
                pc_value=subtotal,
                retention_pct=Decimal(str(pc_data.retention_percent or 0)),
                cgst_pct=cgst_pct,
                sgst_pct=sgst_pct
            )

            # 3. Generate Ref
            seq_val = await self.seq_repo.get_next_sequence(f"pc_seq_{organisation_id}", session=session)
            pc_ref = f"PC-{seq_val:04d}"

            # 4. Save
            pc_dict = pc_data.dict()
            pc_dict.update({
                "organisation_id": organisation_id,
                "pc_ref": pc_ref,
                "subtotal": to_d128(fin["subtotal"]),
                "retention_amount": to_d128(fin["retention_amount"]),
                "total_after_retention": to_d128(fin["total_after_retention"]),
                "cgst": to_d128(fin["cgst"]),
                "sgst": to_d128(fin["sgst"]),
                "grand_total": to_d128(fin["grand_total"]),
                "status": "Draft",
                "line_items": line_items_bson,
                "version": 1,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })

            new_pc = await self.pc_repo.create(pc_dict, session=session)

            # 5. Idempotency Record
            if idempotency_key:
                from app.core.idempotency import record_operation
                await record_operation(self.db, session, idempotency_key, "PAYMENT_CERTIFICATE", response_payload=new_pc)

            # 6. Audit
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=new_pc["id"],
                action_type="CREATE",
                user_id=user["user_id"],
                project_id=project_id,
                new_value=new_pc,
                session=session
            )

            return new_pc

    async def close_payment_certificate(self, user: dict, pc_id: str) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        from app.db.mongodb import db_manager
        from decimal import Decimal
        from bson import ObjectId, Decimal128

        async with db_manager.transaction_session() as session:
            pc = await self.pc_repo.get_by_id(pc_id, organisation_id=organisation_id, session=session)
            if not pc:
                raise HTTPException(status_code=404, detail="Payment Certificate not found")
            
            # Security: Check project access
            await self.permission_checker.check_project_access(user, pc["project_id"], require_write=True)
            
            if pc["status"] == "Closed":
                raise HTTPException(status_code=400, detail="Already closed")

            grand_total = Decimal(str(pc["grand_total"]))
            retention_amount = Decimal(str(pc["retention_amount"]))
            project_id = pc["project_id"]
            pc_type = pc.get("pc_type", "WO_LINKED")

            # 1. Update status
            await self.pc_repo.update_one(
                {"_id": ObjectId(pc_id)},
                {"$set": {"status": "Closed", "closed_at": datetime.now(timezone.utc)}},
                session=session
            )

            # 2. Vendor Ledger Update (Spec §4.4)
            if pc_type == "WO_LINKED" and pc.get("vendor_id"):
                await self.db.vendors.update_one(
                    {"_id": ObjectId(pc["vendor_id"])},
                    {"$inc": {
                        "total_payable": to_d128(-grand_total),
                        "retention_held": to_d128(-retention_amount)
                    }},
                    session=session
                )

            # 3. Liquidity Model Update (Spec §5.2)
            if pc_type == "PETTY_OVH":
                fund_alloc = await self.db.fund_allocations.find_one({"project_id": project_id}, session=session)
                if fund_alloc:
                    new_received = Decimal(str(fund_alloc.get("allocation_received", 0))) + grand_total
                    new_cash = Decimal(str(fund_alloc.get("cash_in_hand", 0))) + grand_total
                    await self.db.fund_allocations.update_one(
                        {"_id": fund_alloc["_id"]},
                        {"$set": {
                            "allocation_received": to_d128(new_received),
                            "cash_in_hand": to_d128(new_cash),
                            "last_pc_closed_date": datetime.now(timezone.utc)
                        }},
                        session=session
                    )
                    await self.financial_service.recalculate_master_budget(project_id, session=session)

            # 4. Audit
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=pc_id,
                action_type="CLOSE",
                user_id=user["user_id"],
                project_id=project_id,
                new_value=pc,
                session=session
            )
            return {"status": "success", "message": "PC closed and financials updated"}
