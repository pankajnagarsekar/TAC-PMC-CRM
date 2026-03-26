from fastapi import APIRouter, Depends, Query, status
from typing import Optional, Dict, Any

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_payment_service
from app.services.payment_service import PaymentService
from app.schemas.financial import PaymentCertificate, PaymentCertificateCreate

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("/{project_id}")
async def list_payment_certificates(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """List payment certificates for a project."""
    return await payment_service.list_payment_certificates(user, project_id, limit, cursor)

@router.post("/", response_model=PaymentCertificate, status_code=status.HTTP_201_CREATED)
async def create_payment_certificate(
    pc_data: PaymentCertificateCreate,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Create a new payment certificate."""
    return await payment_service.create_payment_certificate(user, pc_data)
