import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from bson import ObjectId, Decimal128
from fastapi import HTTPException

from ..schemas.dto import PaymentCertificate, PaymentCertificateCreate
from ..infrastructure.repository import PCRepository
# Note: Repositories from other contexts
from app.modules.project.infrastructure.repository import ProjectRepository
from app.modules.shared.infrastructure.sequence_repo import SequenceRepository

from app.core.utils import serialize_doc
from app.core.financial_utils import to_d128, to_decimal, calculate_pc_financials
from app.core.uow import UnitOfWork

logger = logging.getLogger(__name__)

class PaymentService:
    """
    Sovereign Payment Orchestrator.
    Enforces atomic transactions via UnitOfWork and manages PC lifecycle.
    """
    def __init__(self, db, audit_service, financial_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.financial_service = financial_service
        self.permission_checker = permission_checker
        self.pc_repo = PCRepository(db)
        self.project_repo = ProjectRepository(db)
        self.seq_repo = SequenceRepository(db)

    async def list_payment_certificates(self, user: dict, project_id: str, limit: int, cursor: Optional[str]) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        
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

        return {"items": docs, "next_cursor": next_cursor}

    async def create_payment_certificate(self, user: dict, pc_data: PaymentCertificateCreate) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        idempotency_key = pc_data.idempotency_key
        project_id = pc_data.project_id
        
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        # Note: financial_service should expose validation
        # await self.financial_service.validate_financial_document("PAYMENT_CERTIFICATE", pc_data.dict(), project_id)

        async with UnitOfWork(self.db) as uow:
            if idempotency_key:
                from app.core.idempotency import get_recorded_operation
                recorded = await get_recorded_operation(self.db, uow.session, idempotency_key)
                if recorded: return recorded

            project = await uow.projects.get_by_id(project_id, organisation_id=organisation_id, session=uow.session)
            cgst_pct = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_pct = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")
            
            subtotal = Decimal("0.0")
            line_items_processed = []
            for item in pc_data.line_items:
                qty = Decimal(str(item.qty))
                rate = Decimal(str(item.rate))
                item_total = to_decimal(round(qty * rate, 2)) # Simple rounding for now
                item.total = item_total
                subtotal += item_total
                item_dict = item.dict()
                item_dict["total"] = to_d128(item_total)
                line_items_processed.append(item_dict)
            
            fin = calculate_pc_financials(
                pc_value=subtotal,
                retention_pct=Decimal(str(pc_data.retention_percent or 0)),
                cgst_pct=cgst_pct,
                sgst_pct=sgst_pct
            )

            # Use modular seq repo
            pc_ref_id = f"pc_seq_{organisation_id}"
            next_seq = await uow.sequences.get_next_sequence(pc_ref_id, session=uow.session)
            pc_ref = f"PC-{next_seq:04d}"

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
                "line_items": line_items_processed,
                "version": 1,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })

            new_pc = await uow.payments.create(pc_dict, session=uow.session)

            if idempotency_key:
                from app.core.idempotency import record_operation
                await record_operation(self.db, uow.session, idempotency_key, "PAYMENT_CERTIFICATE", response_payload=new_pc)

            await self.audit_service.log_action(
                organisation_id=organisation_id, module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE", entity_id=new_pc["id"],
                action_type="CREATE", user_id=user["user_id"], project_id=project_id,
                new_value=new_pc, session=uow.session
            )

            return new_pc

    async def close_payment_certificate(self, user: dict, pc_id: str) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]

        async with UnitOfWork(self.db) as uow:
            pc = await uow.payments.get_by_id(pc_id, organisation_id=organisation_id, session=uow.session)
            if not pc: raise HTTPException(status_code=404, detail="Payment Certificate not found")
            
            await self.permission_checker.check_project_access(user, pc["project_id"], require_write=True)
            if pc["status"] == "Closed": raise HTTPException(status_code=400, detail="Already closed")

            grand_total = Decimal(str(pc["grand_total"]))
            retention_amount = Decimal(str(pc["retention_amount"]))
            project_id = pc["project_id"]
            pc_type = pc.get("pc_type", "WO_LINKED")

            await uow.payments.update(pc_id, {"status": "Closed", "closed_at": datetime.now(timezone.utc)}, session=uow.session)

            if pc_type == "WO_LINKED" and pc.get("vendor_id"):
                await uow.db.vendors.update_one(
                    {"_id": ObjectId(pc["vendor_id"])},
                    {"$inc": {"total_payable": to_d128(-grand_total), "retention_held": to_d128(-retention_amount)}},
                    session=uow.session
                )

            if pc_type == "PETTY_OVH":
                fund_alloc = await uow.fund_allocations.find_one({"project_id": project_id}, session=uow.session)
                if fund_alloc:
                    new_received = to_decimal(fund_alloc.get("allocation_received", 0)) + grand_total
                    new_cash = to_decimal(fund_alloc.get("cash_in_hand", 0)) + grand_total
                    await uow.fund_allocations.update(fund_alloc["id"], {
                        "allocation_received": to_d128(new_received),
                        "cash_in_hand": to_d128(new_cash),
                        "last_pc_closed_date": datetime.now(timezone.utc)
                    }, session=uow.session)
                    
                    await self.financial_service.recalculate_master_budget(project_id, session=uow.session)

            await self.audit_service.log_action(
                organisation_id=organisation_id, module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE", entity_id=pc_id,
                action_type="CLOSE", user_id=user["user_id"], project_id=project_id,
                new_value=pc, session=uow.session
            )
            return {"status": "success", "message": "PC closed and financials updated"}
