from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId, Decimal128
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from decimal import Decimal

from core.database import get_db, db_manager
from core.idempotency import check_idempotency, record_operation, get_recorded_operation
from auth import get_current_user
from models import CashTransactionCreate
from permissions import PermissionChecker
from audit_service import AuditService
from cash_service import CashService
from core.rate_limit import limiter
from core.performance import measure_performance

cash_router = APIRouter(prefix="/api/projects", tags=["Cash Transactions"])

def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    serialized = {}
    for k, v in doc.items():
        if k == '_id' and isinstance(v, ObjectId):
            serialized[k] = str(v)
        elif isinstance(v, Decimal128):
            serialized[k] = float(v.to_decimal())
        elif isinstance(v, datetime):
            serialized[k] = v.isoformat()
        else:
            serialized[k] = v
    return serialized

@cash_router.get("/{project_id}/fund-allocations")
async def list_fund_allocations(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_project_access(user, project_id)

    try:
        pipeline = [
            {"$match": {"project_id": project_id}},
            {
                "$lookup": {
                    "from": "categories",
                    "let": {"cat_id": "$category_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$cat_id"]}}}
                    ],
                    "as": "category_info"
                }
            },
            {"$unwind": {"path": "$category_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "project_id": 1,
                    "category_id": 1,
                    "allocation_original": 1,
                    "allocation_received": 1,
                    "allocation_remaining": 1,
                    "last_pc_closed_date": 1,
                    "created_at": 1,
                    "category_name": "$category_info.category_name"
                }
            },
            {"$sort": {"created_at": -1}}
        ]
        
        cursor = db.fund_allocations.aggregate(pipeline)
        docs = await cursor.to_list(length=100)
        
        # Convert Decimal128 values to float
        for d in docs:
            d["allocation_original"] = float(d.get("allocation_original", Decimal128("0")).to_decimal())
            d["allocation_received"] = float(d.get("allocation_received", Decimal128("0")).to_decimal())
            d["allocation_remaining"] = float(d.get("allocation_remaining", Decimal128("0")).to_decimal())

        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cash_router.post("/{project_id}/cash-transactions")
@limiter.limit("20/minute")
async def create_cash_transaction(
    request: Request,
    project_id: str,
    payload: CashTransactionCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)
    await checker.check_project_access(user, project_id, require_write=True)
    
    audit_service = AuditService(db)

    async with db_manager.transaction_session() as session:
        # 1. Idempotency Check - Replay Pattern
        if idempotency_key:
            # First check: try to get recorded response payload
            recorded_response = await get_recorded_operation(db, session, idempotency_key)
            if recorded_response:
                return recorded_response

        # Validate constraints
        payload_amount = Decimal128(str(payload.amount))
        
        allocation = await db.fund_allocations.find_one({
            "project_id": project_id,
            "category_id": payload.category_id
        }, session=session)

        if not allocation:
             raise HTTPException(status_code=404, detail="No active fund allocation found for this category.")

        # Get project for threshold values
        project = await db.projects.find_one({"project_id": project_id}, session=session)
        
        # Get category to determine if Petty or OVH
        category = await db.categories.find_one({"_id": ObjectId(payload.category_id)}, session=session)
        
        # Determine threshold based on category
        default_threshold = Decimal("1000.0")
        threshold = default_threshold
        
        if category and category.get("category_name"):
            cat_name = category["category_name"].lower()
            if "petty" in cat_name:
                threshold = Decimal(str(project.get("threshold_petty", default_threshold))) if project else default_threshold
            elif "ovh" in cat_name or "overhead" in cat_name:
                threshold = Decimal(str(project.get("threshold_ovh", default_threshold))) if project else default_threshold

        warnings = []
        new_cash_in_hand = None

        # ── Atomic balance update on fund_allocations ────────────────────────
        # Use $inc instead of read→compute→$set to avoid TOCTOU races when
        # concurrent transactions hit the same allocation document.
        #
        # DEBIT  → cash_in_hand decreases; total_expenses increases.
        # CREDIT → cash_in_hand increases only (allocation_remaining is managed
        #          separately by the fund-transfer workflow, not here).
        # Per Spec §5.3 — does NOT touch allocation_remaining for plain expenses.

        inc_amount = Decimal(str(payload.amount))

        if payload.type == "DEBIT":
            inc_ops = {
                "cash_in_hand":  Decimal128(str(-inc_amount)),   # subtract
                "total_expenses": Decimal128(str(inc_amount)),   # accumulate
            }
        else:  # CREDIT
            inc_ops = {
                "cash_in_hand": Decimal128(str(inc_amount)),     # add
            }

        updated_alloc = await db.fund_allocations.find_one_and_update(
            {"_id": allocation["_id"]},
            {"$inc": inc_ops},
            return_document=True,   # return the doc AFTER the increment
            session=session
        )

        if updated_alloc is not None:
            raw = updated_alloc.get("cash_in_hand", Decimal128("0"))
            new_cash_in_hand = float(
                raw.to_decimal() if isinstance(raw, Decimal128) else Decimal(str(raw))
            )

        doc = payload.dict()
        doc["project_id"] = project_id
        doc["organisation_id"] = user["organisation_id"]
        doc["amount"] = payload_amount
        doc["created_by"] = user["user_id"]
        doc["created_at"] = datetime.now(timezone.utc)
        
        res = await db.cash_transactions.insert_one(doc, session=session)
        doc["_id"] = res.inserted_id

    # Log action with FULL JSON snapshot
    doc_full = serialize_doc(doc)
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="CASH_TRANSACTIONS",
        entity_type="CASH_TRANSACTION",
        entity_id=str(res.inserted_id),
        action_type="CREATE",
        user_id=user["user_id"],
        project_id=project_id,
        new_value=doc_full,  # FULL JSON snapshot per spec 6.1.2
        session=session
    )

    # Record for idempotency
    await record_operation(db, session, idempotency_key, "CASH_TRANSACTION", response_payload=serialize_doc(doc))

    response = serialize_doc(doc)

    # Add warning flags per 3.2.2 spec
    if new_cash_in_hand is not None:
        if new_cash_in_hand < 0:
            warnings.append("negative_cash")
        elif new_cash_in_hand <= float(threshold):
            warnings.append("threshold_breach")

    if warnings:
        response["warnings"] = warnings

    return response


@cash_router.get("/{project_id}/cash-transactions")
async def list_cash_transactions(
    project_id: str,
    category_id: str = Query(None, description="Optional filter by category_id"),
    cursor: Optional[str] = Query(None, description="ISO timestamp for cursor"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_project_access(user, project_id)

    try:
        cash_service = CashService(db)
        return await cash_service.list_cash_transactions(
            project_id=project_id,
            organisation_id=user["organisation_id"],
            category_id=category_id,
            cursor=cursor,
            limit=limit
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cash_router.get("/{project_id}/cash-summary")
async def get_cash_summary(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_project_access(user, project_id)

    try:
        cash_service = CashService(db)
        return await cash_service.get_cash_summary(project_id, user["organisation_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


