from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId, Decimal128
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from decimal import Decimal

from core.database import get_db, db_manager
from core.idempotency import check_idempotency, record_operation
from auth import get_current_user
from models import CashTransactionCreate
from permissions import PermissionChecker
from audit_service import AuditService
from core.rate_limit import limiter

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
                    "allocation_total": 1,
                    "allocation_remaining": 1,
                    "last_replenished": 1,
                    "created_at": 1,
                    "category_name": "$category_info.category_name"
                }
            },
            {"$sort": {"created_at": -1}}
        ]
        
        cursor = db.fund_allocations.aggregate(pipeline)
        docs = await cursor.to_list(length=100)
        
        # Convert floating values back
        for d in docs:
           d["allocation_total"] = float(d.get("allocation_total", Decimal128("0")).to_decimal())
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
    await checker.check_project_access(user, project_id, require_write=True)
    
    audit_service = AuditService(db)

    async with db_manager.transaction_session() as session:
        # 1. Idempotency Check
        if idempotency_key:
            existing_op = await check_idempotency(db, session, idempotency_key)
            if existing_op and "response_payload" in existing_op:
                return existing_op["response_payload"]

        # Validate constraints
        payload_amount = Decimal128(str(payload.amount))
        
        allocation = await db.fund_allocations.find_one({
            "project_id": project_id,
            "category_id": payload.category_id
        }, session=session)

        if not allocation:
             raise HTTPException(status_code=404, detail="No active fund allocation found for this category.")

        if payload.type == "DEBIT":
            curr_rem = float(allocation.get("allocation_remaining", Decimal128("0")).to_decimal())
            req_amount = float(payload.amount)
            # 8.4.1: Allow negative cash-in-hand instead of blocking
            new_amount = curr_rem - req_amount
            await db.fund_allocations.update_one(
                {"_id": allocation["_id"]},
                {"$set": {"allocation_remaining": Decimal128(str(new_amount))}},
                session=session
            )

        doc = payload.dict()
        doc["project_id"] = project_id
        doc["organisation_id"] = user["organisation_id"]
        doc["amount"] = payload_amount
        doc["created_by"] = user["user_id"]
        doc["created_at"] = datetime.now(timezone.utc)
        
        res = await db.cash_transactions.insert_one(doc, session=session)
        doc["_id"] = res.inserted_id
        
        # Log action
        await audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="CASH_TRANSACTIONS",
            entity_type="CASH_TRANSACTION",
            entity_id=str(res.inserted_id),
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=project_id,
            new_value=payload.dict(),
            session=session
        )
        
        # Record for idempotency
        await record_operation(db, session, idempotency_key, "CASH_TRANSACTION", response_payload=serialize_doc(doc))

        return serialize_doc(doc)


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
        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
        if category_id:
             query["category_id"] = category_id
             
        if cursor:
            try:
                parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
                query["created_at"] = {"$lt": parsed_cursor}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid cursor format")

        cursor_obj = db.cash_transactions.find(query).sort("created_at", -1).limit(limit)
        docs = await cursor_obj.to_list(length=limit)
        
        next_cursor = None
        if len(docs) == limit:
            last_doc = docs[-1]
            ts = last_doc.get("created_at")
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()

        return {
            "items": [serialize_doc(d) for d in docs],
            "next_cursor": next_cursor
        }
    except HTTPException:
        raise
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
        # 1. Fetch all allocations for project
        allocations = await db.fund_allocations.find({"project_id": project_id}).to_list(length=100)
        
        total_remaining = 0.0
        allocation_total = 0.0
        is_below_threshold = False
        default_threshold = 1000.0

        for a in allocations:
            rem = float(a.get("allocation_remaining", Decimal128("0")).to_decimal())
            tot = float(a.get("allocation_total", Decimal128("0")).to_decimal())
            thresh = float(a.get("threshold", Decimal128(str(default_threshold))).to_decimal())
            
            total_remaining += rem
            allocation_total += tot
            if rem < thresh:
                is_below_threshold = True

        # 2. Find last associated PC close date
        last_pc = await db.payment_certificates.find_one(
            {"project_id": project_id, "status": "Closed", "fund_request": True},
            sort=[("updated_at", -1)]
        )
        
        days_since_last_pc_close = None
        if last_pc and last_pc.get("updated_at"):
            last_date = last_pc["updated_at"]
            if last_date.tzinfo is None:
                last_date = last_date.replace(tzinfo=timezone.utc)
            diff = datetime.now(timezone.utc) - last_date
            days_since_last_pc_close = diff.days

        return {
            "cash_in_hand": total_remaining,
            "allocation_remaining": total_remaining, # In this context, they are same (project-wide view)
            "allocation_total": allocation_total,
            "threshold": default_threshold,
            "days_since_last_pc_close": days_since_last_pc_close,
            "flags": {
                "is_negative": total_remaining < 0,
                "is_below_threshold": is_below_threshold
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


