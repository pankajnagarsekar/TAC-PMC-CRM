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

logger = logging.getLogger(__name__)

class WorkOrderService:
    def __init__(self, db, audit_service, financial_service):
        self.db = db
        self.audit_service = audit_service
        self.financial_service = financial_service
        self.wo_repo = WorkOrderRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.vendor_repo = VendorRepository(db)
        self.project_repo = ProjectRepository(db)
        self.seq_repo = SequenceRepository(db)

    async def create_work_order(self, user: dict, project_id: str, wo_data: WorkOrderCreate) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        
        async with db_manager.transaction_session() as session:
            # 1. Validate Budget
            budget = await self.budget_repo.get_by_project_and_category(project_id, wo_data.category_id, session=session)
            if not budget:
                raise HTTPException(status_code=400, detail="Category budget not initialized.")

            # 2. Strict ID verification (Vendor)
            vendor = await self.vendor_repo.get_by_id(wo_data.vendor_id, organisation_id=organisation_id, session=session)
            if not vendor:
                raise HTTPException(status_code=400, detail="Vendor not found.")

            # 3. Calculate Totals
            subtotal = Decimal("0.0")
            for item in wo_data.line_items:
                qty = Decimal(str(item.qty))
                rate = Decimal(str(item.rate))
                item_total = self.financial_service.round_half_up(qty * rate)
                item.total = item_total
                subtotal += item_total
            
            subtotal = self.financial_service.round_half_up(subtotal)
            discount = self.financial_service.round_half_up(Decimal(str(wo_data.discount or 0)))
            total_before_tax = subtotal - discount

            # Project tax rates
            project = await self.project_repo.get_by_id(project_id, organisation_id=organisation_id, session=session)
            cgst_rate = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_rate = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")

            cgst = self.financial_service.round_half_up(total_before_tax * cgst_rate / Decimal("100"))
            sgst = self.financial_service.round_half_up(total_before_tax * sgst_rate / Decimal("100"))
            grand_total = self.financial_service.round_half_up(total_before_tax + cgst + sgst)

            # 4. Generate WO Ref
            seq_val = await self.seq_repo.get_next_sequence(f"wo_seq_{organisation_id}", session=session)
            wo_ref = f"WO-{seq_val:04d}"

            # 5. Save WO
            wo_dict = wo_data.dict()
            wo_dict.update({
                "organisation_id": organisation_id,
                "project_id": project_id,
                "wo_ref": wo_ref,
                "subtotal": Decimal128(str(subtotal)),
                "discount": Decimal128(str(discount)),
                "total_before_tax": Decimal128(str(total_before_tax)),
                "cgst": Decimal128(str(cgst)),
                "sgst": Decimal128(str(sgst)),
                "grand_total": Decimal128(str(grand_total)),
                "status": "Draft",
                "version": 1
            })

            new_wo = await self.wo_repo.create(wo_dict, session=session)

            # 6. Update Budget
            await self.budget_repo.update_one(
                {"_id": ObjectId(budget["id"])},
                {
                    "$inc": {
                        "remaining_budget": Decimal128(str(-grand_total)),
                        "committed_amount": Decimal128(str(grand_total))
                    }
                },
                session=session
            )

            # 7. Audit
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

            return new_wo

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
