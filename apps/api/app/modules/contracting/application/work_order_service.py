import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional
from bson import ObjectId, Decimal128
from fastapi import HTTPException

from ..schemas.dto import WorkOrder, WorkOrderCreate, WorkOrderUpdate
from ..infrastructure.repository import WorkOrderRepository, VendorRepository, LedgerRepository
# Note: SequenceRepository is now in Shared Kernel
from app.modules.shared.infrastructure.sequence_repo import SequenceRepository
# These depend on other contexts yet to be migrated
from app.repositories.project_repo import ProjectRepository
from app.repositories.financial_repo import BudgetRepository
from app.core.utils import serialize_doc
from app.core.financial_utils import to_d128, to_decimal, calculate_wo_financials
from app.core.uow import UnitOfWork

logger = logging.getLogger(__name__)

class WorkOrderService:
    """
    Sovereign Work Order Orchestrator for Contracting Context.
    Enforces atomic transactions and cascading budget recalculations via UnitOfWork.
    """
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
        
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        await self.financial_service.validate_financial_document("WORK_ORDER", wo_data.dict(), project_id)
        
        async with UnitOfWork(self.db) as uow:
            if idempotency_key:
                from app.core.idempotency import get_recorded_operation
                recorded = await get_recorded_operation(self.db, uow.session, idempotency_key)
                if recorded: return recorded

            budget = await uow.budgets.get_by_project_and_category(project_id, wo_data.category_id, session=uow.session)
            if not budget: raise HTTPException(status_code=400, detail="Category budget not initialized.")

            vendor = await uow.db.vendors.find_one({"_id": ObjectId(wo_data.vendor_id), "organisation_id": organisation_id}, session=uow.session)
            if not vendor: raise HTTPException(status_code=400, detail="Vendor not found.")

            subtotal = Decimal("0.0")
            line_items_processed = []
            for item in wo_data.line_items:
                qty = Decimal(str(item.qty))
                rate = Decimal(str(item.rate))
                item_total = self.financial_service.round_half_up(qty * rate)
                subtotal += item_total
                item_dict = item.dict()
                item_dict["total"] = to_d128(item_total)
                line_items_processed.append(item_dict)
            
            project = await uow.projects.get_by_id(project_id, organisation_id=organisation_id, session=uow.session)
            cgst_pct = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_pct = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")
            
            fin = calculate_wo_financials(subtotal=subtotal, retention_pct=Decimal(str(wo_data.retention_percent or 0)),
                                         discount=Decimal(str(wo_data.discount or 0)), cgst_pct=cgst_pct, sgst_pct=sgst_pct)
            grand_total = fin["grand_total"]

            seq_val = await uow.db.sequences.find_one_and_update(
                {"_id": f"wo_seq_{organisation_id}"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True, session=uow.session
            )
            wo_ref = f"WO-{seq_val['seq']:04d}"

            wo_dict = wo_data.dict()
            wo_dict.update({
                "organisation_id": organisation_id, "project_id": project_id, "wo_ref": wo_ref,
                "subtotal": to_d128(fin["subtotal"]), "discount": to_d128(fin["discount"]),
                "total_before_tax": to_d128(fin["total_before_tax"]), "cgst": to_d128(fin["cgst"]),
                "sgst": to_d128(fin["sgst"]), "grand_total": to_d128(fin["grand_total"]),
                "retention_percent": to_d128(Decimal(str(wo_data.retention_percent or 0))),
                "retention_amount": to_d128(fin["retention_amount"]), "total_payable": to_d128(fin["total_payable"]),
                "actual_payable": to_d128(fin["actual_payable"]), "line_items": line_items_processed,
                "status": "Draft", "version": 1, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)
            })

            new_wo = await uow.work_orders.create(wo_dict, session=uow.session)

            await uow.budgets.update(budget["id"], {
                "$inc": {"remaining_budget": to_d128(-grand_total), "committed_amount": to_d128(grand_total)}
            }, session=uow.session)

            if idempotency_key:
                from app.core.idempotency import record_operation
                await record_operation(self.db, uow.session, idempotency_key, "WORK_ORDER", response_payload=new_wo)

            await self.audit_service.log_action(
                organisation_id=organisation_id, module_name="WORK_ORDERS", entity_type="WORK_ORDER",
                entity_id=new_wo["id"], action_type="CREATE", user_id=user["user_id"],
                project_id=project_id, new_value=new_wo, session=uow.session
            )

            await self.financial_service.recalculate_master_budget(project_id, session=uow.session)
            return new_wo

    async def update_work_order(self, user: dict, wo_id: str, update_req: WorkOrderUpdate) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        
        async with UnitOfWork(self.db) as uow:
            old_wo = await uow.work_orders.get_by_id(wo_id, organisation_id=organisation_id, session=uow.session)
            if not old_wo: raise HTTPException(status_code=404, detail="Work Order not found.")
            
            await self.permission_checker.check_write_access_with_role(user, old_wo["project_id"])
            await self.financial_service.validate_financial_document("WORK_ORDER", update_req.dict(), old_wo["project_id"])

            if old_wo["status"] not in ["Draft", "Pending"]:
                raise HTTPException(status_code=400, detail="Only 'Draft' or 'Pending' Work Orders can be edited.")

            linked_pcs = await uow.payments.list({"work_order_id": wo_id, "status": {"$ne": "Cancelled"}}, session=uow.session)
            linked_pc_total = sum(to_decimal(pc.get("grand_total", 0)) for pc in linked_pcs)

            subtotal = Decimal("0.0")
            line_items_data = update_req.line_items if update_req.line_items is not None else old_wo.get("line_items", [])
            line_items_processed = []
            
            for item in (line_items_data if isinstance(line_items_data, list) else []):
                i_dict = item if isinstance(item, dict) else item.dict()
                qty = Decimal(str(i_dict.get("qty", 0)))
                rate = Decimal(str(i_dict.get("rate", 0)))
                item_total = self.financial_service.round_half_up(qty * rate)
                subtotal += item_total
                i_dict["total"] = to_d128(item_total)
                line_items_processed.append(i_dict)
            
            project = await uow.projects.get_by_id(old_wo["project_id"], organisation_id=organisation_id, session=uow.session)
            cgst_pct = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_pct = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")
            
            retention_pct = Decimal(str(update_req.retention_percent if update_req.retention_percent is not None else old_wo.get("retention_percent", 0)))
            discount_val = Decimal(str(update_req.discount if update_req.discount is not None else old_wo.get("discount", 0)))

            fin = calculate_wo_financials(subtotal=subtotal, retention_pct=retention_pct, discount=discount_val, 
                                         cgst_pct=cgst_pct, sgst_pct=sgst_pct)

            if linked_pc_total > 0 and fin["grand_total"] < linked_pc_total:
                raise HTTPException(status_code=400, detail=f"Cannot reduce WO below linked PC total of ₹{linked_pc_total}")

            update_dict = {
                "subtotal": to_d128(fin["subtotal"]), "discount": to_d128(fin["discount"]),
                "total_before_tax": to_d128(fin["total_before_tax"]), "cgst": to_d128(fin["cgst"]),
                "sgst": to_d128(fin["sgst"]), "grand_total": to_d128(fin["grand_total"]),
                "retention_percent": to_d128(retention_pct), "retention_amount": to_d128(fin["retention_amount"]),
                "total_payable": to_d128(fin["total_payable"]), "actual_payable": to_d128(fin["actual_payable"]),
                "line_items": line_items_processed, "updated_at": datetime.now(timezone.utc),
                "version": update_req.expected_version 
            }

            result = await uow.work_orders.update(wo_id, update_dict, session=uow.session)
            if not result:
                raise HTTPException(status_code=409, detail="CONFLICT: Resource modified or version mismatch.")

            await self.audit_service.log_action(
                organisation_id=organisation_id, module_name="WORK_ORDERS", entity_type="WORK_ORDER",
                entity_id=wo_id, action_type="UPDATE", user_id=user["user_id"],
                project_id=old_wo["project_id"], old_value=old_wo, new_value=result, session=uow.session
            )

            agg = await uow.work_orders.aggregate([
                {"$match": {"project_id": old_wo["project_id"], "category_id": old_wo.get("category_id"), "status": {"$ne": "Cancelled"}}},
                {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
            ], session=uow.session).to_list(1)
            committed_sum = agg[0]["total"] if agg else Decimal128("0.0")

            await uow.budgets.update_one(
                {"project_id": old_wo["project_id"], "category_id": old_wo.get("category_id")},
                {"$set": {"committed_amount": committed_sum}}, session=uow.session
            )

            await self.financial_service.recalculate_master_budget(old_wo["project_id"], session=uow.session)
            return result

    async def list_work_orders(self, user: dict, project_id: Optional[str], limit: int, cursor: Optional[str]) -> Dict[str, Any]:
        query = {"organisation_id": user["organisation_id"]}
        if project_id: query["project_id"] = project_id
        if cursor: query["created_at"] = {"$lt": datetime.fromisoformat(cursor)}

        docs = await self.wo_repo.list(query, sort=[("created_at", -1)], limit=limit)
        next_cursor = docs[-1]["created_at"].isoformat() if len(docs) == limit else None
        return {"items": docs, "next_cursor": next_cursor}
