import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.core.idempotency import IdempotencyGuard
from app.core.storage import storage_manager
from app.core.time import now
from app.core.uow import UnitOfWork
import uuid

# Note: Repositories from other contexts
from app.modules.project.infrastructure.repository import ProjectRepository
from app.modules.shared.domain.exceptions import NotFoundError, ValidationError
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.shared.domain.state_machine import StateMachine
from app.modules.shared.infrastructure.sequence_repo import SequenceRepository

from ..infrastructure.repository import PCRepository
from ..schemas.dto import PaymentCertificateCreate

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

    async def list_payment_certificates(
        self, user: dict, project_id: Optional[str], limit: int, cursor: Optional[str], vendor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if project_id:
            await self.permission_checker.check_project_access(user, project_id)

        query = {"organisation_id": user["organisation_id"]}
        if project_id:
            query["project_id"] = project_id
        if vendor_id:
            query["vendor_id"] = vendor_id

        if cursor:
            try:
                parsed_cursor = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
                query["created_at"] = {"$lt": parsed_cursor}
            except ValueError:
                raise ValidationError("Invalid cursor format")

        docs = await self.pc_repo.list(query, sort=[("created_at", -1)], limit=limit)

        # Populate names for UI transparency
        vendor_ids = {str(d["vendor_id"]) for d in docs if d.get("vendor_id")}
        cat_ids = {str(d["category_id"]) for d in docs if d.get("category_id")}

        vendors = {}
        if vendor_ids:
            v_ids = [ObjectId(v) for v in vendor_ids if ObjectId.is_valid(v)]
            v_docs = await self.db.vendors.find({"_id": {"$in": v_ids}}).to_list(None)
            vendors = {str(v["_id"]): v.get("name") or v.get("vendor_name", "Unknown") for v in v_docs}

        categories = {}
        if cat_ids:
            c_ids = [ObjectId(c) for c in cat_ids if ObjectId.is_valid(c)]
            c_query = {"$or": [{"_id": {"$in": c_ids}}, {"code": {"$in": list(cat_ids)}}]}
            c_docs = await self.db.code_master.find(c_query).to_list(None)
            categories = {str(c["_id"]): c.get("category_name") or c.get("name") or c.get("code") for c in c_docs}
            for c in c_docs:
                if "code" in c:
                    categories[c["code"]] = c.get("category_name") or c.get("name") or c["code"]

        for doc in docs:
            if "vendor_id" in doc:
                doc["vendor_name"] = vendors.get(str(doc["vendor_id"]), "Unknown Vendor")
            if "category_id" in doc:
                doc["category_name"] = categories.get(str(doc["category_id"]), "Unknown Category")
            raw_cert_date = doc.get("approved_at") or doc.get("submitted_at") or doc.get("created_at") or doc.get("updated_at") or datetime.now(timezone.utc)
            doc["certification_date"] = raw_cert_date.isoformat() if isinstance(raw_cert_date, datetime) else str(raw_cert_date)
            if "created_at" in doc and isinstance(doc["created_at"], datetime):
                doc["created_at"] = doc["created_at"].isoformat()

        next_cursor = None
        if len(docs) == limit:
            last_doc = docs[-1]
            ts = last_doc.get("created_at")
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()
            elif isinstance(ts, str):
                next_cursor = ts

        return {"items": docs, "next_cursor": next_cursor}

    async def create_payment_certificate(
        self, user: dict, pc_data: PaymentCertificateCreate
    ) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        idempotency_key = pc_data.idempotency_key
        project_id = pc_data.project_id

        await self.permission_checker.check_project_access(
            user, project_id, require_write=True
        )

        fund_request = pc_data.fund_request
        pc_type = "PETTY_OVH" if fund_request else "WO_LINKED"

        # BUG-29: Validate document schema and project invariants via authoritative service
        doc_data = pc_data.model_dump()
        doc_data["pc_type"] = pc_type
        await self.financial_service.validate_financial_document("PAYMENT_CERTIFICATE", doc_data, project_id)

        async with UnitOfWork(self.db) as uow:
            if idempotency_key:
                from app.core.idempotency import get_recorded_operation
                existing_op = await get_recorded_operation(
                    uow.session, idempotency_key, organisation_id
                )
                if existing_op:
                    logging.info(f"Idempotency hit for key: {idempotency_key}")
                    return existing_op.get("result")

            project = await uow.projects.get_by_id(
                project_id, organisation_id=organisation_id, session=uow.session
            )
            cgst_pct = (
                Decimal(str(project.get("project_cgst_percentage", "9.0")))
                if project
                else Decimal("9.0")
            )
            sgst_pct = (
                Decimal(str(project.get("project_sgst_percentage", "9.0")))
                if project
                else Decimal("9.0")
            )

            # J1: Mode B Category/Allocation Validation
            if fund_request:
                # 1. Verify Category budget_type
                if not pc_data.category_id:
                    raise ValidationError("Category ID is required for Fund Request")
                category = await uow.code_master.get_by_id(pc_data.category_id, session=uow.session)
                if not category:
                    category = await uow.code_master.find_one({"code": pc_data.category_id}, session=uow.session)

                if not category:
                    raise ValidationError(f"Category {pc_data.category_id} not found")

                if category.get("budget_type") != "fund_transfer":
                    raise ValidationError("Fund request category must be of type 'fund_transfer'")

                pc_data.category_id = category["code"]  # Store the Code for consistent lookups (Point 75)

                # 2. CALC-5: allocation_remaining > 0
                allocation = await uow.fund_allocations.find_one(
                    {"project_id": project_id, "category_id": pc_data.category_id},
                    session=uow.session
                )
                if not allocation:
                    raise ValidationError(f"Fund allocation for category {pc_data.category_id} not initialized")

                remaining = FinancialEngine.to_decimal(allocation.get("allocation_remaining", 0))
                if remaining <= 0:
                    raise ValidationError("Cannot raise PC: no allocation remaining")

            subtotal = Decimal("0.0")
            line_items_processed = []
            for item in pc_data.line_items:
                qty = FinancialEngine.to_decimal(item.qty)
                rate = FinancialEngine.to_decimal(item.rate)
                item_total = FinancialEngine.round(qty * rate)
                item.total = item_total
                subtotal += item_total
                item_dict = item.model_dump()
                item_dict["total"] = FinancialEngine.to_d128(item_total)
                line_items_processed.append(item_dict)

            fin = FinancialEngine.calculate_pc_financials(
                pc_value=subtotal,
                retention_pct=FinancialEngine.to_decimal(pc_data.retention_percent or 0),
                cgst_pct=cgst_pct,
                sgst_pct=sgst_pct,
            )

            # BUG-016: Over-certification guard
            if not fund_request and pc_data.work_order_id:
                summary = await self.get_wo_certification_summary(user, pc_data.work_order_id)
                new_total = FinancialEngine.to_decimal(summary["previously_certified"]) + fin["grand_total"]
                wo_total = FinancialEngine.to_decimal(summary["wo_grand_total"])
                if new_total > wo_total:
                    overage = new_total - wo_total
                    logger.warning(f"Over-certification: WO {pc_data.work_order_id} by {overage}")
                    raise ValidationError(
                        f"This PC (₹{fin['grand_total']}) would exceed WO total by ₹{overage:.2f}. "
                        f"Previously: ₹{summary['previously_certified']:.2f}, "
                        f"WO Total: ₹{summary['wo_grand_total']:.2f}"
                    )

            # Use modular seq repo
            pc_ref_id = f"pc_seq_{organisation_id}"
            next_seq = await uow.sequences.get_next_sequence(
                pc_ref_id, session=uow.session
            )
            pc_ref = f"PC-{next_seq:04d}"

            pc_dict = pc_data.model_dump()
            pc_dict.update(
                {
                    "organisation_id": organisation_id,
                    "pc_ref": pc_ref,
                    "pc_type": pc_type,  # Mode identification
                    "subtotal": FinancialEngine.to_d128(fin["subtotal"]),
                    "retention_amount": FinancialEngine.to_d128(
                        fin["retention_amount"]
                    ),
                    "total_after_retention": FinancialEngine.to_d128(
                        fin["actual_payable"]
                    ),
                    "cgst": FinancialEngine.to_d128(fin["cgst"]),
                    "sgst": FinancialEngine.to_d128(fin["sgst"]),
                    "grand_total": FinancialEngine.to_d128(fin["grand_total"]),
                    "total_payable": FinancialEngine.to_d128(fin["actual_payable"]),
                    "retention_percent": FinancialEngine.to_d128(
                        Decimal(str(pc_data.retention_percent or 0))
                    ),
                    "status": "Draft",
                    "line_items": line_items_processed,
                    "version": 1,
                    "created_at": now(),
                    "updated_at": now(),
                }
            )

            new_pc = await uow.payments.create(pc_dict, session=uow.session)

            # Calculate initial base_page_count for UI consistency (Point 98)
            try:
                await self.refresh_base_page_count(user, new_pc["id"])
            except Exception as e:
                logger.warning(
                    f"Failed to refresh base_page_count for new PC {new_pc['id']}: {e}"
                )

            # Update last_pc_created_at for timer tracking (Notebook Truth Scenario 3)
            if fund_request:
                await uow.db.fund_allocations.update_one(
                    {"project_id": project_id, "category_id": pc_data.category_id},
                    {"$set": {"last_pc_created_at": now()}},
                    session=uow.session
                )

            if idempotency_key:
                from app.core.idempotency import record_operation

                await record_operation(
                    self.db,
                    uow.session,
                    idempotency_key,
                    "PAYMENT_CERTIFICATE",
                    response_payload=new_pc,
                )

            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=new_pc["id"],
                action_type="CREATE",
                user_id=user["user_id"],
                project_id=project_id,
                new_value=new_pc,
                session=uow.session,
            )

            return new_pc

    async def mark_as_paid(self, user: dict, pc_id: str, expected_version: int) -> Dict[str, Any]:
        """Finalize payment (Approved/Processing -> Paid). Updates all downstream financial ledgers."""
        organisation_id = user["organisation_id"]

        async with UnitOfWork(self.db) as uow:
            pc = await uow.payments.get_by_id(
                pc_id, organisation_id=organisation_id, session=uow.session
            )
            if not pc:
                raise NotFoundError("Payment Certificate", pc_id)

            await self.permission_checker.check_project_access(
                user, pc["project_id"], require_write=True
            )

            # Authoritative State Validation (BUG-RECONCILE)
            current_status = pc.get("status", "Draft")
            if not pc.get("fund_request"):
                StateMachine.validate_transition("PAYMENT", current_status, "Paid")
            else:
                if current_status not in ("Draft", "Paid"):
                    raise ValidationError(f"Invalid status '{current_status}' for Mode B PC closure.")

            grand_total = Decimal(str(pc["grand_total"]))
            retention_amount = Decimal(str(pc["retention_amount"]))
            project_id = pc["project_id"]
            pc_type = pc.get("pc_type", "WO_LINKED")

            updated_pc = await uow.payments.update(
                pc_id,
                {"status": "Paid", "paid_at": now(), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session,
            )
            if not updated_pc:
                raise ValidationError(
                    "CONFLICT: Payment Certificate was modified by another process (Version Mismatch)."
                )

            if pc_type == "WO_LINKED" and pc.get("vendor_id"):
                await uow.vendors.update_one(
                    {"_id": ObjectId(pc["vendor_id"])},
                    {
                        "$inc": {
                            "total_payable": FinancialEngine.to_d128(-grand_total),
                            "retention_held": FinancialEngine.to_d128(
                                -retention_amount
                            ),
                        }
                    },
                    session=uow.session,
                )

            if pc_type == "PETTY_OVH":
                category_id = pc.get("category_id")
                fund_alloc = await uow.fund_allocations.find_one(
                    {"project_id": project_id, "category_id": category_id}, session=uow.session
                )
                if fund_alloc:
                    alloc_original = FinancialEngine.to_decimal(
                        fund_alloc.get("allocation_original", 0)
                    )
                    new_received = (
                        FinancialEngine.to_decimal(
                            fund_alloc.get("allocation_received", 0)
                        )
                        + grand_total
                    )
                    # §5.2: allocation_remaining = allocation_original - allocation_received
                    new_remaining = alloc_original - new_received
                    new_cash = (
                        FinancialEngine.to_decimal(fund_alloc.get("cash_in_hand", 0))
                        + grand_total
                    )
                    await uow.fund_allocations.update(
                        fund_alloc["id"],
                        {
                            "allocation_received": FinancialEngine.to_d128(
                                new_received
                            ),
                            "allocation_remaining": FinancialEngine.to_d128(
                                new_remaining
                            ),
                            "cash_in_hand": FinancialEngine.to_d128(new_cash),
                            "last_pc_paid_date": now(),
                        },
                        session=uow.session,
                    )

                    old_cash = FinancialEngine.to_decimal(fund_alloc.get("cash_in_hand", 0))
                    await self.audit_service.evaluate_and_log_petty_cash_alert(
                        organisation_id=organisation_id,
                        user_id=user["user_id"],
                        project_id=project_id,
                        category_id=category_id,
                        old_cash=old_cash,
                        new_cash=new_cash,
                        session=uow.session,
                    )

                    await uow.cash_transactions.create({
                        "project_id": project_id,
                        "category_id": category_id,
                        "amount": FinancialEngine.to_d128(grand_total),
                        "type": "CREDIT",
                        "flow_direction": "INFLOW",
                        "description": f"Replenishment via PC {pc['pc_ref']}",
                        "transaction_date": now(),
                        "created_by": user["user_id"],
                        "organisation_id": organisation_id
                    }, session=uow.session)

            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=pc_id,
                action_type="MARK_AS_PAID",
                user_id=user["user_id"],
                project_id=project_id,
                new_value=updated_pc,
                session=uow.session,
            )

            # C2: Write Vendor Ledger Entry (PAYMENT_MADE)
            if pc_type == "WO_LINKED" and pc.get("vendor_id"):
                await uow.ledger.create({
                    "vendor_id": str(pc["vendor_id"]),
                    "project_id": project_id,
                    "ref_id": pc_id,
                    "entry_type": "PAYMENT_MADE",
                    "flow_direction": "OUTFLOW",
                    "amount": FinancialEngine.to_d128(grand_total),
                    "created_at": now()
                }, session=uow.session)

                # J2: If retention, track it
                if retention_amount > 0:
                    await uow.ledger.create({
                        "vendor_id": str(pc["vendor_id"]),
                        "project_id": project_id,
                        "ref_id": pc_id,
                        "entry_type": "RETENTION_HELD",
                        "flow_direction": "INFLOW",
                        "amount": FinancialEngine.to_d128(retention_amount),
                        "created_at": now()
                    }, session=uow.session)

            # Final Authoritative Recalculation for Project
            await self.financial_service.recalculate_master_budget(
                project_id, session=uow.session
            )

            return {"status": "success", "message": "PC marked as paid and financials updated"}

    async def get_payment_certificate(self, user: dict, pc_id: str) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        pc = await self.pc_repo.get_by_id(pc_id, organisation_id=organisation_id)
        if not pc:
            raise NotFoundError("Payment Certificate", pc_id)

        # Ensure total_payable is populated for frontend (Point 3.3/75 consistency)
        if "total_payable" not in pc:
            pc["total_payable"] = pc.get("grand_total") or pc.get("total_after_retention", 0)

        # BUG-09: Populate names for UI transparency
        if "vendor_id" in pc:
            v_id = pc["vendor_id"]
            res_id = ObjectId(v_id) if ObjectId.is_valid(v_id) else v_id
            vendor = await self.db.vendors.find_one({"_id": res_id})
            if vendor:
                pc["vendor_name"] = vendor.get("name") or vendor.get("vendor_name", "Unknown")

        if "category_id" in pc:
            v_cid = pc["category_id"]
            res_id = ObjectId(v_cid) if ObjectId.is_valid(v_cid) else None
            cat = await self.db.code_master.find_one(
                {"$or": [{"_id": res_id}, {"code": v_cid}]}
            )
            if cat:
                pc["category_name"] = cat.get("category_name") or cat.get("name") or cat.get("code") or "Unknown"

        return pc

    async def get_wo_certification_summary(self, user: dict, work_order_id: str) -> Dict:
        """Aggregate all non-cancelled PCs against a WO to return certified-to-date."""
        pipeline = [
            {"$match": {
                "work_order_id": work_order_id,
                "organisation_id": user["organisation_id"],
                "status": {"$in": ["Approved", "Payment Raised", "Processing", "Paid"]}
            }},
            {"$group": {"_id": None, "total_certified": {"$sum": "$grand_total"}, "pc_count": {"$sum": 1}}}
        ]
        result = await self.db.payment_certificates.aggregate(pipeline).to_list(1)
        agg = result[0] if result else {"total_certified": 0, "pc_count": 0}

        # Fetch WO grand_total
        wo = await self.db.work_orders.find_one({"_id": ObjectId(work_order_id)})
        wo_total = FinancialEngine.to_decimal(wo.get("grand_total", 0)) if wo else Decimal("0")
        certified = FinancialEngine.to_decimal(agg["total_certified"])

        return {
            "work_order_id": work_order_id,
            "wo_grand_total": float(wo_total),
            "previously_certified": float(certified),
            "balance_remaining": float(wo_total - certified),
            "pc_count": agg["pc_count"],
        }

    # -------------------------------------------------------------------------
    # APPROVAL WORKFLOW METHODS
    # -------------------------------------------------------------------------

    async def submit_for_approval(
        self, user: dict, payment_id: str, expected_version: int, idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit payment for approval (Draft -> Submitted).
        Validates state transition and records idempotency."""
        organisation_id = user["organisation_id"]
        user_id = user["user_id"]
        idempotency_guard = IdempotencyGuard(self.db)

        async with UnitOfWork(self.db) as uow:
            # Check idempotency first
            if idempotency_key:
                recorded = await idempotency_guard.get_or_set(
                    idempotency_key,
                    {"payment_id": payment_id, "action": "SUBMIT"},
                    session=uow.session,
                )
                if recorded:
                    return recorded

            payment = await uow.payments.get_by_id(
                payment_id, organisation_id=organisation_id, session=uow.session
            )
            if not payment:
                raise NotFoundError("Payment", payment_id)

            current_status = payment.get("status", "Draft")
            StateMachine.validate_transition("PAYMENT", current_status, "Submitted")

            updated = await uow.payments.update(
                payment_id,
                {"status": "Submitted", "submitted_at": now(), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session,
            )
            if not updated:
                raise ValidationError(
                    "CONFLICT: Payment Certificate was modified by another process (Version Mismatch)."
                )

            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=payment_id,
                action_type="SUBMIT",
                user_id=user_id,
                project_id=payment.get("project_id"),
                old_value=payment,
                new_value=updated,
                session=uow.session,
            )

            if idempotency_key:
                await idempotency_guard.finalize(
                    idempotency_key,
                    {"payment_id": payment_id, "action": "SUBMIT"},
                    response=updated,
                    session=uow.session,
                )

            return updated

    async def approve_payment(
        self, user: dict, payment_id: str, expected_version: int, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve payment (Submitted -> Approved).
        Role-based threshold: Supervisor max $10k, Finance Manager/Lead unlimited."""
        organisation_id = user["organisation_id"]
        approver_id = user["user_id"]
        approver_role = user.get("role", "Unknown")

        async with UnitOfWork(self.db) as uow:
            payment = await uow.payments.get_by_id(
                payment_id, organisation_id=organisation_id, session=uow.session
            )
            if not payment:
                raise NotFoundError("Payment", payment_id)

            current_status = payment.get("status", "Draft")
            StateMachine.validate_transition("PAYMENT", current_status, "Approved")

            amount = Decimal(str(payment.get("grand_total", 0)))
            if approver_role == "Supervisor" and amount > Decimal("10000"):
                raise ValidationError(
                    f"Supervisor can only approve payments <= $10k. This payment is ${amount}."
                )

            approval_event = {
                "approver_id": approver_id,
                "approval_date": now(),
                "status": "Approved",
                "approver_role": approver_role,
                "comment": comment,
            }

            approval_trail = list(payment.get("approval_trail", []))
            approval_trail.append(approval_event)

            updated = await uow.payments.update(
                payment_id,
                {
                    "status": "Approved",
                    "approved_at": now(),
                    "approved_by": approver_id,
                    "approval_trail": approval_trail,
                    "version": expected_version + 1,
                },
                expected_version=expected_version,
                session=uow.session,
            )
            if not updated:
                raise ValidationError(
                    "CONFLICT: Payment Certificate was modified by another process (Version Mismatch)."
                )

            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=payment_id,
                action_type="APPROVE",
                user_id=approver_id,
                project_id=payment.get("project_id"),
                old_value=payment,
                new_value=updated,
                session=uow.session,
            )

            # C2: Write Vendor Ledger Entry (PC_CERTIFIED)
            if updated.get("vendor_id"):
                await uow.ledger.create({
                    "vendor_id": str(updated["vendor_id"]),
                    "project_id": updated["project_id"],
                    "ref_id": str(updated["id"]),
                    "entry_type": "PC_CERTIFIED",
                    "flow_direction": "INFLOW",
                    "amount": FinancialEngine.to_d128(amount),
                    "created_at": now()
                }, session=uow.session)

            # Authoritative Recalculation
            await self.financial_service.recalculate_master_budget(
                updated["project_id"], session=uow.session
            )

            return updated

    async def reject_payment(
        self, user: dict, payment_id: str, expected_version: int, reason: str
    ) -> Dict[str, Any]:
        """Reject payment (Submitted -> Rejected)."""
        organisation_id = user["organisation_id"]
        rejecter_id = user["user_id"]
        rejecter_role = user.get("role", "Unknown")

        async with UnitOfWork(self.db) as uow:
            payment = await uow.payments.get_by_id(
                payment_id, organisation_id=organisation_id, session=uow.session
            )
            if not payment:
                raise NotFoundError("Payment", payment_id)

            current_status = payment.get("status", "Draft")
            StateMachine.validate_transition("PAYMENT", current_status, "Rejected")

            rejection_event = {
                "approver_id": rejecter_id,
                "approval_date": now(),
                "status": "Rejected",
                "approver_role": rejecter_role,
                "comment": reason,
            }

            approval_trail = list(payment.get("approval_trail", []))
            approval_trail.append(rejection_event)

            updated = await uow.payments.update(
                payment_id,
                {
                    "status": "Rejected",
                    "rejected_at": now(),
                    "rejected_reason": reason,
                    "approval_trail": approval_trail,
                    "version": expected_version + 1,
                },
                expected_version=expected_version,
                session=uow.session,
            )
            if not updated:
                raise ValidationError(
                    "CONFLICT: Payment Certificate was modified by another process (Version Mismatch)."
                )

            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=payment_id,
                action_type="REJECT",
                user_id=rejecter_id,
                project_id=payment.get("project_id"),
                old_value=payment,
                new_value=updated,
                session=uow.session,
            )

            return updated

    async def raise_payment(
        self, user: dict, payment_id: str, expected_version: int, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Raise payment (Approved -> Payment Raised)."""
        organisation_id = user["organisation_id"]
        raiser_id = user["user_id"]
        raiser_role = user.get("role", "Unknown")

        async with UnitOfWork(self.db) as uow:
            payment = await uow.payments.get_by_id(
                payment_id, organisation_id=organisation_id, session=uow.session
            )
            if not payment:
                raise NotFoundError("Payment", payment_id)

            current_status = payment.get("status", "Draft")
            StateMachine.validate_transition("PAYMENT", current_status, "Payment Raised")

            raise_event = {
                "approver_id": raiser_id,
                "approval_date": now(),
                "status": "Payment Raised",
                "approver_role": raiser_role,
                "comment": comment,
            }

            approval_trail = list(payment.get("approval_trail", []))
            approval_trail.append(raise_event)

            updated = await uow.payments.update(
                payment_id,
                {
                    "status": "Payment Raised",
                    "payment_raised_at": now(),
                    "payment_raised_by": raiser_id,
                    "approval_trail": approval_trail,
                    "version": expected_version + 1,
                },
                expected_version=expected_version,
                session=uow.session,
            )
            if not updated:
                raise ValidationError(
                    "CONFLICT: Payment Certificate was modified by another process (Version Mismatch)."
                )

            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=payment_id,
                action_type="RAISE_PAYMENT",
                user_id=raiser_id,
                project_id=payment.get("project_id"),
                old_value=payment,
                new_value=updated,
                session=uow.session,
            )

            return updated

    async def get_pending_approvals(
        self, user: dict, project_id: str
    ) -> List[Dict[str, Any]]:
        """List payments pending approval for the current user (based on role + threshold)."""
        organisation_id = user["organisation_id"]
        approver_role = user.get("role", "Unknown")

        query = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "status": "Submitted",
        }

        docs = await self.pc_repo.list(query, limit=100)

        filtered = []
        for doc in docs:
            amount = Decimal(str(doc.get("grand_total", 0)))
            if approver_role == "Supervisor" and amount > Decimal("10000"):
                continue
            filtered.append(doc)

        return filtered

    async def get_approval_history(
        self, user: dict, payment_id: str
    ) -> List[Dict[str, Any]]:
        """Return approval_trail for a payment."""
        organisation_id = user["organisation_id"]

        payment = await self.pc_repo.get_by_id(payment_id, organisation_id=organisation_id)
        if not payment:
            raise NotFoundError("Payment", payment_id)

        return payment.get("approval_trail", [])

    async def attach_document(
        self, user: dict, pc_id: str, file_name: str, file_content: bytes
    ) -> Dict[str, Any]:
        """Attach a supporting PDF document to a payment certificate."""
        organisation_id = user["organisation_id"]

        # Validate PC existence and access
        pc = await self.pc_repo.get_by_id(pc_id, organisation_id=organisation_id)
        if not pc:
            raise NotFoundError("Payment Certificate", pc_id)

        await self.permission_checker.check_project_access(
            user, pc["project_id"], require_write=True
        )

        # 1. Calculate page count using pypdf
        import io
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(file_content))
            page_count = len(reader.pages)
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise ValidationError("Invalid PDF file")

        # 2. Save to storage
        file_ext = file_name.split(".")[-1] if "." in file_name else "pdf"
        file_id = str(uuid.uuid4())
        relative_path = f"organisations/{organisation_id}/payments/{pc_id}/{file_id}.{file_ext}"
        await storage_manager.save_file(file_content, relative_path)

        # 3. Update PC record
        new_doc = {
            "file_id": file_id,
            "original_name": file_name,
            "file_path": relative_path,
            "page_count": page_count,
            "uploaded_at": now(),
        }

        await self.pc_repo.update_one(
            {"_id": pc_id, "organisation_id": organisation_id},
            {"$push": {"additional_documents": new_doc}}
        )

        # 4. Refresh base_page_count in case the main document list was updated
        try:
            await self.refresh_base_page_count(user, pc_id)
        except Exception as e:
            logger.warning(f"Failed to refresh base_page_count after attachment: {e}")

        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="PAYMENT_CERTIFICATE",
            entity_id=pc_id,
            action_type="ATTACH_DOCUMENT",
            user_id=user["user_id"],
            project_id=pc["project_id"],
            new_value=new_doc,
        )

        return new_doc

    async def delete_document(self, user: dict, pc_id: str, file_id: str) -> bool:
        """Delete a supporting document from a payment certificate."""
        organisation_id = user["organisation_id"]
        pc = await self.pc_repo.get_by_id(pc_id, organisation_id=organisation_id)
        if not pc:
            raise NotFoundError("Payment Certificate", pc_id)

        await self.permission_checker.check_project_access(
            user, pc["project_id"], require_write=True
        )

        docs = list(pc.get("additional_documents") or [])
        doc_to_delete = next((d for d in docs if d["file_id"] == file_id), None)

        if not doc_to_delete:
            raise NotFoundError("Attachment", file_id)

        # 1. Delete from storage
        try:
            await storage_manager.delete_file(doc_to_delete["file_path"])
        except Exception as e:
            logger.error(f"Failed to delete file {file_id} from storage: {e}")

        # 2. Update DB atomically
        await self.pc_repo.update_one(
            {"_id": pc_id, "organisation_id": organisation_id},
            {"$pull": {"additional_documents": {"file_id": file_id}}}
        )

        # 3. Refresh base_page_count in case the main document list was updated
        try:
            await self.refresh_base_page_count(user, pc_id)
        except Exception as e:
            logger.warning(f"Failed to refresh base_page_count after deletion: {e}")

        # 4. Log audit action
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="PAYMENT_CERTIFICATE",
            entity_id=pc_id,
            action_type="DELETE_DOCUMENT",
            user_id=user["user_id"],
            project_id=pc["project_id"],
            old_value=doc_to_delete,
        )

        return True

    async def refresh_base_page_count(self, user: dict, pc_id: str):
        """
        Calculates and updates the base page count for a payment certificate.
        Ensures the UI always knows where attachments begin.
        """
        from app.core.template_export_service import TemplateExportService
        organisation_id = user["organisation_id"]

        pc = await self.get_payment_certificate(user, pc_id)
        enriched_pc = await self.prepare_pc_for_export(user, pc)

        # Dry run export to get exact page count of the main document
        _, base_count = TemplateExportService.export_payment_certificate_exact(
            enriched_pc, fmt="pdf", attachments=[], return_metadata=True
        )

        await self.pc_repo.update(
            pc_id,
            {"base_page_count": base_count, "updated_at": now()},
            organisation_id=organisation_id
        )
        return base_count

    async def update_base_page_count(self, user: dict, pc_id: str, page_count: int):
        """Update the base page count for the PC document itself."""
        organisation_id = user["organisation_id"]
        await self.pc_repo.update(
            pc_id,
            {"base_page_count": page_count, "updated_at": now()},
            organisation_id=organisation_id
        )

    async def prepare_pc_for_export(self, user: dict, pc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriches PC data with vendor, category, and company details for export.
        This ensures consistent PDF generation across routes.
        """
        organisation_id = user["organisation_id"]

        # 1. Vendor enrichment
        vendor_id = pc.get("vendor_id")
        if vendor_id:
            try:
                v_oid = ObjectId(vendor_id) if ObjectId.is_valid(vendor_id) else None
                if v_oid:
                    vendor = await self.db.vendors.find_one({"_id": v_oid})
                    if vendor:
                        pc["vendor"] = vendor
                    else:
                        pc["vendor"] = {"name": pc.get("vendor_name", "Unknown"), "gst_no": ""}
                else:
                    pc["vendor"] = {"name": pc.get("vendor_name", "Unknown"), "gst_no": ""}
            except Exception:
                pc["vendor"] = {"name": pc.get("vendor_name", "Unknown"), "gst_no": ""}
        else:
            pc["vendor"] = {"name": pc.get("vendor_name", "Unknown"), "gst_no": ""}

        # 2. Category enrichment
        category_id = pc.get("category_id")
        if category_id:
            try:
                c_query = {
                    "$or": [
                        {"_id": ObjectId(category_id) if ObjectId.is_valid(category_id) else None},
                        {"code": category_id}
                    ]
                }
                category = await self.db.code_master.find_one(c_query)
                if category:
                    pc["category"] = category
                    pc["code"] = category.get("code", "")
                else:
                    pc["category"] = {}
                    pc["code"] = pc.get("code", "")
            except Exception:
                pc["category"] = {}
                pc["code"] = pc.get("code", "")
        else:
            pc["category"] = {}
            pc["code"] = pc.get("code", "")

        # 3. Default date
        if "pc_date" not in pc:
            pc["pc_date"] = pc.get("created_at", now())

        # 4. Company details
        settings = await self.db.organisation_settings.find_one({"organisation_id": organisation_id})
        if settings:
            pc["company"] = {
                "name": settings.get("name", "Third Angle Concepts (PMC)"),
                "address": settings.get("address", ""),
                "gst_number": settings.get("gst_number", ""),
                "pan_number": settings.get("pan_number", ""),
                "email": settings.get("email", ""),
                "phone": settings.get("phone", "")
            }
        else:
            is_oid = ObjectId.is_valid(organisation_id)
            query = {"_id": ObjectId(organisation_id)} if is_oid else {"organisation_id": organisation_id}
            org = await self.db.organisations.find_one(query)
            pc["company"] = {"name": org.get("name") if org else "Third Angle Concepts (PMC)", "address": ""}

        return pc
