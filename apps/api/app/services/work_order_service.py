import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional
from bson import ObjectId, Decimal128
from fastapi import HTTPException

from app.db.mongodb import db_manager
from app.schemas.financial import WorkOrder, WorkOrderCreate, WorkOrderUpdate
from app.repositories.financial_repo import WorkOrderRepository, BudgetRepository, SequenceRepository
from app.repositories.vendor_repo import VendorRepository
from app.repositories.project_repo import ProjectRepository
from app.core.utils import serialize_doc
from app.core.financial_utils import to_d128, to_decimal

logger = logging.getLogger(__name__)

class WorkOrderService:
    def __init__(self, db, audit_service, financial_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.financial_service = financial_service
        self.permission_checker = permission_checker
        self.wo_repo = WorkOrderRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.vendor_repo = VendorRepository(db)
        self.project_repo = ProjectRepository(db)
        self.seq_repo = SequenceRepository(db)

    async def create_work_order(self, user: dict, project_id: str, wo_data: WorkOrderCreate) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        idempotency_key = wo_data.idempotency_key
        
        # Security: Check project access
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        
        # Validate financial integrity (Parity with tech arch §6.4)
        await self.financial_service.validate_financial_document("WORK_ORDER", wo_data.dict(), project_id)
        
        async with db_manager.transaction_session() as session:
            # 1. Idempotency Check
            if idempotency_key:
                from app.core.idempotency import get_recorded_operation, record_operation
                recorded = await get_recorded_operation(self.db, session, idempotency_key)
                if recorded:
                    return recorded

            # 2. Validate Budget
            budget = await self.budget_repo.get_by_project_and_category(project_id, wo_data.category_id, session=session)
            if not budget:
                raise HTTPException(status_code=400, detail="Category budget not initialized.")

            # 3. Strict ID verification (Vendor)
            vendor = await self.vendor_repo.get_by_id(wo_data.vendor_id, organisation_id=organisation_id, session=session)
            if not vendor:
                raise HTTPException(status_code=400, detail="Vendor not found.")

            # 4. Calculate financials using utility
            subtotal = Decimal("0.0")
            for item in wo_data.line_items:
                qty = Decimal(str(item.qty))
                rate = Decimal(str(item.rate))
                item_total = self.financial_service.round_half_up(qty * rate)
                item.total = item_total
                subtotal += item_total
            
            project = await self.project_repo.get_by_id(project_id, organisation_id=organisation_id, session=session)
            cgst_pct = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_pct = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")
            
            from app.core.financial_utils import calculate_wo_financials
            fin = calculate_wo_financials(
                subtotal=subtotal,
                retention_pct=Decimal(str(wo_data.retention_percent or 0)),
                discount=Decimal(str(wo_data.discount or 0)),
                cgst_pct=cgst_pct,
                sgst_pct=sgst_pct
            )

            actual_payable = fin["actual_payable"]
            grand_total = fin["grand_total"]

            # 5. Generate WO Ref
            seq_val = await self.seq_repo.get_next_sequence(f"wo_seq_{organisation_id}", session=session)
            wo_ref = f"WO-{seq_val:04d}"

            # 6. Save WO
            wo_dict = wo_data.dict()
            wo_dict.update({
                "organisation_id": organisation_id,
                "project_id": project_id,
                "wo_ref": wo_ref,
                "subtotal": to_d128(fin["subtotal"]),
                "discount": to_d128(fin["discount"]),
                "total_before_tax": to_d128(fin["total_before_tax"]),
                "cgst": to_d128(fin["cgst"]),
                "sgst": to_d128(fin["sgst"]),
                "grand_total": to_d128(fin["grand_total"]),
                "retention_percent": to_d128(Decimal(str(wo_data.retention_percent or 0))),
                "retention_amount": to_d128(fin["retention_amount"]),
                "total_payable": to_d128(fin["total_payable"]),
                "actual_payable": to_d128(fin["actual_payable"]),
                "status": "Draft",
                "version": 1,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })

            new_wo = await self.wo_repo.create(wo_dict, session=session)

            # 7. Update Budget
            await self.budget_repo.update_one(
                {"_id": ObjectId(budget["id"])},
                {
                    "$inc": {
                        "remaining_budget": to_d128(-grand_total),
                        "committed_amount": to_d128(grand_total)
                    }
                },
                session=session
            )

            # 8. Record for Idempotency
            if idempotency_key:
                from app.core.idempotency import record_operation
                await record_operation(self.db, session, idempotency_key, "WORK_ORDER", response_payload=new_wo)

            # 9. Audit (Full JSON Snapshot)
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=new_wo["id"],
                action_type="CREATE",
                user_id=user["user_id"],
                project_id=project_id,
                new_value=new_wo,
                session=session
            )

            # 10. Financial Recalculation Bridge
            await self.financial_service.recalculate_master_budget(project_id, session=session)

            return new_wo

    async def update_work_order(self, wo_id: str, wo_data: dict, user: dict) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        
        # 1. Fetch current to get project_id for validation
        old_wo = await self.wo_repo.get_by_id(wo_id, organisation_id=organisation_id)
        if not old_wo:
            raise HTTPException(status_code=404, detail="Work Order not found.")
        
        # Security: Check write access with role
        await self.permission_checker.check_write_access_with_role(user, old_wo["project_id"])

        # Validate financial integrity (Parity with tech arch §6.4)
        await self.financial_service.validate_financial_document("WORK_ORDER", wo_data, old_wo["project_id"])

        from app.db.mongodb import db_manager
        from decimal import Decimal
        from bson import Decimal128

        async with db_manager.transaction_session() as session:
            # 2. Status Lock
            if old_wo["status"] not in ["Draft", "Pending"]:
                raise HTTPException(status_code=400, detail="Only 'Draft' or 'Pending' Work Orders can be edited.")

            # 3. Linked-PC Lock Rule (Spec §3.3)
            # Cannot reduce grand_total below the sum of already issued (non-cancelled) PCs
            linked_pcs = await self.db.payment_certificates.find({
                "work_order_id": wo_id,
                "status": {"$ne": "Cancelled"}
            }, session=session).to_list(length=None)
            linked_pc_total = sum(Decimal(str(pc.get("grand_total", "0"))) for pc in linked_pcs)

            # 4. Perform math using utility
            subtotal = Decimal("0.0")
            for item in wo_data.get("line_items", []):
                qty = Decimal(str(item.get("qty", 0)))
                rate = Decimal(str(item.get("rate", 0)))
                item["total"] = self.financial_service.round_half_up(qty * rate)
                subtotal += Decimal(str(item["total"]))
            
            project = await self.project_repo.get_by_id(old_wo["project_id"], organisation_id=organisation_id, session=session)
            cgst_pct = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_pct = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")
            
            retention_pct = Decimal(str(wo_data.get("retention_percent") or old_wo.get("retention_percent", 0)))
            discount_val = Decimal(str(wo_data.get("discount", 0)))

            from app.core.financial_utils import calculate_wo_financials
            fin = calculate_wo_financials(
                subtotal=subtotal,
                retention_pct=retention_pct,
                discount=discount_val,
                cgst_pct=cgst_pct,
                sgst_pct=sgst_pct
            )

            # Rule Enforcement
            if linked_pc_total > 0 and fin["grand_total"] < linked_pc_total:
                raise HTTPException(status_code=400, detail=f"Cannot reduce WO below linked PC total of ₹{linked_pc_total}")

            # 5. Update
            update_dict = {
                "subtotal": to_d128(fin["subtotal"]),
                "discount": to_d128(fin["discount"]),
                "total_before_tax": to_d128(fin["total_before_tax"]),
                "cgst": to_d128(fin["cgst"]),
                "sgst": to_d128(fin["sgst"]),
                "grand_total": to_d128(fin["grand_total"]),
                "retention_percent": to_d128(retention_pct),
                "retention_amount": to_d128(fin["retention_amount"]),
                "total_payable": to_d128(fin["total_payable"]),
                "actual_payable": to_d128(fin["actual_payable"]),
                "line_items": [db_manager.to_bson(item) for item in wo_data.get("line_items", [])],
                "updated_at": datetime.now(timezone.utc)
            }
            if "description" in wo_data: update_dict["description"] = wo_data["description"]
            if "terms" in wo_data: update_dict["terms"] = wo_data["terms"]

            await self.wo_repo.update_one({"_id": ObjectId(wo_id)}, {"$set": update_dict, "$inc": {"version": 1}}, session=session)

            # 6. Authoritative Budget Recompute (Spec §3.4)
            # Recomputes committed_amount as a SUM to prevent floating drift
            pipeline = [
                {"$match": {"project_id": old_wo["project_id"], "category_id": old_wo["category_id"], "status": {"$ne": "Cancelled"}}},
                {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
            ]
            agg = await self.db.work_orders.aggregate(pipeline, session=session).to_list(length=1)
            committed_sum = agg[0]["total"] if agg else Decimal128("0")

            await self.db.project_category_budgets.update_one(
                {"project_id": old_wo["project_id"], "category_id": old_wo["category_id"]},
                {"$set": {"committed_amount": committed_sum}},
                session=session
            )

            # 7. Audit & Recalculate
            await self.financial_service.recalculate_master_budget(old_wo["project_id"], session=session)
            return await self.wo_repo.get_by_id(wo_id, organisation_id=organisation_id, session=session)

    async def list_work_orders(self, user: dict, project_id: Optional[str], limit: int, cursor: Optional[str]) -> Dict[str, Any]:
        query = {"organisation_id": user["organisation_id"]}
        if project_id:
            query["project_id"] = project_id
        
        if cursor:
            query["created_at"] = {"$lt": datetime.fromisoformat(cursor)}

        docs = await self.wo_repo.list(query, sort=[("created_at", -1)], limit=limit)
        
        next_cursor = None
        if len(docs) == limit:
            next_cursor = docs[-1]["created_at"].isoformat()

        return {
            "items": docs,
            "next_cursor": next_cursor
        }
