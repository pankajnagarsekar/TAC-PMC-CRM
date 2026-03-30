from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import (
    get_authenticated_user,
    get_cash_service,
    get_financial_service,
    get_master_data_service,
    get_payment_service,
    verify_nonce,
)
from app.modules.shared.domain.schemas import GenericResponse

from ..application.cash_service import CashService
from ..application.financial_service import FinancialService
from ..application.master_data_service import MasterDataService
from ..application.payment_service import PaymentService
from ..schemas.dto import (
    CashTransaction,
    CashTransactionCreate,
    CodeMaster,
    CodeMasterCreate,
    FundAllocation,
    FundAllocationCreate,
    PaymentCertificate,
    PaymentCertificateCreate,
)

router = APIRouter()

# --- PAYMENT CERTIFICATE ENDPOINTS ---


@router.get(
    "/payments/{project_id}",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Payments"],
)
async def list_payment_certificates(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """List payment certificates for a project."""
    result = await payment_service.list_payment_certificates(
        user, project_id, limit, cursor
    )
    return GenericResponse(data=result)


@router.post(
    "/payments/",
    response_model=GenericResponse[PaymentCertificate],
    status_code=status.HTTP_201_CREATED,
    tags=["Payments"],
)
async def create_payment_certificate(
    pc_data: PaymentCertificateCreate,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Create a new payment certificate."""
    new_pc = await payment_service.create_payment_certificate(user, pc_data)
    return GenericResponse(
        data=new_pc, message="Payment certificate created successfully"
    )


@router.post(
    "/payments/{pc_id}/close",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Payments"],
)
async def close_payment_certificate(
    pc_id: str,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Close a payment certificate and update financial models."""
    result = await payment_service.close_payment_certificate(user, pc_id)
    return GenericResponse(
        data=result, message="Payment certificate closed effectively"
    )


# --- CASH MANAGEMENT ENDPOINTS ---


@router.get(
    "/cash/allocations",
    response_model=GenericResponse[List[Any]],
    tags=["Cash Management"],
)
async def list_fund_allocations(
    project_id: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
):
    """List fund allocations for a project or all projects."""
    allocations = await cash_service.list_fund_allocations(user, project_id)
    return GenericResponse(data=allocations)


@router.post(
    "/cash/allocations", response_model=GenericResponse[Any], tags=["Cash Management"]
)
async def create_fund_allocation(
    allocation_data: FundAllocationCreate,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
    nonce: str = Depends(verify_nonce),
):
    """Allocate funds to a project category."""
    # Note: Service method name might vary slightly based on implementation
    result = await cash_service.create_fund_allocation(user, allocation_data)
    return GenericResponse(data=result, message="Funds allocated successfully")


@router.get(
    "/cash/transactions",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Cash Management"],
)
async def list_cash_transactions(
    project_id: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
):
    """List petty cash transactions with cursor pagination."""
    result = await cash_service.list_cash_transactions(
        user, project_id, limit=limit, cursor=cursor
    )
    return GenericResponse(data=result)


@router.post("/petty-cash/transaction", response_model=GenericResponse[dict])
async def record_cash_transaction(
    txn_data: CashTransactionCreate,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
):
    """Record a petty cash or overhead transaction."""
    result = await cash_service.record_transaction(user, txn_data)
    return GenericResponse(data=result)


# --- MASTER DATA ENDPOINTS (Reference Codes) ---


@router.get(
    "/settings/codes",
    response_model=GenericResponse[List[CodeMaster]],
    tags=["Settings"],
)
async def list_categories(
    user: dict = Depends(get_authenticated_user),
    master_service: MasterDataService = Depends(get_master_data_service),
):
    """List reference codes for the organisation."""
    categories = await master_service.list_codes(user)
    return GenericResponse(data=categories)


@router.post(
    "/settings/codes",
    response_model=GenericResponse[dict],
    status_code=status.HTTP_201_CREATED,
    tags=["Settings"],
)
async def create_category(
    category_data: CodeMasterCreate,
    user: dict = Depends(get_authenticated_user),
    master_service: MasterDataService = Depends(get_master_data_service),
):
    """Create a new category code (Admin only)."""
    result = await master_service.create_code(user, category_data)
    return GenericResponse(data=result, message="Category code created successfully")


@router.get(
    "/cash/balance/{project_id}",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Cash Management"],
)
async def get_project_cash_balance(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
):
    """Get current petty cash balance for a project."""
    # Note: Using get_cash_summary if simple balance not exposed
    summary = await cash_service.get_cash_summary(user, project_id)
    return GenericResponse(data={"balance": summary["summary"]["total_cash_in_hand"]})


@router.get(
    "/cash/summary/{project_id}",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Cash Management"],
)
async def get_project_cash_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
):
    """Get comprehensive cash summary per category for a project."""
    summary = await cash_service.get_cash_summary(user, project_id)
    return GenericResponse(data=summary)
