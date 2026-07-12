import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from bson import ObjectId

from app.core.uow import UnitOfWork

# These depend on other contexts yet to be migrated
from app.modules.project.infrastructure.repository import (
    BudgetRepository,
    ProjectRepository,
)
from app.modules.shared.domain.exceptions import NotFoundError, ValidationError, DomainError
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.shared.domain.state_machine import StateMachine

# Note: SequenceRepository is now in Shared Kernel
from app.modules.shared.infrastructure.sequence_repo import SequenceRepository
from ..domain.models import WorkOrder as WorkOrderModel
from ..infrastructure.repository import (
    LedgerRepository,
    VendorRepository,
    WorkOrderRepository,
)
from ..schemas.dto import WorkOrderCreate, WorkOrderUpdate

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
        self.ledger_repo = LedgerRepository(db)

    async def _get_tax_rates(self, organisation_id: str, project_id: str, session=None) -> Dict[str, Decimal]:
        """BUG-006: Helper to resolve tax rates with proper fallback hierarchy."""
        # 1. Check Project Settings
        project = await self.project_repo.get_by_id(project_id, organisation_id=organisation_id, session=session)
        if project and project.get("project_cgst_percentage") is not None:
            return {
                "cgst": Decimal(str(project["project_cgst_percentage"])),
                "sgst": Decimal(str(project.get("project_sgst_percentage", "9.0")))
            }

        # 2. Check Global Organisation Settings
        settings = await self.db.organisation_settings.find_one({"organisation_id": organisation_id}, session=session)
        if settings:
            return {
                "cgst": Decimal(str(settings.get("cgst_percentage", "9.0"))),
                "sgst": Decimal(str(settings.get("sgst_percentage", "9.0")))
            }

        # 3. Final Fallback
        return {"cgst": Decimal("9.0"), "sgst": Decimal("9.0")}

    async def create_work_order(
        self, user: dict, project_id: str, wo_data: WorkOrderCreate
    ) -> Dict[str, Any]:
        """Atomic Work Order Creation (Point 75)."""
        try:
            organisation_id = user["organisation_id"]
            idempotency_key = wo_data.idempotency_key

            await self.permission_checker.check_project_access(
                user, project_id, require_write=True
            )
            await self.financial_service.validate_financial_document(
                "WORK_ORDER", wo_data.model_dump(), project_id
            )

            async with UnitOfWork(self.db) as uow:
                if idempotency_key:
                    from app.core.idempotency import get_recorded_operation

                    recorded = await get_recorded_operation(
                        self.db, uow.session, idempotency_key
                    )
                    if recorded:
                        return recorded

                async with uow:
                    # 1. Authoritative Budget Check (CALC-1)
                    budget = await uow.budgets.get_by_project_and_category(
                        project_id, wo_data.category_id, session=uow.session
                    )
                    if not budget:
                        raise ValidationError("Category budget not initialized.")

                    # 2. Domain Validation: Vendor Consistency
                    # Standardizing vendor lookup (Fixed BUG-35)
                    vendor = await uow.db.vendors.find_one(
                        {
                            "_id": ObjectId(wo_data.vendor_id),
                            "organisation_id": organisation_id,
                        },
                        session=uow.session,
                    )
                    if not vendor:
                        raise ValidationError("Vendor not found.")

                    # 3. Calculation Engine: Line Items (CALC-5)
                    items_data = [item.model_dump() for item in wo_data.line_items]
                    subtotal = Decimal("0.0")

                    for item in items_data:
                        qty = FinancialEngine.to_decimal(item["qty"])
                        rate = FinancialEngine.to_decimal(item["rate"])
                        item_total = FinancialEngine.round(qty * rate)
                        item["total"] = FinancialEngine.to_d128(item_total)  # Fixed BULL-99: Ensure 128-bit precision
                        subtotal += item_total

                    # 4. Calculation Engine: Global WO Financials (BUG-006 Fix)
                    rates = await self._get_tax_rates(organisation_id, project_id, session=uow.session)
                    cgst_pct = rates["cgst"]
                    sgst_pct = rates["sgst"]

                    fin = FinancialEngine.calculate_wo_financials(
                        subtotal=subtotal,
                        discount_value=FinancialEngine.to_decimal(wo_data.discount_value or 0),
                        discount_type=wo_data.discount_type or "value",
                        retention_pct=FinancialEngine.to_decimal(wo_data.retention_percent or 0),
                        cgst_pct=cgst_pct,
                        sgst_pct=sgst_pct,
                    )
                    grand_total = fin["grand_total"]

                    # Sovereign Logic: Sequence Generation
                    next_seq = await self.seq_repo.get_next_sequence(
                        f"wo_seq_{organisation_id}", session=uow.session
                    )
                    wo_ref = f"WO-{next_seq:04d}"

                    wo_dict = wo_data.model_dump()
                    wo_dict.update(
                        {
                            "organisation_id": organisation_id,
                            "project_id": project_id,
                            "wo_ref": wo_ref,
                            "subtotal": FinancialEngine.to_d128(fin["subtotal"]),
                            "discount_value": FinancialEngine.to_d128(fin["discount_value"]),
                            "discount_type": fin["discount_type"],
                            "discount": FinancialEngine.to_d128(fin["discount"]),
                            "total_before_tax": FinancialEngine.to_d128(
                                fin["total_before_tax"]
                            ),
                            "cgst": FinancialEngine.to_d128(fin["cgst"]),
                            "sgst": FinancialEngine.to_d128(fin["sgst"]),
                            "grand_total": FinancialEngine.to_d128(fin["grand_total"]),
                            "retention_percent": FinancialEngine.to_d128(
                                Decimal(str(wo_data.retention_percent or 0))
                            ),
                            "retention_amount": FinancialEngine.to_d128(
                                fin["retention_amount"]
                            ),
                            "total_payable": FinancialEngine.to_d128(fin["total_payable"]),
                            "actual_payable": FinancialEngine.to_d128(
                                fin["actual_payable"]
                            ),
                            "status": "Draft",
                            "line_items": items_data,
                            "version": 1,
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc),
                        }
                    )

                    new_wo = await uow.work_orders.create(wo_dict, session=uow.session)

                    # BUG-007: Restore Audit Log
                    await self.audit_service.log_financial_event(
                        organisation_id=organisation_id,
                        entity_type="WORK_ORDER",
                        entity_id=str(new_wo["id"]),
                        action_type="CREATE",
                        user_id=user["user_id"],
                        project_id=project_id,
                        new_value=new_wo,
                        session=uow.session,
                    )

                    # CALC-1: Authoritative SUM Recalculation instead of $inc (BUG-35)
                    agg = await uow.work_orders.aggregate(
                        [
                            {
                                "$match": {
                                    "project_id": project_id,
                                    "category_id": wo_data.category_id,
                                    "status": {"$nin": ["Cancelled", "Draft"]},
                                }
                            },
                        ],
                        session=uow.session,
                    ).to_list(10000)

                    # Manual sum to avoid group empty result complexity
                    total_commit = Decimal("0.0")
                    for w in agg:
                        total_commit += FinancialEngine.to_decimal(w.get("grand_total", 0))

                    committed_sum = FinancialEngine.to_d128(total_commit)

                    await uow.budgets.update_one(
                        {"_id": ObjectId(budget["id"]) if ObjectId.is_valid(budget["id"]) else budget["id"]},
                        {"$set": {"committed_amount": committed_sum}},
                        session=uow.session,
                    )

                    # C2: Write Vendor Ledger Entry (Reference: Point 75 Ledger)
                    await uow.ledger.create({
                        "vendor_id": str(wo_data.vendor_id),
                        "project_id": project_id,
                        "ref_id": str(new_wo["id"]),
                        "entry_type": "COMMITTED",
                        "amount": FinancialEngine.to_d128(grand_total),
                        "created_at": datetime.now(timezone.utc)
                    }, session=uow.session)

                    if idempotency_key:
                        from app.core.idempotency import record_operation

                        await record_operation(
                            self.db,
                            uow.session,
                            idempotency_key,
                            "WORK_ORDER",
                            response_payload=new_wo,
                        )

                    # Final Recalculation Chain
                    await self.financial_service.recalculate_master_budget(
                        project_id, session=uow.session
                    )

                    # Populate names for immediate UI feedback
                    # Populate names for immediate UI feedback
                    if "vendor_id" in new_wo:
                        v_id = new_wo["vendor_id"]
                        res_id = ObjectId(v_id) if ObjectId.is_valid(v_id) else v_id
                        vendor = await self.db.vendors.find_one({"_id": res_id})
                        if vendor:
                            v_name = vendor.get("name") or vendor.get("vendor_name", "Unknown")
                            new_wo["vendor_name"] = v_name
                    if "category_id" in new_wo:
                        v_cid = new_wo["category_id"]
                        res_id = ObjectId(v_cid) if ObjectId.is_valid(v_cid) else None
                        cat_query = {"$or": [{"_id": res_id}, {"code": v_cid}]}
                        cat = await self.db.code_master.find_one(cat_query)
                        if cat:
                            c_name = cat.get("category_name") or cat.get("name") or cat.get("code") or "Unknown"
                            new_wo["category_name"] = c_name

                    return new_wo
        except Exception as e:
            import traceback
            print(f"CRITICAL SERVICE ERROR: {e}")
            traceback.print_exc()
            raise e

    async def update_work_order(
        self, user: dict, wo_id: str, update_req: WorkOrderUpdate
    ) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]

        async with UnitOfWork(self.db) as uow:
            old_wo = await uow.work_orders.get_by_id(
                wo_id, organisation_id=organisation_id, session=uow.session
            )
            if not old_wo:
                raise NotFoundError("Work Order", wo_id)

            await self.permission_checker.check_write_access_with_role(
                user, old_wo["project_id"]
            )
            # BUG-007 Fix: Merge existing data for validation to prevent false misses on required fields
            updates = update_req.model_dump(exclude_unset=True)
            # Authoritative Invariant: If line items are changing, ensure subtotal in validation context matches
            if "line_items" in updates and "subtotal" not in updates:
                items_raw = [
                    itm if isinstance(itm, dict) else itm.model_dump()
                    for itm in updates["line_items"]
                ]
                line_res = FinancialEngine.calculate_line_items(items_raw)
                updates["subtotal"] = line_res["subtotal"]

            # Authoritative State Check: Standardized Data Freeze
            StateMachine.check_modification_allowed("WORK_ORDER", old_wo.get("status", "Draft"))

            if update_req.status and update_req.status != old_wo.get("status"):
                StateMachine.validate_transition("WORK_ORDER", old_wo.get("status", "Draft"), update_req.status)

            wo_model = WorkOrderModel(old_wo)

            linked_pcs = await uow.payments.list(
                {"work_order_id": wo_id, "status": {"$ne": "Cancelled"}},
                session=uow.session,
            )
            linked_pc_total = sum(
                (FinancialEngine.to_decimal(pc.get("grand_total", 0)) for pc in linked_pcs),
                Decimal("0")
            )

            line_items_data = (
                update_req.line_items
                if update_req.line_items is not None
                else old_wo.get("line_items", [])
            )
            items_raw = [
                item if isinstance(item, dict) else item.model_dump()
                for item in (
                    line_items_data if isinstance(line_items_data, list) else []
                )
            ]

            # Sovereign Logic: Calculate Line Items
            line_result = FinancialEngine.calculate_line_items(items_raw)
            line_items_processed = []
            for itm in line_result["items"]:
                itm["total"] = FinancialEngine.to_d128(itm["total"])
                line_items_processed.append(itm)

            subtotal = line_result["subtotal"]

            # BUG-006: Use new tax rate resolver
            rates = await self._get_tax_rates(organisation_id, old_wo["project_id"], session=uow.session)
            cgst_pct = rates["cgst"]
            sgst_pct = rates["sgst"]

            retention_pct = FinancialEngine.to_decimal(
                update_req.retention_percent
                if update_req.retention_percent is not None
                else old_wo.get("retention_percent", 0)
            )
            discount_type = (
                update_req.discount_type
                if update_req.discount_type is not None
                else old_wo.get("discount_type", "value")
            )
            discount_value = (
                FinancialEngine.to_decimal(update_req.discount_value)
                if update_req.discount_value is not None
                else FinancialEngine.to_decimal(old_wo.get("discount_value", 0))
            )

            fin = FinancialEngine.calculate_wo_financials(
                subtotal=subtotal,
                discount_value=discount_value,
                discount_type=discount_type,
                retention_pct=retention_pct,
                cgst_pct=cgst_pct,
                sgst_pct=sgst_pct,
            )

            # Domain Aggregate Invariant Check
            wo_model.validate_for_update(linked_pc_total, fin["grand_total"])

            update_dict = {
                "subtotal": FinancialEngine.to_d128(fin["subtotal"]),
                "discount_value": FinancialEngine.to_d128(fin["discount_value"]),
                "discount_type": fin["discount_type"],
                "discount": FinancialEngine.to_d128(fin["discount"]),
                "total_before_tax": FinancialEngine.to_d128(fin["total_before_tax"]),
                "cgst": FinancialEngine.to_d128(fin["cgst"]),
                "sgst": FinancialEngine.to_d128(fin["sgst"]),
                "grand_total": FinancialEngine.to_d128(fin["grand_total"]),
                "retention_percent": FinancialEngine.to_d128(retention_pct),
                "retention_amount": FinancialEngine.to_d128(fin["retention_amount"]),
                "total_payable": FinancialEngine.to_d128(fin["total_payable"]),
                "actual_payable": FinancialEngine.to_d128(fin["actual_payable"]),
                "line_items": line_items_processed,
                "updated_at": datetime.now(timezone.utc),
                "version": update_req.expected_version + 1,
            }
            if update_req.status is not None:
                update_dict["status"] = update_req.status

            if update_req.category_id is not None:
                update_dict["category_id"] = update_req.category_id

            if update_req.vendor_id is not None:
                update_dict["vendor_id"] = update_req.vendor_id

            if update_req.description_of_works is not None:
                update_dict["description_of_works"] = update_req.description_of_works

            if update_req.general_t_and_c is not None:
                update_dict["general_t_and_c"] = update_req.general_t_and_c

            if update_req.payment_terms is not None:
                update_dict["payment_terms"] = update_req.payment_terms

            if update_req.vendor_contact_person is not None:
                update_dict["vendor_contact_person"] = update_req.vendor_contact_person

            if update_req.vendor_phone is not None:
                update_dict["vendor_phone"] = update_req.vendor_phone

            if update_req.start_date is not None:
                update_dict["start_date"] = update_req.start_date

            if update_req.end_date is not None:
                update_dict["end_date"] = update_req.end_date

            if update_req.product_warranty is not None:
                update_dict["product_warranty"] = update_req.product_warranty

            if update_req.workmanship_warranty is not None:
                update_dict["workmanship_warranty"] = update_req.workmanship_warranty

            result = await uow.work_orders.update(
                wo_id, update_dict, expected_version=update_req.expected_version, session=uow.session
            )
            if not result:
                raise ValidationError(
                    "CONFLICT: Resource modified or version mismatch."
                )

            # Audit Log
            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="UPDATE",
                user_id=user["user_id"],
                project_id=old_wo["project_id"],
                old_value=old_wo,
                new_value=result,
                session=uow.session,
            )

            # Recalculate everything authoritative via SUM (Point 75, CALC-1)
            # This handles both old and new category if changed
            await self.financial_service.recalculate_master_budget(
                old_wo["project_id"], session=uow.session
            )

            # Populate names for return
            if "vendor_id" in result:
                v_id = result["vendor_id"]
                res_id = ObjectId(v_id) if ObjectId.is_valid(v_id) else v_id
                vendor = await self.db.vendors.find_one({"_id": res_id})
                if vendor:
                    result["vendor_name"] = vendor.get("name") or vendor.get("vendor_name", "Unknown")
            if "category_id" in result:
                v_cid = result["category_id"]
                res_id = ObjectId(v_cid) if ObjectId.is_valid(v_cid) else None
                cat = await self.db.code_master.find_one(
                    {"$or": [{"_id": res_id}, {"code": v_cid}]}
                )
                if cat:
                    c_name = cat.get("category_name") or cat.get("name") or cat.get("code") or "Unknown"
                    result["category_name"] = c_name

            return result

    async def delete_work_order(self, user: dict, wo_id: str) -> bool:
        """Atomic Work Order Deletion with safety gates (Track I3)."""
        organisation_id = user["organisation_id"]

        async with UnitOfWork(self.db) as uow:
            wo = await uow.work_orders.get_by_id(
                wo_id, organisation_id=organisation_id, session=uow.session
            )
            if not wo:
                raise NotFoundError("Work Order", wo_id)

            project_id = wo["project_id"]

            await self.permission_checker.check_write_access_with_role(
                user, project_id
            )

            # Safety Gate: Must be in 'Draft' status (Track I3)
            # AND no linked PCs
            if wo.get("status") != "Draft":
                raise ValidationError(
                    f"Cannot delete Work Order {wo_id}: Only Draft work orders can be deleted."
                )

            linked_pcs = await uow.payments.list(
                {"work_order_id": wo_id, "status": {"$ne": "Cancelled"}},
                limit=1,
                session=uow.session,
            )
            if linked_pcs:
                raise ValidationError(
                    f"Cannot delete Work Order {wo_id}: It has linked Payment Certificates."
                )

            # Atomic Deletion
            success = await uow.work_orders.delete(wo_id, session=uow.session)
            if not success:
                return False

            # Audit Log
            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="DELETE",
                user_id=user["user_id"],
                project_id=project_id,
                old_value=wo,
                new_value=None,
                session=uow.session,
            )

            # Recalculate Master Budget (Track I3)
            await self.financial_service.recalculate_master_budget(
                project_id, session=uow.session
            )

            return True

    async def list_work_orders(
        self, user: dict, project_id: Optional[str], limit: int, cursor: Optional[str], vendor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        query = {"organisation_id": user["organisation_id"]}
        if project_id:
            query["project_id"] = project_id
        if vendor_id:
            query["vendor_id"] = vendor_id
        if cursor:
            query["created_at"] = {"$lt": datetime.fromisoformat(cursor)}

        docs = await self.wo_repo.list(query, sort=[("created_at", -1)], limit=limit)

        # BUG-09: Populate human-readable names for IDs to prevent UI leaks
        vendor_ids = {d["vendor_id"] for d in docs if "vendor_id" in d and ObjectId.is_valid(d["vendor_id"])}
        category_ids = {d["category_id"] for d in docs if "category_id" in d and ObjectId.is_valid(d["category_id"])}

        vendors = {}
        if vendor_ids:
            v_recs = await self.db.vendors.find({"_id": {"$in": [ObjectId(vid) for vid in vendor_ids]}}).to_list(None)
            vendors = {str(v["_id"]): v.get("name") or v.get("vendor_name", "Unknown") for v in v_recs}

        categories = {}
        if category_ids:
            # BUG-09: Category data is in 'code_master' collection, not 'categories'
            c_recs = await self.db.code_master.find({
                "$or": [
                    {"_id": {"$in": [ObjectId(cid) for cid in category_ids]}},
                    {"code": {"$in": list(category_ids)}}
                ]
            }).to_list(None)
            for c in c_recs:
                k = str(c["_id"])
                name = c.get("category_name") or c.get("name") or c.get("code") or "Unknown"
                categories[k] = name
                if "code" in c:
                    categories[c["code"]] = name

        # Ensure total_payable consistency for all docs (BUG-006)
        for doc in docs:
            if "total_payable" not in doc or FinancialEngine.to_decimal(doc.get("total_payable", 0)) == Decimal("0"):
                doc["total_payable"] = doc.get("grand_total")

            # Map IDs to names for UI safety
            if "vendor_id" in doc:
                doc["vendor_name"] = vendors.get(str(doc["vendor_id"]), "Unknown Vendor")
            if "category_id" in doc:
                doc["category_name"] = categories.get(str(doc["category_id"]), "Unknown Category")
            doc["wo_date"] = doc.get("created_at")

        # Fixed CR-23: Safe handling of empty list to prevent IndexError
        next_cursor = None
        if docs and len(docs) == limit:
            next_cursor = docs[-1]["created_at"].isoformat()

        return {"items": docs, "next_cursor": next_cursor}

    async def get_work_order(self, user: dict, wo_id: str) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        wo = None
        if ObjectId.is_valid(wo_id):
            wo = await self.wo_repo.get_by_id(wo_id, organisation_id=organisation_id)
        if not wo:
            wo = await self.wo_repo.find_one({"wo_ref": wo_id, "organisation_id": organisation_id})
        if not wo:
            raise NotFoundError("Work Order", wo_id)

        # BUG-09: Populate names for UI transparency
        if "vendor_id" in wo:
            v_id = wo["vendor_id"]
            res_id = ObjectId(v_id) if ObjectId.is_valid(v_id) else v_id
            vendor = await self.db.vendors.find_one({"_id": res_id})
            if vendor:
                wo["vendor_name"] = vendor.get("name") or vendor.get("vendor_name", "Unknown")

        if "category_id" in wo:
            v_cid = wo["category_id"]
            res_id = ObjectId(v_cid) if ObjectId.is_valid(v_cid) else None
            cat = await self.db.code_master.find_one({
                "$or": [
                    {"_id": res_id},
                    {"code": v_cid}
                ]
            })
            if cat:
                wo["category_name"] = cat.get("category_name") or cat.get("name") or cat.get("code") or "Unknown"

        # Ensure total_payable consistency (BUG-006)
        if "total_payable" not in wo or FinancialEngine.to_decimal(wo.get("total_payable", 0)) == Decimal("0"):
            wo["total_payable"] = wo.get("grand_total")

        return wo

    async def submit_work_order(self, user: dict, wo_id: str, expected_version: int) -> Dict[str, Any]:
        """Orchestrate WO submission for approval."""
        async with UnitOfWork(self.db) as uow:
            wo_data = await uow.work_orders.get_by_id(
                wo_id, organisation_id=user["organisation_id"], session=uow.session
            )
            if not wo_data:
                raise NotFoundError("Work Order", wo_id)

            # Sovereign State Transition
            StateMachine.validate_transition("WORK_ORDER", wo_data.get("status", "Draft"), "Pending")

            result = await uow.work_orders.update(
                wo_id,
                {"status": "Pending", "updated_at": datetime.now(timezone.utc), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session
            )
            if not result:
                raise ValidationError("CONFLICT: Work Order was modified by another process (Version Mismatch).")

            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="SUBMIT",
                user_id=user["user_id"],
                project_id=wo_data["project_id"],
                old_value=wo_data,
                new_value=result,
                session=uow.session
            )

            # Authoritative Recalculation
            await self.financial_service.recalculate_master_budget(
                wo_data["project_id"], session=uow.session
            )

            return result

    async def approve_work_order(self, user: dict, wo_id: str, expected_version: int) -> Dict[str, Any]:
        """Orchestrate WO approval (Admin only)."""
        # Note: Permission check should happen in Route or via permission_checker
        async with UnitOfWork(self.db) as uow:
            wo_data = await uow.work_orders.get_by_id(
                wo_id, organisation_id=user["organisation_id"], session=uow.session
            )
            if not wo_data:
                raise NotFoundError("Work Order", wo_id)

            # Sovereign State Transition
            if wo_data.get("status") != "Pending":
                raise DomainError("Only Pending Work Orders can be approved")
            StateMachine.validate_transition("WORK_ORDER", wo_data.get("status", "Draft"), "Approved")

            result = await uow.work_orders.update(
                wo_id,
                {"status": "Approved", "updated_at": datetime.now(timezone.utc), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session
            )
            if not result:
                raise ValidationError("CONFLICT: Work Order was modified by another process (Version Mismatch).")

            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="APPROVE",
                user_id=user["user_id"],
                project_id=wo_data["project_id"],
                old_value=wo_data,
                new_value=result,
                session=uow.session
            )

            # Authoritative Recalculation
            await self.financial_service.recalculate_master_budget(
                wo_data["project_id"], session=uow.session
            )

            return result

    async def cancel_work_order(self, user: dict, wo_id: str, expected_version: int) -> Dict[str, Any]:
        """Orchestrate WO cancellation."""
        async with UnitOfWork(self.db) as uow:
            wo_data = await uow.work_orders.get_by_id(
                wo_id, organisation_id=user["organisation_id"], session=uow.session
            )
            if not wo_data:
                raise NotFoundError("Work Order", wo_id)

            # Sovereign State Transition
            StateMachine.validate_transition("WORK_ORDER", wo_data.get("status", "Draft"), "Cancelled")

            result = await uow.work_orders.update(
                wo_id,
                {"status": "Cancelled", "updated_at": datetime.now(timezone.utc), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session
            )
            if not result:
                raise ValidationError("CONFLICT: Work Order was modified by another process (Version Mismatch).")

            # Reverse budget commitment? (Optional depending on business rule, but common)
            # For now just status change as per plan

            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="CANCEL",
                user_id=user["user_id"],
                project_id=wo_data["project_id"],
                old_value=wo_data,
                new_value=result,
                session=uow.session
            )

            # Authoritative Recalculation
            await self.financial_service.recalculate_master_budget(
                wo_data["project_id"], session=uow.session
            )

            return result

    async def reject_work_order(self, user: dict, wo_id: str, expected_version: int) -> Dict[str, Any]:
        """Orchestrate WO rejection (Admin only)."""
        async with UnitOfWork(self.db) as uow:
            wo_data = await uow.work_orders.get_by_id(
                wo_id, organisation_id=user["organisation_id"], session=uow.session
            )
            if not wo_data:
                raise NotFoundError("Work Order", wo_id)

            # Sovereign State Transition
            StateMachine.validate_transition("WORK_ORDER", wo_data.get("status", "Draft"), "Rejected")

            result = await uow.work_orders.update(
                wo_id,
                {"status": "Rejected", "updated_at": datetime.now(timezone.utc), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session
            )
            if not result:
                raise ValidationError("CONFLICT: Work Order was modified by another process (Version Mismatch).")

            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="REJECT",
                user_id=user["user_id"],
                project_id=wo_data["project_id"],
                old_value=wo_data,
                new_value=result,
                session=uow.session
            )

            # Authoritative Recalculate
            await self.financial_service.recalculate_master_budget(
                wo_data["project_id"], session=uow.session
            )

            return result

    async def complete_work_order(self, user: dict, wo_id: str, expected_version: int) -> Dict[str, Any]:
        """Transition WO to Completed status."""
        async with UnitOfWork(self.db) as uow:
            wo_data = await uow.work_orders.get_by_id(
                wo_id, organisation_id=user["organisation_id"], session=uow.session
            )
            if not wo_data:
                raise NotFoundError("Work Order", wo_id)

            StateMachine.validate_transition("WORK_ORDER", wo_data.get("status", "Draft"), "Completed")

            result = await uow.work_orders.update(
                wo_id,
                {"status": "Completed", "updated_at": datetime.now(timezone.utc), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session
            )
            if not result:
                raise ValidationError("CONFLICT: Work Order was modified by another process.")

            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="COMPLETE",
                user_id=user["user_id"],
                project_id=wo_data["project_id"],
                old_value=wo_data,
                new_value=result,
                session=uow.session
            )
            return result

    async def close_work_order(self, user: dict, wo_id: str, expected_version: int) -> Dict[str, Any]:
        """Transition WO to Closed status (Final)."""
        async with UnitOfWork(self.db) as uow:
            wo_data = await uow.work_orders.get_by_id(
                wo_id, organisation_id=user["organisation_id"], session=uow.session
            )
            if not wo_data:
                raise NotFoundError("Work Order", wo_id)

            StateMachine.validate_transition("WORK_ORDER", wo_data.get("status", "Draft"), "Closed")

            result = await uow.work_orders.update(
                wo_id,
                {"status": "Closed", "updated_at": datetime.now(timezone.utc), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session
            )
            if not result:
                raise ValidationError("CONFLICT: Work Order was modified by another process.")

            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="WORK_ORDERS",
                entity_type="WORK_ORDER",
                entity_id=wo_id,
                action_type="CLOSE",
                user_id=user["user_id"],
                project_id=wo_data["project_id"],
                old_value=wo_data,
                new_value=result,
                session=uow.session
            )
            return result
