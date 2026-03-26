from fastapi import APIRouter, Depends, Body, Query
from typing import List, Dict, Any, Optional
from app.core.dependencies import get_authenticated_user, get_cash_service, verify_nonce
from app.services.cash_service import CashService
from app.schemas.shared import GenericResponse
from app.schemas.cash import FundAllocationCreate, CashTransactionCreate, FundAllocation, CashTransaction

router = APIRouter(prefix="/cash", tags=["Cash Management"])

@router.get("/allocations", response_model=GenericResponse[List[Any]])
async def list_fund_allocations(
    project_id: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service)
):
    """List fund allocations for a project or all projects."""
    allocations = await cash_service.list_fund_allocations(user, project_id)
    return GenericResponse(data=allocations)

@router.post("/allocations", response_model=GenericResponse[Any])
async def create_fund_allocation(
    allocation_data: FundAllocationCreate,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
    nonce: str = Depends(verify_nonce)
):
    """Allocate funds to a project category."""
    # Note: Using unified method name in service
    result = await cash_service.create_fund_allocation(user, allocation_data)
    return GenericResponse(data=result, message="Funds allocated successfully")

@router.get("/transactions", response_model=GenericResponse[Dict[str, Any]])
async def list_cash_transactions(
    project_id: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service)
):
    """List petty cash transactions with cursor pagination."""
    result = await cash_service.list_cash_transactions(user, project_id, limit=limit, cursor=cursor)
    return GenericResponse(data=result)

@router.post("/transactions", response_model=GenericResponse[Any])
async def record_cash_transaction(
    transaction_data: CashTransactionCreate,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
    nonce: str = Depends(verify_nonce)
):
    """Record a new petty cash expense or top-up."""
    # Fixed CR-12: Added typed request data and nonce verification
    result = await cash_service.create_cash_transaction(user, transaction_data.project_id, transaction_data.dict(), nonce)
    return GenericResponse(data=result, message="Transaction recorded successfully")

@router.get("/balance/{project_id}", response_model=GenericResponse[Dict[str, Any]])
async def get_project_cash_balance(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service)
):
    """Get current petty cash balance for a project."""
    balance = await cash_service.get_project_balance(user, project_id)
    return GenericResponse(data={"balance": balance})

@router.get("/summary/{project_id}", response_model=GenericResponse[Dict[str, Any]])
async def get_project_cash_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service)
):
    """Get comprehensive cash summary per category for a project."""
    summary = await cash_service.get_cash_summary(user, project_id)
    return GenericResponse(data=summary)
