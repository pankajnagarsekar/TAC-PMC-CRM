from fastapi import APIRouter, Depends, Query, status
from typing import Optional, Dict, Any, List

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_payment_service
from app.services.payment_service import PaymentService
from app.schemas.financial import PaymentCertificate, PaymentCertificateCreate
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("/{project_id}", response_model=GenericResponse[Dict[str, Any]])
async def list_payment_certificates(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """List payment certificates for a project."""
    result = await payment_service.list_payment_certificates(user, project_id, limit, cursor)
    return GenericResponse(data=result)

@router.post("/", response_model=GenericResponse[PaymentCertificate], status_code=status.HTTP_201_CREATED)
async def create_payment_certificate(
    pc_data: PaymentCertificateCreate,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Create a new payment certificate."""
    new_pc = await payment_service.create_payment_certificate(user, pc_data)
    return GenericResponse(data=new_pc, message="Payment certificate created successfully")

@router.post("/{pc_id}/close", response_model=GenericResponse[Dict[str, Any]])
async def close_payment_certificate(
    pc_id: str,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Close a payment certificate and update financial models."""
    result = await payment_service.close_payment_certificate(user, pc_id)
    return GenericResponse(data=result, message="Payment certificate closed effectively")
