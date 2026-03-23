from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from bson import ObjectId
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import StreamingResponse
from core.pdf_service import pdf_generator
from core.database import get_db, db_manager
from core.utils import serialize_doc
import traceback
from auth import get_current_user
from payment_certificate_service import PaymentCertificateService
from audit_service import AuditService
from financial_service import FinancialRecalculationService
from core.rate_limit import limiter
from permissions import PermissionChecker




pc_router = APIRouter(prefix="/api", tags=["Payment Certificates"])


# --- Service dependency ---
def get_pc_service(db=Depends(get_db)) -> PaymentCertificateService:
    """FastAPI dependency that wires up PaymentCertificateService with its dependencies."""
    audit_service = AuditService(db)
    financial_service = FinancialRecalculationService(db)
    return PaymentCertificateService(db, audit_service, financial_service)


# --- Incoming Schemas ---
class PCLineItemCreate(BaseModel):
    sr_no: int
    scope_of_work: str
    rate: float
    qty: float
    unit: str


class PaymentCertificateCreate(BaseModel):
    work_order_id: Optional[str] = None
    vendor_id: Optional[str] = None
    description: Optional[str] = ""
    pc_type: Optional[str] = "WO_LINKED"
    retention_percent: float = 5.0
    line_items: List[PCLineItemCreate]


class PaymentCertificateUpdate(BaseModel):
    work_order_id: Optional[str] = None
    vendor_id: Optional[str] = None
    description: Optional[str] = ""
    retention_percent: Optional[float] = None
    line_items: Optional[List[PCLineItemCreate]] = None


# --- Routes ---
@pc_router.post("/projects/{project_id}/payment-certificates")
@limiter.limit("5/minute")
async def create_pc(
    request: Request,
    project_id: str,
    payload: PaymentCertificateCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
    pc_service: PaymentCertificateService = Depends(get_pc_service)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)
    await checker.check_project_access(user, project_id, require_write=True)

    try:
        pc_data = payload.dict()
        pc_data["idempotency_key"] = idempotency_key

        result = await pc_service.create_payment_certificate(
            pc_data=pc_data,
            current_user=user,
            project_id=project_id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@pc_router.put("/payment-certificates/{pc_id}")
@limiter.limit("10/minute")
async def update_pc(
    request: Request,
    pc_id: str,
    payload: PaymentCertificateUpdate,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
    pc_service: PaymentCertificateService = Depends(get_pc_service)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    try:
        result = await pc_service.update_payment_certificate(
            pc_id=pc_id,
            pc_data=payload.dict(exclude_none=True),
            current_user=user
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@pc_router.patch("/payment-certificates/{pc_id}/close")
@limiter.limit("10/minute")
async def close_pc(
    request: Request,
    pc_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
    pc_service: PaymentCertificateService = Depends(get_pc_service)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    try:
        result = await pc_service.close_payment_certificate(
            pc_id=pc_id,
            current_user=user
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close PC: {e}")


@pc_router.delete("/payment-certificates/{pc_id}")
@limiter.limit("10/minute")
async def delete_pc(
    request: Request,
    pc_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
    pc_service: PaymentCertificateService = Depends(get_pc_service)
):
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await checker.check_web_crm_access(user)
    await checker.check_client_readonly(user)

    try:
        result = await pc_service.delete_payment_certificate(
            pc_id=pc_id,
            current_user=user
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
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

        from core.utils import serialize_doc
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
    if not ObjectId.is_valid(pc_id):
        raise HTTPException(status_code=400, detail="Invalid PC ID format")

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    try:
        doc = await db.payment_certificates.find_one({
            "_id": ObjectId(pc_id),
            "organisation_id": user["organisation_id"]
        })
        if not doc:
            raise HTTPException(status_code=404, detail="Payment Certificate not found")

        # Check project access
        await checker.check_project_access(user, doc.get("project_id"))

        return serialize_doc(doc)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@pc_router.get("/payment-certificates/{pc_id}/export")
async def export_payment_certificate_pdf(
    pc_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(pc_id):
        raise HTTPException(status_code=400, detail="Invalid PC ID format")

    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)

    doc = await db.payment_certificates.find_one({
        "_id": ObjectId(pc_id),
        "organisation_id": user["organisation_id"]
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Payment Certificate not found")

    await checker.check_project_access(user, doc.get("project_id"))

    # Fetch settings for branding
    settings = await db.global_settings.find_one({"organisation_id": user["organisation_id"]})
    if not settings:
        settings = {}

    # Fetch vendor info
    vendor_id = doc.get("vendor_id")
    vendor = None
    if vendor_id and ObjectId.is_valid(vendor_id):
        vendor = await db.vendors.find_one({"_id": ObjectId(vendor_id)})

    from core.utils import serialize_doc
    pdf_bytes = pdf_generator.generate_payment_certificate_pdf(
        serialize_doc(doc),
        serialize_doc(settings),
        serialize_doc(vendor) if vendor else None
    )

    filename = pdf_generator.get_pc_filename(doc.get("pc_ref", pc_id))

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
    )
