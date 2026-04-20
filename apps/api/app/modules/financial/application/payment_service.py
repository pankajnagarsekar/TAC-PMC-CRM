import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.core.idempotency import IdempotencyGuard
from app.core.time import now
from app.core.uow import UnitOfWork

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
        self, user: dict, project_id: str, limit: int, cursor: Optional[str]
    ) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)

        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
        if cursor:
            try:
                parsed_cursor = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
                query["created_at"] = {"$lt": parsed_cursor}
            except ValueError:
                raise ValidationError("Invalid cursor format")

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
        doc_data = pc_data.dict()
        doc_data["pc_type"] = pc_type
        await self.financial_service.validate_financial_document("PAYMENT_CERTIFICATE", doc_data, project_id)

        async with UnitOfWork(self.db) as uow:
            if idempotency_key:
                from app.core.idempotency import get_recorded_operation

                recorded = await get_recorded_operation(
                    self.db, uow.session, idempotency_key
                )
                if recorded:
                    return recorded

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
                category = await uow.code_master.get_by_id(pc_data.category_id, session=uow.session)
                if not category:
                    category = await uow.code_master.find_one({"code": pc_data.category_id}, session=uow.session)
                
                if not category:
                    raise ValidationError(f"Category {pc_data.category_id} not found")
                
                if category.get("budget_type") != "fund_transfer":
                    raise ValidationError("Fund request category must be of type 'fund_transfer'")
                
                pc_data.category_id = category["code"] # Store the Code for consistent lookups (Point 75)
                
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
                qty = Decimal(str(item.qty))
                rate = Decimal(str(item.rate))
                item_total = FinancialEngine.round(qty * rate)
                item.total = item_total
                subtotal += item_total
                item_dict = item.dict()
                item_dict["total"] = FinancialEngine.to_d128(item_total)
                line_items_processed.append(item_dict)

            fin = FinancialEngine.calculate_pc_financials(
                pc_value=subtotal,
                retention_pct=Decimal(str(pc_data.retention_percent or 0)),
                cgst_pct=cgst_pct,
                sgst_pct=sgst_pct,
            )

            # Use modular seq repo
            pc_ref_id = f"pc_seq_{organisation_id}"
            next_seq = await uow.sequences.get_next_sequence(
                pc_ref_id, session=uow.session
            )
            pc_ref = f"PC-{next_seq:04d}"

            pc_dict = pc_data.dict()
            pc_dict.update(
                {
                    "organisation_id": organisation_id,
                    "pc_ref": pc_ref,
                    "pc_type": pc_type, # Mode identification
                    "subtotal": FinancialEngine.to_d128(fin["subtotal"]),
                    "retention_amount": FinancialEngine.to_d128(
                        fin["retention_amount"]
                    ),
                    "total_after_retention": FinancialEngine.to_d128(
                        fin["total_after_retention"]
                    ),
                    "cgst": FinancialEngine.to_d128(fin["cgst"]),
                    "sgst": FinancialEngine.to_d128(fin["sgst"]),
                    "grand_total": FinancialEngine.to_d128(fin["grand_total"]),
                    "total_payable": FinancialEngine.to_d128(fin["grand_total"]),
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

            if idempotency_key:
                from app.core.idempotency import record_operation

                await record_operation(
                    self.db,
                    uow.session,
                    idempotency_key,
                    "PAYMENT_CERTIFICATE",
                    response_payload=new_pc,
                )

            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=new_pc["id"],
                action_type="CREATE",
                user_id=user["user_id"],
                project_id=project_id,
                new_value=new_pc,
                session=uow.session,
            )

            return new_pc

    async def close_payment_certificate(self, user: dict, pc_id: str, expected_version: int) -> Dict[str, Any]:
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
            if pc["status"] == "Closed":
                raise ValidationError("Already closed")

            grand_total = Decimal(str(pc["grand_total"]))
            retention_amount = Decimal(str(pc["retention_amount"]))
            project_id = pc["project_id"]
            pc_type = pc.get("pc_type", "WO_LINKED")

            updated_pc = await uow.payments.update(
                pc_id,
                {"status": "Closed", "closed_at": now(), "version": expected_version + 1},
                expected_version=expected_version,
                session=uow.session,
            )
            if not updated_pc:
                raise ValidationError("CONFLICT: Payment Certificate was modified by another process (Version Mismatch).")

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
                            "last_pc_closed_date": now(),
                        },
                        session=uow.session,
                    )

                    await uow.cash_transactions.create({
                        "project_id": project_id,
                        "category_id": category_id,
                        "amount": FinancialEngine.to_d128(grand_total),
                        "type": "CREDIT",
                        "description": f"Replenishment via PC {pc['pc_ref']}",
                        "transaction_date": now(),
                        "created_by": user["user_id"],
                        "organisation_id": organisation_id
                    }, session=uow.session)

            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=pc_id,
                action_type="CLOSE",
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
                    "ref_id": str(pc_id),
                    "entry_type": "PAYMENT_MADE",
                    "amount": FinancialEngine.to_d128(grand_total),
                    "created_at": now()
                }, session=uow.session)

                # J2: If retention, track it
                if retention_amount > 0:
                    await uow.ledger.create({
                        "vendor_id": str(pc["vendor_id"]),
                        "project_id": project_id,
                        "ref_id": str(pc_id),
                        "entry_type": "RETENTION_HELD",
                        "amount": FinancialEngine.to_d128(retention_amount),
                        "created_at": now()
                    }, session=uow.session)

            # Final Authoritative Recalculation for Project
            await self.financial_service.recalculate_master_budget(
                project_id, session=uow.session
            )

            return {"status": "success", "message": "PC closed and financials updated"}

    async def get_payment_certificate(self, user: dict, pc_id: str) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        pc = await self.pc_repo.get_by_id(pc_id, organisation_id=organisation_id)
        if not pc:
            raise NotFoundError("Payment Certificate", pc_id)
        
        # Ensure total_payable is populated for frontend (Point 3.3/75 consistency)
        if "total_payable" not in pc:
            pc["total_payable"] = pc.get("grand_total") or pc.get("total_after_retention", 0)

        return pc

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
                raise ValidationError("CONFLICT: Payment Certificate was modified by another process (Version Mismatch).")

            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
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
                raise ValidationError("CONFLICT: Payment Certificate was modified by another process (Version Mismatch).")

            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
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
                raise ValidationError("CONFLICT: Payment Certificate was modified by another process (Version Mismatch).")

            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
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
