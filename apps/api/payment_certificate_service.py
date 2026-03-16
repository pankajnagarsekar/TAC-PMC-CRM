from datetime import datetime, timezone
from bson import Decimal128, ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import ValidationError
from typing import Optional, Dict
from decimal import Decimal

from models import PaymentCertificate
from core.database import db_manager
from core.idempotency import check_idempotency, record_operation, get_recorded_operation
from financial_service import FinancialRecalculationService

async def extract_sequence(db: AsyncIOMotorDatabase, session, prefix: str):
    # Retrieve & Increment global sequences directly inside transaction wrapper 
    counter = await db.sequences.find_one_and_update(
        {"_id": "pc_sequence"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
        session=session
    )
    # PC-001 formatting
    return f"{prefix}{counter['seq']:03d}"

async def calculate_pc_totals(line_items: list, cgst_percent: float, sgst_percent: float, retention_percent: float) -> dict:
    subtotal = Decimal("0")
    for item in line_items:
        if isinstance(item, dict):
            rate = Decimal(str(item.get("rate", 0)))
            qty = Decimal(str(item.get("qty", 0)))
        else:
            rate = Decimal(str(getattr(item, "rate", 0)))
            qty = Decimal(str(getattr(item, "qty", 0)))
        subtotal += FinancialRecalculationService.round_half_up(rate * qty)
    subtotal = FinancialRecalculationService.round_half_up(subtotal)
    
    retention_amount = FinancialRecalculationService.round_half_up(subtotal * (Decimal(str(retention_percent)) / Decimal("100")))
    total_before_tax = subtotal
    
    cgst_amount = FinancialRecalculationService.round_half_up(total_before_tax * (Decimal(str(cgst_percent)) / Decimal("100")))
    sgst_amount = FinancialRecalculationService.round_half_up(total_before_tax * (Decimal(str(sgst_percent)) / Decimal("100")))
    
    grand_total = FinancialRecalculationService.round_half_up(total_before_tax + cgst_amount + sgst_amount)
    total_payable = FinancialRecalculationService.round_half_up(grand_total - retention_amount)
    
    return {
        "subtotal": subtotal,
        "retention_amount": retention_amount,
        "cgst": cgst_amount,
        "sgst": sgst_amount,
        "grand_total": grand_total,
        "total_payable": total_payable
    }

async def create_payment_certificate(
        db: AsyncIOMotorDatabase, 
        project_id: str, 
        user_id: str, 
        pc_data: dict, 
        idempotency_key: str
) -> dict:
    async with db_manager.transaction_session() as session:
        # Idempotency lock - Replay Pattern
        if idempotency_key:
            # First check: try to get recorded response payload
            recorded_response = await get_recorded_operation(db, session, idempotency_key)
            if recorded_response:
                return recorded_response
            
            # Fallback: check legacy records without payload
            existing_pc = await db.payment_certificates.find_one({"idempotency_key": idempotency_key}, session=session)
            if existing_pc:
                # Return existing document to ensure deterministic replay
                for k, v in existing_pc.items():
                    if isinstance(v, Decimal128):
                        existing_pc[k] = float(v.to_decimal())
                if "_id" in existing_pc:
                    existing_pc["_id"] = str(existing_pc["_id"])
                return existing_pc
            
        settings = await db.global_settings.find_one({}, session=session)
        if not settings:
            raise HTTPException(status_code=500, detail="Global settings missing.")

        mode_a_wo_linked = bool(pc_data.get('work_order_id'))
        
        # Branch variables
        category_id = None
        vendor_id = None
        subtotal = 0.0

        if mode_a_wo_linked:
            wo_id = pc_data["work_order_id"]
            if ObjectId.is_valid(wo_id):
                wo_query = {"_id": ObjectId(wo_id)}
            else:
                wo_query = {"_id": wo_id}

            wo = await db.work_orders.find_one(wo_query, session=session)
            if not wo:
                raise HTTPException(status_code=404, detail="Work Order not found.")
            if wo['status'] == 'Cancelled':
                raise HTTPException(status_code=400, detail="Cannot create PC for cancelled Work Order.")
                
            category_id = wo['category_id']
            vendor_id = wo['vendor_id']
        else:
            category_id = pc_data.get('category_id')
            if not category_id:
               raise HTTPException(status_code=400, detail="Category ID required for Fund Requests.") 
            
            # Retrieve CodeMaster verifying constraints (Mode B must be fund_transfer type)
            category_query = {"_id": ObjectId(category_id)} if ObjectId.is_valid(category_id) else {"_id": category_id}
            category = await db.code_master.find_one(category_query, session=session)
            if not category or category.get('budget_type') != 'fund_transfer':
                raise HTTPException(status_code=400, detail="Selected category must be of type Fund Transfer.")
            
            allocations = await db.fund_allocations.find_one({
                "project_id": project_id, 
                "category_id": category_id
            }, session=session)

            if not allocations or float(allocations.get('allocation_remaining', 0)) <= 0:
                raise HTTPException(status_code=400, detail="Insufficient or zero fund allocations remaining.")

        # 4. Strict Financial Validation
        fin_svc = FinancialRecalculationService(db)
        await fin_svc.validate_financial_document("PAYMENT_CERTIFICATE", pc_data, project_id, session=session)

        # 5. Calc constraints
        totals_dict = await calculate_pc_totals(
             pc_data.get('line_items', []), 
             settings.get('cgst_percentage', 9), 
             settings.get('sgst_percentage', 9),
             pc_data.get('retention_percent', 5)
        )
        
        # Generator wrapper
        pc_ref = await extract_sequence(db, session, settings.get('pc_prefix', 'PC-'))

        pc_doc = {
            "project_id": project_id,
            "work_order_id": pc_data.get('work_order_id'),
            "category_id": category_id,
            "vendor_id": vendor_id,
            "pc_ref": pc_ref,
            "status": "Draft",
            "fund_request": not mode_a_wo_linked,
            "line_items": pc_data.get('line_items', []),
            "created_at": datetime.now(timezone.utc),
            "idempotency_key": idempotency_key,
            **totals_dict
        }

        # Transform decimals implicitly
        for key in ["subtotal", "retention_amount", "cgst", "sgst", "grand_total", "total_payable"]:
           pc_doc[key] = Decimal128(str(pc_doc[key]))

        # Commit Document
        result = await db.payment_certificates.insert_one(pc_doc, session=session)
        inserted_id = str(result.inserted_id)
        
        # Vendor Ledger (Mode A only)
        if mode_a_wo_linked:
            await db.vendor_ledger.insert_one({
                "vendor_id": vendor_id,
                "project_id": project_id,
                "ref_id": inserted_id,
                "entry_type": "PC_CERTIFIED",
                "amount": Decimal128(str(totals_dict['grand_total'])),
                "created_at": datetime.now(timezone.utc)
            }, session=session)

        # Audit Logging
        await db.audit_logs.insert_one({
            "entity_name": "PaymentCertificate",
            "entity_id": inserted_id,
            "action_type": "CREATE",
            "user_id": user_id,
            "new_state": {"pc_ref": pc_ref, "grand_total": str(totals_dict['grand_total'])},
            "created_at": datetime.now(timezone.utc)
        }, session=session)

        # Seal
        pc_doc["_id"] = inserted_id
        # Convert Decimals for returning dictionary
        for k, v in pc_doc.items():
            if isinstance(v, Decimal128):
                pc_doc[k] = float(v.to_decimal())

        await record_operation(db, session, idempotency_key, "PaymentCertificate", response_payload=pc_doc)

        return pc_doc


async def close_payment_certificate(
        db: AsyncIOMotorDatabase, 
        pc_id: str, 
        user_id: str,
        expected_version: int
) -> dict:
    async with db_manager.transaction_session() as session:
        pc = await db.payment_certificates.find_one({"_id": ObjectId(pc_id)}, session=session)
        if not pc:
            raise HTTPException(status_code=404, detail="Payment Certificate not found")

        current_version = pc.get("version", 1)
        if current_version != expected_version:
            raise HTTPException(
                status_code=409, 
                detail={"error": "concurrency_conflict", "message": "This Payment Certificate was modified in another session. Please reload and try again."}
            )

        if pc["status"] == "Closed":
            raise HTTPException(status_code=400, detail="Payment Certificate is already closed")

        if pc["status"] == "Cancelled":
             raise HTTPException(status_code=400, detail="Cannot close a cancelled Payment Certificate")

        grand_total_dec = pc.get("grand_total") # Assumed Decimal128
        
        # Branch variables based on Mode
        mode_b_fund_request = pc.get("fund_request", False)
        
        # Initialize for response
        project_id = pc.get("project_id")
        category_id = pc.get("category_id")
        
        if mode_b_fund_request:
            # Mode B: Petty Cash / OVH Fund Request
            # Deduct allocation_remaining
            allocations = await db.fund_allocations.find_one({"project_id": project_id, "category_id": category_id}, session=session)
            if not allocations:
                raise HTTPException(status_code=404, detail="Fund allocations missing for this category.")
            
            # Mathematical lock enforcing constraints
            new_allocation = float(allocations.get('allocation_remaining', 0)) - float(grand_total_dec.to_decimal())
            if new_allocation < 0:
                 raise HTTPException(status_code=400, detail="Insufficient allocation remaining to close this request")

            await db.fund_allocations.update_one(
                 {"_id": allocations["_id"]},
                 {
                     "$set": {
                         "allocation_remaining": Decimal128(str(new_allocation)),
                         "last_pc_closed_date": datetime.now(timezone.utc)
                     }
                 },
                 session=session
            )

            # Deduct Master Remaining Budget precisely
            project = await db.projects.find_one({"project_id": project_id}, session=session)
            if project and 'master_remaining_budget' in project:
                 new_master_remaining = float(project['master_remaining_budget'].to_decimal()) - float(grand_total_dec.to_decimal())
                 await db.projects.update_one(
                     {"_id": project["_id"]},
                     {"$set": {"master_remaining_budget": Decimal128(str(new_master_remaining))}},
                     session=session
                 )

            # Log Credit into Cash Transactions natively
            await db.cash_transactions.insert_one({
                "project_id": project_id,
                "category_id": category_id,
                "amount": grand_total_dec,
                "type": "CREDIT",
                "bill_reference": pc.get("pc_ref", "SYSTEM_CLOSE"),
                "created_at": datetime.now(timezone.utc)
            }, session=session)

        else:
             # Mode A: Work Order Linked
             vendor_id = pc.get("vendor_id")
             project_id = pc.get("project_id")
             retention_amount = pc.get("retention_amount")
             
             # Main payment block
             await db.vendor_ledger.insert_one({
                    "vendor_id": vendor_id,
                    "project_id": project_id,
                    "ref_id": str(pc["_id"]),
                    "entry_type": "PAYMENT_MADE",
                    "amount": grand_total_dec,
                    "created_at": datetime.now(timezone.utc)
             }, session=session)

             # Retention isolated tracking block
             if retention_amount and float(retention_amount.to_decimal()) > 0:
                 await db.vendor_ledger.insert_one({
                    "vendor_id": vendor_id,
                    "project_id": project_id,
                    "ref_id": str(pc["_id"]),
                    "entry_type": "RETENTION_HELD",
                    "amount": retention_amount,
                    "created_at": datetime.now(timezone.utc)
                 }, session=session)

        # Base Close Logic
        await db.payment_certificates.update_one(
            {"_id": pc["_id"]},
            {"$set": {"status": "Closed", "updated_at": datetime.now(timezone.utc)}, "$inc": {"version": 1}},
            session=session
        )

        await db.audit_logs.insert_one({
            "entity_name": "PaymentCertificate",
            "entity_id": pc_id,
            "action_type": "CLOSE",
            "user_id": user_id,
            "previous_state": {"status": pc["status"]},
            "new_state": {"status": "Closed"},
            "created_at": datetime.now(timezone.utc)
        }, session=session)

        # Build enhanced response with financial summaries
        response = {
            "status": "Closed",
            "pc_id": pc_id,
            "updated_pc": {
                "_id": str(pc["_id"]),
                "pc_ref": pc.get("pc_ref"),
                "status": "Closed",
                "grand_total": float(grand_total_dec.to_decimal())
            }
        }

        # For Mode B (fund request), include updated cash/allocation info
        if mode_b_fund_request:
            # Get updated allocation
            updated_alloc = await db.fund_allocations.find_one(
                {"project_id": project_id, "category_id": category_id}, 
                session=session
            )
            
            # Get updated project master remaining
            updated_project = await db.projects.find_one(
                {"project_id": project_id}, 
                session=session
            )
            
            # Calculate cash_in_hand for this category
            cash_pipeline = [
                {"$match": {"project_id": project_id, "category_id": category_id}},
                {"$group": {
                    "_id": None,
                    "total_credit": {"$sum": {"$cond": [{"$eq": ["$type", "CREDIT"]}, "$amount", 0]}},
                    "total_debit": {"$sum": {"$cond": [{"$eq": ["$type", "DEBIT"]}, "$amount", 0]}}
                }}
            ]
            cash_result = await db.cash_transactions.aggregate(cash_pipeline).to_list(1)
            cash_in_hand = 0.0
            if cash_result:
                cash_in_hand = float(cash_result[0].get("total_credit", 0)) - float(cash_result[0].get("total_debit", 0))
            
            response["financial_summary"] = {
                "cash_in_hand": cash_in_hand,
                "allocation_remaining": float(updated_alloc.get("allocation_remaining", Decimal128("0")).to_decimal()) if updated_alloc else 0,
                "master_remaining_budget": float(updated_project.get("master_remaining_budget", Decimal128("0")).to_decimal()) if updated_project else 0
            }

        return response

