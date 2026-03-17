from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from core.database import get_db
from auth import get_current_user
from payment_certificate_service import create_payment_certificate, close_payment_certificate
from core.rate_limit import limiter
from permissions import PermissionChecker


# --- Helper ---
def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    serialized = {}
    for k, v in doc.items():
        if k == '_id' and isinstance(v, ObjectId):
            serialized[k] = str(v)
        else:
            serialized[k] = v
    return serialized


pc_router = APIRouter(prefix="/api", tags=["Payment Certificates"])


# --- Incoming Schemas ---
class PCLineItemCreate(BaseModel):
    sr_no: int
    scope_of_work: str
    rate: float
    qty: float
    unit: str


class PaymentCertificateCreate(BaseModel):
    work_order_id: Optional[str] = None
    category_id: Optional[str] = None
    retention_percent: float = 5.0
    line_items: List[PCLineItemCreate]


# --- Routes ---
@pc_router.post("/projects/{project_id}/payment-certificates")
@limiter.limit("5/minute")
async def create_pc(
    request: Request,
    project_id: str,
    payload: PaymentCertificateCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)
    await checker.check_project_access(user, project_id, require_write=True)

    try:
        user_id = user.get("user_id") or "system"
        pc_doc = await create_payment_certificate(
            db=db,
            project_id=project_id,
            user_id=user_id,
            pc_data=payload.dict(),
            idempotency_key=idempotency_key
        )
        return serialize_doc(pc_doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@pc_router.patch("/payment-certificates/{pc_id}/close")
@limiter.limit("10/minute")
async def close_pc(
    request: Request,
    pc_id: str,
    expected_version: int = Query(..., description="The version of the document to update"),
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    try:
        user_id = user.get("user_id") or "system"
        res = await close_payment_certificate(db, pc_id, user_id, expected_version)
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close PC: {e}")


@pc_router.get("/projects/{project_id}/payment-certificates")
async def list_project_pcs(
    project_id: str,
    work_order_id: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None, description="ISO timestamp for cursor"),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_project_access(user, project_id)

    try:
        query = {"project_id": project_id}
        if work_order_id:
            query["work_order_id"] = work_order_id

        if cursor:
            try:
                parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
                query["created_at"] = {"$lt": parsed_cursor}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid cursor format")

        cursor_obj = db.payment_certificates.find(query).sort("created_at", -1).limit(limit)
        docs = await cursor_obj.to_list(length=limit)

        next_cursor = None
        if len(docs) == limit:
            last_doc = docs[-1]
            ts = last_doc.get("created_at")
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()

        return {
            "items": [serialize_doc(doc) for doc in docs],
            "next_cursor": next_cursor
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@pc_router.get("/payment-certificates/{pc_id}")
async def get_single_pc(
    pc_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    try:
        doc = await db.payment_certificates.find_one({"_id": ObjectId(pc_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Payment Certificate not found")

        # Check project access
        await checker.check_project_access(user, doc.get("project_id"))

        return serialize_doc(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
