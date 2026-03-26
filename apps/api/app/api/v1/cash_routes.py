from fastapi import APIRouter, Depends, Body, Query
from typing import List, Dict, Any, Optional
from app.core.dependencies import get_authenticated_user
from app.core.deps import get_cash_service
from app.services.cash_service import CashService
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/cash", tags=["Cash Management"])

@router.get("/allocations", response_model=GenericResponse[List[Any]])
async def list_fund_allocations(
    project_id: Optional[str] = Query(None),
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service)
):
    """List fund allocations for a project or all projects."""
    allocations = await cash_service.list_allocations(user, project_id)
    return GenericResponse(data=allocations)

@router.post("/allocations", response_model=GenericResponse[Any])
async def create_fund_allocation(
    allocation_data: dict = Body(...),
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service)
):
    """Allocate funds to a project category."""
    result = await cash_service.create_allocation(user, allocation_data)
    return GenericResponse(data=result, message="Funds allocated successfully")

@router.get("/transactions", response_model=GenericResponse[Dict[str, Any]])
async def list_cash_transactions(
    project_id: str = Query(...),
    limit: int = 50,
    cursor: Optional[str] = None,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service)
):
    """List petty cash transactions with cursor pagination."""
    result = await cash_service.list_transactions(user, project_id, limit, cursor)
    return GenericResponse(data=result)

@router.post("/transactions", response_model=GenericResponse[Any])
async def record_cash_transaction(
    transaction_data: dict = Body(...),
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service)
):
    """Record a new petty cash expense or top-up."""
    result = await cash_service.record_transaction(user, transaction_data)
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
