"""
Work Order Business Logic Service
Implements the MongoDB Multi-Document Transactions for creating and updating Work Orders
as defined in the Enterprise Technical Architecture Specification.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId, Decimal128
from fastapi import HTTPException
from core.database import db_manager
from core.idempotency import check_idempotency, record_operation, get_recorded_operation
from core.performance import measure_performance

logger = logging.getLogger(__name__)


class WorkOrderService:
    def __init__(self, db, audit_service, financial_service):
        self.db = db
        self.audit_service = audit_service
        self.financial_service = financial_service

    @measure_performance("WORK_ORDER_SAVE")
    async def create_work_order(self, wo_data: dict, current_user: dict, project_id: str) -> dict:
        """
        Creates a Work Order inside a strict MongoDB ACID transaction.
        Enforces single-category constraint, calculates totals, deducts budget, and logs audit trail.
        """
        idempotency_key = wo_data.get("idempotency_key")
        organisation_id = current_user.get("organisation_id")
        user_id = current_user.get("user_id")
        category_id = wo_data.get("category_id")

        async with db_manager.transaction_session() as session:
            # 1. Idempotency Check - Replay Pattern
            if idempotency_key:
                # First check: try to get recorded response payload
                recorded_response = await get_recorded_operation(self.db, session, idempotency_key)
                if recorded_response:
                    return recorded_response

                # Fallback: check legacy records without payload
                # SECURITY: organisation_id MUST be included to prevent cross-tenant leakage
                existing_wo = await self.db.work_orders.find_one(
                    {"idempotency_key": idempotency_key, "organisation_id": organisation_id},
                    session=session
                )
                if existing_wo:
                    return db_manager.from_bson(existing_wo)

            # 2. Validate Category Budget exists
            budget = await self.db.project_category_budgets.find_one({
                "project_id": project_id,
                "category_id": category_id
            }, session=session)
            if not budget:
                raise HTTPException(status_code=400, detail="Category budget not initialized for this project.")

            # 3. Validation: Vendor exists
            vendor = await self.db.vendors.find_one({
                "_id": ObjectId(wo_data["vendor_id"]),
                "organisation_id": organisation_id,
                "active_status": True
            }, session=session)
            if not vendor:
                raise HTTPException(status_code=400, detail="Invalid or inactive vendor.")

            # 4. Strict Financial Validation
            await self.financial_service.validate_financial_document("WORK_ORDER", wo_data, project_id, session=session)

            # 5. Server-Side Calculations (per CRM Spec §3.3)
            subtotal = Decimal("0.0")
            for item in wo_data.get("line_items", []):
                qty = Decimal(str(item.get("qty", 0)))
                rate = Decimal(str(item.get("rate", 0)))
                line_total = self.financial_service.round_half_up(qty * rate)
                item["total"] = line_total
                subtotal += line_total
            subtotal = self.financial_service.round_half_up(subtotal)
            discount = self.financial_service.round_half_up(Decimal(str(wo_data.get("discount", 0))))
            total_before_tax = self.financial_service.round_half_up(subtotal - discount)

            # Get project tax rates for server-side calculation (per Spec §3.3)
            project = await self.db.projects.find_one(
                {"_id": ObjectId(project_id)} if len(project_id) == 24 else {"project_id": project_id},
                session=session
            )
            cgst_rate = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_rate = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")

            # Calculate CGST/SGST server-side (per Spec §3.3)
            cgst = self.financial_service.round_half_up(total_before_tax * cgst_rate / Decimal("100"))
            sgst = self.financial_service.round_half_up(total_before_tax * sgst_rate / Decimal("100"))
            grand_total = self.financial_service.round_half_up(total_before_tax + cgst + sgst)
            retention_percent = Decimal(str(wo_data.get("retention_percent", 0)))
            retention_amount = self.financial_service.round_half_up(grand_total * (retention_percent / Decimal("100")))
            # Per Spec §3.3: total_payable = grand_total (full amount, no retention deducted)
            total_payable = grand_total
            # Per Spec §3.3: actual_payable = grand_total - retention_amount (net after retention)
            actual_payable = self.financial_service.round_half_up(grand_total - retention_amount)

            # 5. Auto-generate WO Ref — atomic sequence to prevent duplicate IDs under concurrent load
            settings = await self.db.global_settings.find_one({"organisation_id": organisation_id}, session=session)
            prefix = settings.get("wo_prefix", "WO-") if settings else "WO-"
            seq_doc = await self.db.sequences.find_one_and_update(
                {"_id": f"wo_seq_{organisation_id}"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=True,
                session=session
            )
            wo_ref = f"{prefix}{seq_doc['seq']:04d}"

            # 6. Apply Budget Constraint (deduct remaining, add committed)
            old_remaining = Decimal(str(budget.get("remaining_budget", 0)))
            old_committed = Decimal(str(budget.get("committed_amount", 0)))
            new_remaining = old_remaining - grand_total
            new_committed = old_committed + grand_total

            # Warning flag if over budget (per spec, we don't block saving)
            warning = "over_budget" if new_remaining < 0 else None

            await self.db.project_category_budgets.update_one(
                {"_id": budget["_id"]},
                {"$set": {
                    "remaining_budget": Decimal128(str(new_remaining)),
                    "committed_amount": Decimal128(str(new_committed)),
                    "updated_at": datetime.now(timezone.utc)
                }},
                session=session
            )

            # 7. Construct WO Document
            wo_doc = {
                "organisation_id": organisation_id,
                "project_id": project_id,
                "category_id": category_id,
                "vendor_id": wo_data["vendor_id"],
                "wo_ref": wo_ref,
                "description": wo_data.get("description", ""),
                "terms": wo_data.get("terms", ""),
                "subtotal": Decimal128(str(subtotal)),
                "discount": Decimal128(str(discount)),
                "total_before_tax": Decimal128(str(total_before_tax)),
                "cgst": Decimal128(str(cgst)),
                "sgst": Decimal128(str(sgst)),
                "grand_total": Decimal128(str(grand_total)),
                "retention_percent": Decimal128(str(retention_percent)),
                "retention_amount": Decimal128(str(retention_amount)),
                "total_payable": Decimal128(str(total_payable)),
                "actual_payable": Decimal128(str(actual_payable)),
                "status": "Draft",
                "line_items": [db_manager.to_bson(item) for item in wo_data.get("line_items", [])],
                "idempotency_key": idempotency_key,
                "version": 1,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # 8. Insert WO
            result = await self.db.work_orders.insert_one(wo_doc, session=session)
            wo_id = str(result.inserted_id)
            wo_doc["_id"] = result.inserted_id

            # 9. Record operation & Audit Log with FULL JSON snapshot
            response_doc = db_manager.from_bson(wo_doc)
            if warning:
                response_doc["_warning"] = warning

            await record_operation(self.db, session, idempotency_key, "WORK_ORDER", response_payload=response_doc)
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="CREATE",
                user_id=user_id,
                new_value=response_doc,  # FULL JSON snapshot per spec 6.1.2
                session=session
            )

            # 10. Update Master Budget
            await self.financial_service.recalculate_master_budget(project_id, session=session)

            return response_doc

    @measure_performance("WORK_ORDER_SAVE")
    async def update_work_order(self, wo_id: str, wo_data: dict, current_user: dict) -> dict:
        """
        Updates a Work Order (Draft only) and synchronizes budget deductions.
        """
        organisation_id = current_user.get("organisation_id")
        user_id = current_user.get("user_id")

        async with db_manager.transaction_session() as session:
            # 1. Fetch current WO
            old_wo = await self.db.work_orders.find_one({
                "_id": ObjectId(wo_id),
                "organisation_id": organisation_id
            }, session=session)
            if not old_wo:
                raise HTTPException(status_code=404, detail="Work Order not found.")

            # 1.1 Version check for optimistic concurrency
            expected_version = wo_data.pop("expected_version", None)
            if expected_version is not None:
                current_version = old_wo.get("version", 1)
                if current_version != expected_version:
                    raise HTTPException(
                        status_code=409,
                        detail={"error": "concurrency_conflict", "message": "Work Order was modified in another session. Please refresh."}
                    )

            # Allow editing in Draft and Pending states (workflow flexibility)
            if old_wo["status"] not in ["Draft", "Pending"]:
                raise HTTPException(status_code=400, detail="Only Work Orders in 'Draft' or 'Pending' status can be edited.")

            # 1.2 Check for linked PCs - Lock Rule: cannot reduce grand_total below sum of linked PCs
            linked_pcs = await self.db.payment_certificates.find({
                "work_order_id": wo_id,
                "status": {"$ne": "Cancelled"}
            }).to_list(length=None)
            linked_pc_total = sum(float(pc.get("grand_total", Decimal128("0")).to_decimal()) for pc in linked_pcs)
            old_grand_total = Decimal(str(old_wo["grand_total"].to_decimal()))
            old_category_id = old_wo["category_id"]
            project_id = old_wo["project_id"]

            # 2. Reverse old budget impact
            await self.db.project_category_budgets.update_one(
                {"project_id": project_id, "category_id": old_category_id},
                {"$inc": {
                    "remaining_budget": Decimal128(str(old_grand_total)),
                    "committed_amount": Decimal128(str(-old_grand_total))
                }},
                session=session
            )

            # 3. Strict Financial Validation
            await self.financial_service.validate_financial_document("WORK_ORDER", wo_data, project_id, session=session)

            # 4. Calculate new totals (per CRM Spec §3.3)
            subtotal = Decimal("0.0")
            for item in wo_data.get("line_items", []):
                qty = Decimal(str(item.get("qty", 0)))
                rate = Decimal(str(item.get("rate", 0)))
                line_total = self.financial_service.round_half_up(qty * rate)
                item["total"] = line_total
                subtotal += line_total
            subtotal = self.financial_service.round_half_up(subtotal)
            discount = self.financial_service.round_half_up(Decimal(str(wo_data.get("discount", 0))))
            total_before_tax = self.financial_service.round_half_up(subtotal - discount)

            # Get project tax rates for server-side calculation (per Spec §3.3)
            project = await self.db.projects.find_one(
                {"_id": ObjectId(project_id)} if len(project_id) == 24 else {"project_id": project_id},
                session=session
            )
            cgst_rate = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_rate = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")

            # Calculate CGST/SGST server-side (per Spec §3.3)
            cgst = self.financial_service.round_half_up(total_before_tax * cgst_rate / Decimal("100"))
            sgst = self.financial_service.round_half_up(total_before_tax * sgst_rate / Decimal("100"))
            grand_total = self.financial_service.round_half_up(total_before_tax + cgst + sgst)

            # 4.1 Linked-PC Lock Rule: cannot reduce grand_total below sum of linked PCs
            if linked_pc_total > 0 and grand_total < Decimal(str(linked_pc_total)):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot reduce WO total below ₹{linked_pc_total}. There are linked Payment Certificates with total ₹{linked_pc_total}."
                )

            retention_percent = Decimal(str(wo_data.get("retention_percent", 0)))
            retention_amount = self.financial_service.round_half_up(grand_total * (retention_percent / Decimal("100")))
            # Per Spec §3.3: total_payable = grand_total (full amount, no retention deducted)
            total_payable = grand_total
            # Per Spec §3.3: actual_payable = grand_total - retention_amount (net after retention)
            actual_payable = self.financial_service.round_half_up(grand_total - retention_amount)

            # 4. Apply new budget impact
            new_category_id = wo_data.get("category_id", old_category_id)

            # Check if budget exists for new category
            budget = await self.db.project_category_budgets.find_one({
                "project_id": project_id,
                "category_id": new_category_id
            }, session=session)
            if not budget:
                raise HTTPException(status_code=400, detail="Target category budget not initialized.")

            # Per Spec §3.4: On WO UPDATE, committed_amount = SUM(all WO grand_total for category)
            # Recompute as authoritative SUM rather than delta to prevent drift under concurrent edits
            pipeline = [
                {"$match": {
                    "project_id": project_id,
                    "category_id": new_category_id,
                    "status": {"$nin": ["Cancelled"]}
                }},
                {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
            ]
            result = await self.db.work_orders.aggregate(pipeline).to_list(length=1)
            raw_total = result[0].get("total") if result else None
            committed_amount = Decimal(str(raw_total.to_decimal())) if isinstance(raw_total, Decimal128) else Decimal(str(raw_total)) if raw_total is not None else Decimal("0")
            raw_budget = budget.get("original_budget", Decimal128("0"))
            original_budget = Decimal(str(raw_budget.to_decimal())) if isinstance(raw_budget, Decimal128) else Decimal(str(raw_budget))
            remaining_budget = original_budget - committed_amount

            await self.db.project_category_budgets.update_one(
                {"_id": budget["_id"]},
                {"$set": {
                    "committed_amount": Decimal128(str(committed_amount)),
                    "remaining_budget": Decimal128(str(remaining_budget))
                }},
                session=session
            )

            # 5. Update WO Document
            update_fields = {
                "category_id": new_category_id,
                "vendor_id": wo_data.get("vendor_id", old_wo["vendor_id"]),
                "description": wo_data.get("description", ""),
                "terms": wo_data.get("terms", ""),
                "subtotal": Decimal128(str(subtotal)),
                "discount": Decimal128(str(discount)),
                "total_before_tax": Decimal128(str(total_before_tax)),
                "cgst": Decimal128(str(cgst)),
                "sgst": Decimal128(str(sgst)),
                "grand_total": Decimal128(str(grand_total)),
                "retention_percent": Decimal128(str(retention_percent)),
                "retention_amount": Decimal128(str(retention_amount)),
                "total_payable": Decimal128(str(total_payable)),
                "actual_payable": Decimal128(str(actual_payable)),
                "line_items": [db_manager.to_bson(item) for item in wo_data.get("line_items", [])],
                "updated_at": datetime.now(timezone.utc)
            }
            await self.db.work_orders.update_one(
                {"_id": ObjectId(wo_id)},
                {"$set": update_fields, "$inc": {"version": 1}},
                session=session
            )

            # 6. Audit Log with FULL JSON snapshots
            old_wo_full = db_manager.from_bson(old_wo)
            new_wo_full = db_manager.from_bson(await self.db.work_orders.find_one({"_id": ObjectId(wo_id)}, session=session))
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="UPDATE",
                user_id=current_user.get("user_id"),
                project_id=project_id,
                old_value=old_wo_full,  # FULL JSON snapshot per spec 6.1.2
                new_value=new_wo_full,  # FULL JSON snapshot per spec 6.1.2
                session=session
            )

            # 7. Refresh Financials
            await self.financial_service.recalculate_master_budget(project_id, session=session)
            updated_wo = await self.db.work_orders.find_one({"_id": ObjectId(wo_id)}, session=session)
            return db_manager.from_bson(updated_wo)

    async def delete_work_order(self, wo_id: str, current_user: dict) -> dict:
        """
        Deletes a Work Order (Draft only, No linked PCs).
        """
        organisation_id = current_user.get("organisation_id")

        async with db_manager.transaction_session() as session:
            wo = await self.db.work_orders.find_one({
                "_id": ObjectId(wo_id),
                "organisation_id": organisation_id
            }, session=session)
            if not wo:
                raise HTTPException(status_code=404, detail="Work Order not found.")

            # Rule: Only Drafts can be deleted
            if wo["status"] != "Draft":
                raise HTTPException(status_code=400, detail="Only 'Draft' Work Orders can be deleted. Please cancel instead.")

            # Rule: Cannot delete if linked to a Payment Certificate
            linked_pc = await self.db.payment_certificates.find_one({
                "work_order_id": wo_id,
                "status": {"$ne": "Cancelled"}
            }, session=session)
            if linked_pc:
                raise HTTPException(status_code=400, detail="Cannot delete Work Order with linked Payment Certificates.")

            # Capture full WO state before deletion for audit
            wo_full = db_manager.from_bson(wo)
            grand_total = Decimal(str(wo["grand_total"].to_decimal()))
            project_id = wo["project_id"]
            category_id = wo["category_id"]

            # 1. Revert budget impact
            await self.db.project_category_budgets.update_one(
                {"project_id": project_id, "category_id": category_id},
                {"$inc": {
                    "remaining_budget": Decimal128(str(grand_total)),
                    "committed_amount": Decimal128(str(-grand_total))
                }},
                session=session
            )

            # 2. Delete WO
            await self.db.work_orders.delete_one({"_id": ObjectId(wo_id)}, session=session)

            # 3. Audit Log with FULL JSON snapshot of deleted document
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="DELETE",
                user_id=current_user.get("user_id"),
                project_id=project_id,
                old_value=wo_full,  # FULL JSON snapshot per spec 6.1.2
                session=session
            )

            # 4. Refresh Financials
            await self.financial_service.recalculate_master_budget(project_id, session=session)

            return {"status": "success", "message": "Work Order deleted and budget restored."}
