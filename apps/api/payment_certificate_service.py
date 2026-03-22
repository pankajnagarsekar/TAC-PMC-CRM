"""
Payment Certificate Business Logic Service
Implements the MongoDB Multi-Document Transactions for creating and updating Payment Certificates
as defined in the Enterprise Technical Architecture Specification.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId, Decimal128
from fastapi import HTTPException
from core.database import db_manager
from core.idempotency import check_idempotency, record_operation
from core.performance import measure_performance

logger = logging.getLogger(__name__)


class PaymentCertificateService:
    def __init__(self, db, audit_service, financial_service):
        self.db = db
        self.audit_service = audit_service
        self.financial_service = financial_service

    @measure_performance("PC_SAVE")
    async def create_payment_certificate(self, pc_data: dict, current_user: dict, project_id: str) -> dict:
        """
        Creates a Payment Certificate inside a strict MongoDB ACID transaction.
        """
        idempotency_key = pc_data.get("idempotency_key")
        organisation_id = current_user.get("organisation_id")
        user_id = current_user.get("user_id")
        pc_type = pc_data.get("pc_type", "WO_LINKED")  # or "PETTY_OVH"

        async with db_manager.transaction_session() as session:
            # 1. Idempotency Check
            if idempotency_key:
                # SECURITY: organisation_id MUST be included to prevent cross-tenant leakage
                existing_pc = await self.db.payment_certificates.find_one(
                    {"idempotency_key": idempotency_key, "organisation_id": organisation_id},
                    session=session
                )
                if existing_pc:
                    return db_manager.from_bson(existing_pc)

            # 2. Calculate totals (per CRM Spec §4.3)
            subtotal = Decimal("0.0")
            for item in pc_data.get("line_items", []):
                qty = Decimal(str(item.get("qty", 0)))
                rate = Decimal(str(item.get("rate", 0)))
                line_total = self.financial_service.round_half_up(qty * rate)
                item["total"] = line_total
                subtotal += line_total
            subtotal = self.financial_service.round_half_up(subtotal)

            # Per Spec §4.3: Calculate retention first, then tax on remaining
            retention_percent = Decimal(str(pc_data.get("retention_percent", 0)))
            retention_amount = self.financial_service.round_half_up(subtotal * (retention_percent / Decimal("100")))
            total_after_retention = self.financial_service.round_half_up(subtotal - retention_amount)

            # Get project tax rates for server-side calculation
            project = await self.db.projects.find_one(
                {"_id": ObjectId(project_id)} if len(project_id) == 24 else {"project_id": project_id},
                session=session
            )
            cgst_rate = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_rate = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")

            # Calculate CGST/SGST on total_after_retention (per Spec §4.3)
            cgst_amount = self.financial_service.round_half_up(total_after_retention * cgst_rate / Decimal("100"))
            sgst_amount = self.financial_service.round_half_up(total_after_retention * sgst_rate / Decimal("100"))
            grand_total = self.financial_service.round_half_up(total_after_retention + cgst_amount + sgst_amount)

            # 3. Auto-generate PC Ref — atomic sequence to prevent duplicate IDs under concurrent load
            settings = await self.db.global_settings.find_one({"organisation_id": organisation_id}, session=session)
            prefix = settings.get("pc_prefix", "PC-") if settings else "PC-"
            seq_doc = await self.db.sequences.find_one_and_update(
                {"_id": f"pc_seq_{organisation_id}"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=True,
                session=session
            )
            pc_ref = f"{prefix}{seq_doc['seq']:04d}"

            # 4. Construct PC Document
            pc_doc = {
                "organisation_id": organisation_id,
                "project_id": project_id,
                "pc_ref": pc_ref,
                "pc_type": pc_type,
                "work_order_id": pc_data.get("work_order_id"),
                "vendor_id": pc_data.get("vendor_id"),
                "description": pc_data.get("description", ""),
                "subtotal": Decimal128(str(subtotal)),
                "retention_percent": Decimal128(str(retention_percent)),
                "retention_amount": Decimal128(str(retention_amount)),
                "total_after_retention": Decimal128(str(total_after_retention)),  # NEW: per Spec §4.3
                "cgst": Decimal128(str(cgst_amount)),
                "sgst": Decimal128(str(sgst_amount)),
                "grand_total": Decimal128(str(grand_total)),
                "status": "Draft",
                "line_items": [db_manager.to_bson(item) for item in pc_data.get("line_items", [])],
                "idempotency_key": idempotency_key,
                "version": 1,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # 5. Insert PC
            result = await self.db.payment_certificates.insert_one(pc_doc, session=session)
            pc_id = str(result.inserted_id)
            pc_doc["_id"] = result.inserted_id

            # 6. Record operation & Audit Log
            response_doc = db_manager.from_bson(pc_doc)
            await record_operation(self.db, session, idempotency_key, "PAYMENT_CERTIFICATE", response_payload=response_doc)
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=pc_id,
                action_type="CREATE",
                user_id=user_id,
                new_value=response_doc,
                session=session
            )

            return response_doc

    @measure_performance("PC_SAVE")
    async def update_payment_certificate(self, pc_id: str, pc_data: dict, current_user: dict) -> dict:
        """
        Updates a Payment Certificate (Draft only).
        """
        organisation_id = current_user.get("organisation_id")
        user_id = current_user.get("user_id")

        async with db_manager.transaction_session() as session:
            # 1. Fetch current PC
            old_pc = await self.db.payment_certificates.find_one({
                "_id": ObjectId(pc_id),
                "organisation_id": organisation_id
            }, session=session)
            if not old_pc:
                raise HTTPException(status_code=404, detail="Payment Certificate not found.")

            if old_pc["status"] != "Draft":
                raise HTTPException(status_code=400, detail="Only 'Draft' Payment Certificates can be edited.")

            project_id = old_pc["project_id"]

            # 2. Calculate new totals (per CRM Spec §4.3)
            subtotal = Decimal("0.0")
            for item in pc_data.get("line_items", []):
                qty = Decimal(str(item.get("qty", 0)))
                rate = Decimal(str(item.get("rate", 0)))
                line_total = self.financial_service.round_half_up(qty * rate)
                item["total"] = line_total
                subtotal += line_total
            subtotal = self.financial_service.round_half_up(subtotal)

            # Per Spec §4.3: Calculate retention first, then tax on remaining
            retention_percent = Decimal(str(pc_data.get("retention_percent", 0)))
            retention_amount = self.financial_service.round_half_up(subtotal * (retention_percent / Decimal("100")))
            total_after_retention = self.financial_service.round_half_up(subtotal - retention_amount)

            # Get project tax rates for server-side calculation
            project = await self.db.projects.find_one(
                {"_id": ObjectId(project_id)} if len(project_id) == 24 else {"project_id": project_id},
                session=session
            )
            cgst_rate = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
            sgst_rate = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")

            # Calculate CGST/SGST on total_after_retention (per Spec §4.3)
            cgst_amount = self.financial_service.round_half_up(total_after_retention * cgst_rate / Decimal("100"))
            sgst_amount = self.financial_service.round_half_up(total_after_retention * sgst_rate / Decimal("100"))
            grand_total = self.financial_service.round_half_up(total_after_retention + cgst_amount + sgst_amount)

            # 3. Update PC Document
            update_fields = {
                "work_order_id": pc_data.get("work_order_id", old_pc.get("work_order_id")),
                "vendor_id": pc_data.get("vendor_id", old_pc.get("vendor_id")),
                "description": pc_data.get("description", ""),
                "subtotal": Decimal128(str(subtotal)),
                "retention_percent": Decimal128(str(retention_percent)),
                "retention_amount": Decimal128(str(retention_amount)),
                "total_after_retention": Decimal128(str(total_after_retention)),  # NEW: per Spec §4.3
                "cgst": Decimal128(str(cgst_amount)),
                "sgst": Decimal128(str(sgst_amount)),
                "grand_total": Decimal128(str(grand_total)),
                "line_items": [db_manager.to_bson(item) for item in pc_data.get("line_items", [])],
                "updated_at": datetime.now(timezone.utc)
            }
            await self.db.payment_certificates.update_one(
                {"_id": ObjectId(pc_id)},
                {"$set": update_fields, "$inc": {"version": 1}},
                session=session
            )

            # 4. Audit Log
            old_pc_full = db_manager.from_bson(old_pc)
            new_pc_full = db_manager.from_bson(await self.db.payment_certificates.find_one({"_id": ObjectId(pc_id)}, session=session))
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=pc_id,
                action_type="UPDATE",
                user_id=user_id,
                project_id=project_id,
                old_value=old_pc_full,
                new_value=new_pc_full,
                session=session
            )

            return new_pc_full

    async def close_payment_certificate(self, pc_id: str, current_user: dict) -> dict:
        """
        Closes a Payment Certificate and updates financials.
        Per Spec §4.4 and §5.2
        """
        organisation_id = current_user.get("organisation_id")
        user_id = current_user.get("user_id")

        async with db_manager.transaction_session() as session:
            pc = await self.db.payment_certificates.find_one({
                "_id": ObjectId(pc_id),
                "organisation_id": organisation_id
            }, session=session)
            if not pc:
                raise HTTPException(status_code=404, detail="Payment Certificate not found.")

            if pc["status"] == "Closed":
                raise HTTPException(status_code=400, detail="Payment Certificate is already closed.")

            grand_total = Decimal(str(pc["grand_total"].to_decimal()))
            retention_amount = Decimal(str(pc["retention_amount"].to_decimal()))
            project_id = pc["project_id"]
            pc_type = pc.get("pc_type", "WO_LINKED")

            # Update status to Closed
            await self.db.payment_certificates.update_one(
                {"_id": ObjectId(pc_id)},
                {"$set": {"status": "Closed", "closed_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}},
                session=session
            )

            # Per Spec §4.4: Update vendor ledger for WO-linked PCs
            if pc_type == "WO_LINKED" and pc.get("vendor_id"):
                vendor_id = pc["vendor_id"]
                # Update vendor running totals
                await self.db.vendors.update_one(
                    {"_id": ObjectId(vendor_id)},
                    {"$inc": {
                        "total_payable": Decimal128(str(-grand_total)),  # Deduct from payable
                        "retention_held": Decimal128(str(-retention_amount))  # Release retention
                    }},
                    session=session
                )

            # Per Spec §5.2: For Petty/OVH PCs, update liquidity model
            # NOTE: Only PETTY_OVH PCs (fund_transfer categories) trigger liquidity updates on close.
            # WO-linked PCs (commitment model, §4) update vendor payable ledger only.
            # This is intentional per spec §5.2: "PC (Fund Request) Behavior" is defined under §5 "Petty Cash / OVH (Liquidity Model)".
            # Fund allocations (cash_in_hand, allocation_received) track liquidity; vendors track payables.
            if pc_type == "PETTY_OVH":
                # Get the fund allocation for this project
                fund_alloc = await self.db.fund_allocations.find_one(
                    {"project_id": project_id},
                    session=session
                )
                if fund_alloc:
                    # Per Spec §5.2: allocation_received += grand_total
                    current_received = Decimal(str(fund_alloc.get("allocation_received", 0)))
                    new_received = current_received + grand_total

                    # Per Spec §5.2: allocation_remaining = allocation_original - allocation_received
                    allocation_original = Decimal(str(fund_alloc.get("allocation_original", 0)))
                    new_remaining = allocation_original - new_received

                    # Per Spec §5.2: cash_in_hand += grand_total
                    current_cash = Decimal(str(fund_alloc.get("cash_in_hand", 0)))
                    new_cash = current_cash + grand_total

                    await self.db.fund_allocations.update_one(
                        {"_id": fund_alloc["_id"]},
                        {"$set": {
                            "allocation_received": Decimal128(str(new_received)),
                            "allocation_remaining": Decimal128(str(new_remaining)),
                            "cash_in_hand": Decimal128(str(new_cash)),
                            "last_pc_closed_date": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }},
                        session=session
                    )

                    # Per Spec §5.2: master_remaining_budget -= grand_total
                    await self.financial_service.recalculate_master_budget(project_id, session=session)

            # Audit Log
            pc_full = db_manager.from_bson(await self.db.payment_certificates.find_one({"_id": ObjectId(pc_id)}, session=session))
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=pc_id,
                action_type="CLOSE",
                user_id=user_id,
                project_id=project_id,
                new_value=pc_full,
                session=session
            )

            return {"status": "success", "message": "Payment Certificate closed successfully."}

    async def delete_payment_certificate(self, pc_id: str, current_user: dict) -> dict:
        """
        Deletes a Payment Certificate (Draft only).
        """
        organisation_id = current_user.get("organisation_id")

        async with db_manager.transaction_session() as session:
            pc = await self.db.payment_certificates.find_one({
                "_id": ObjectId(pc_id),
                "organisation_id": organisation_id
            }, session=session)
            if not pc:
                raise HTTPException(status_code=404, detail="Payment Certificate not found.")

            if pc["status"] != "Draft":
                raise HTTPException(status_code=400, detail="Only 'Draft' Payment Certificates can be deleted.")

            # Capture full PC state before deletion for audit
            pc_full = db_manager.from_bson(pc)
            project_id = pc["project_id"]

            # Delete PC
            await self.db.payment_certificates.delete_one({"_id": ObjectId(pc_id)}, session=session)

            # Audit Log
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="PAYMENT_CERTIFICATES",
                entity_type="PAYMENT_CERTIFICATE",
                entity_id=pc_id,
                action_type="DELETE",
                user_id=current_user.get("user_id"),
                project_id=project_id,
                old_value=pc_full,
                session=session
            )

            return {"status": "success", "message": "Payment Certificate deleted."}
