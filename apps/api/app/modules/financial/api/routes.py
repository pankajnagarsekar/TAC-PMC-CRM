from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies import (
    get_authenticated_user,
    get_budget_service,
    get_cash_service,
    get_master_data_service,
    get_payment_service,
    get_vendor_service,
)
from app.modules.contracting.application.vendor_service import VendorService
from app.modules.shared.domain.schemas import GenericResponse

from ..application.budget_service import BudgetService
from ..application.cash_service import CashService
from ..application.master_data_service import MasterDataService
from ..application.payment_service import PaymentService
from ..schemas.dto import (
    Budget,
    BudgetCreate,
    BudgetForecast,
    BudgetUpdate,
    CashTransactionCreate,
    CodeMaster,
    CodeMasterCreate,
    CodeMasterUpdate,
    FundAllocationCreate,
    PaymentCertificate,
    PaymentCertificateCreate,
)

router = APIRouter()

# --- PAYMENT CERTIFICATE ENDPOINTS ---


# --- PAYMENT CERTIFICATE ENDPOINTS ---


@router.get(
    "/payments/id/{pc_id}",
    response_model=GenericResponse[PaymentCertificate],
    tags=["Payments"],
)
async def get_payment_certificate(
    pc_id: str,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Get a specific payment certificate by ID."""
    pc = await payment_service.get_payment_certificate(user, pc_id)
    return GenericResponse(data=pc)


@router.get(
    "/payments/{pc_id}/export/excel",
    tags=["Payments"],
)
async def export_payment_certificate_excel(
    pc_id: str,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service),
):
    from fastapi.responses import StreamingResponse
    import io
    from app.core.template_export_service import TemplateExportService
    from app.modules.identity.application.settings_service import SettingsService
    from app.core.dependencies import get_settings_service, get_vendor_service, get_db

    pc = await payment_service.get_payment_certificate(user, pc_id)
    
    excel_bytes = TemplateExportService.export_payment_certificate_exact(pc, fmt="excel")
    
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=PC_{pc_id}.xlsx"}
    )


@router.get(
    "/payments/{pc_id}/export/pdf",
    tags=["Payments"],
)
async def export_payment_certificate_pdf(
    pc_id: str,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    from fastapi.responses import StreamingResponse
    import io
    from app.core.template_export_service import TemplateExportService
    from app.core.dependencies import get_db

    pc = await payment_service.get_payment_certificate(user, pc_id)
    
    # Bridge data for exact export
    vendor = await vendor_service.get_vendor(user, pc.get("vendor_id"))
    pc["vendor"] = vendor
    
    # Fetch Category (CodeMaster) info
    from app.modules.financial.application.master_data_service import MasterDataService
    db = await get_db()
    md_service = MasterDataService(db, None, None) 
    category = await md_service.get_code_by_id(user, pc.get("category_id"))
    pc["category"] = category
    pc["code"] = category.get("code", "") if category else ""
    
    # Set default dates for template
    if "pc_date" not in pc:
        pc["pc_date"] = pc.get("created_at")
    
    # Get Company/Organisation details
    settings = await db.organisation_settings.find_one({"organisation_id": user["organisation_id"]})
    if settings and "company_profile" in settings:
        pc["company"] = settings["company_profile"]
    else:
        # Try finding the organisation name directly as a fallback
        from bson import ObjectId
        query = {"_id": ObjectId(user["organisation_id"])} if ObjectId.is_valid(user["organisation_id"]) else {"organisation_id": user["organisation_id"]}
        org = await db.organisations.find_one(query)
        pc["company"] = {"name": org.get("name") if org else "Third Angle Concepts (PMC)", "address": "Site Address"}
    
    pdf_bytes = TemplateExportService.export_payment_certificate_exact(pc, fmt="pdf")
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=PC_{pc_id}.pdf"}
    )


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
    request: Request,
    pc_data: PaymentCertificateCreate,
    user: dict = Depends(get_authenticated_user),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Create a new payment certificate."""
    idempotency_key = request.headers.get("X-Idempotency-Key") or pc_data.idempotency_key
    pc_data.idempotency_key = idempotency_key
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
    request: Request,
    allocation_data: FundAllocationCreate,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
):
    """Allocate funds to a project category."""
    idempotency_key = request.headers.get("X-Idempotency-Key") or allocation_data.idempotency_key
    allocation_data.idempotency_key = idempotency_key
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
    request: Request,
    txn_data: CashTransactionCreate,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
):
    """Record a petty cash or overhead transaction."""
    idempotency_key = request.headers.get("X-Idempotency-Key") or txn_data.idempotency_key
    result = await cash_service.create_cash_transaction(
        user, txn_data.project_id, txn_data.dict(), idempotency_key
    )
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


@router.get(
    "/settings/petty-cash-categories",
    response_model=GenericResponse[List[CodeMaster]],
    tags=["Settings"],
)
async def list_petty_cash_categories(
    user: dict = Depends(get_authenticated_user),
    master_service: MasterDataService = Depends(get_master_data_service),
):
    """List petty cash and site overhead categories only."""
    categories = await master_service.list_petty_cash_categories(user)
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
    "/settings/codes/{code_id}",
    response_model=GenericResponse[CodeMaster],
    tags=["Settings"],
)
async def get_category(
    code_id: str,
    user: dict = Depends(get_authenticated_user),
    master_service: MasterDataService = Depends(get_master_data_service),
):
    """Get details for a specific category code."""
    result = await master_service.get_code_by_id(user, code_id)
    return GenericResponse(data=result)


@router.put(
    "/settings/codes/{code_id}",
    response_model=GenericResponse[CodeMaster],
    tags=["Settings"],
)
async def update_category(
    code_id: str,
    category_data: CodeMasterUpdate,
    user: dict = Depends(get_authenticated_user),
    master_service: MasterDataService = Depends(get_master_data_service),
):
    """Update a category code (Admin only)."""
    result = await master_service.update_code(user, code_id, category_data)
    return GenericResponse(data=result, message="Category code updated successfully")


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


# --- BUDGET MANAGEMENT ENDPOINTS ---


@router.post(
    "/budgets",
    response_model=GenericResponse[Budget],
    status_code=status.HTTP_201_CREATED,
    tags=["Budgets"],
)
async def create_budget(
    budget_data: BudgetCreate,
    user: dict = Depends(get_authenticated_user),
    budget_service: BudgetService = Depends(get_budget_service),
):
    """Create a new budget for a project."""
    result = await budget_service.create_budget(user, budget_data.project_id, budget_data)
    return GenericResponse(data=result, message="Budget created successfully")


@router.get(
    "/budgets/{budget_id}",
    response_model=GenericResponse[Budget],
    tags=["Budgets"],
)
async def get_budget(
    budget_id: str,
    user: dict = Depends(get_authenticated_user),
    budget_service: BudgetService = Depends(get_budget_service),
):
    """Get a specific budget by ID."""
    result = await budget_service.get_budget(user, budget_id)
    return GenericResponse(data=result)


@router.put(
    "/budgets/{budget_id}/allocations",
    response_model=GenericResponse[Budget],
    tags=["Budgets"],
)
async def update_budget_allocations(
    budget_id: str,
    allocation_data: BudgetUpdate,
    user: dict = Depends(get_authenticated_user),
    budget_service: BudgetService = Depends(get_budget_service),
):
    """Update budget allocations."""
    result = await budget_service.update_allocations(user, budget_id, allocation_data)
    return GenericResponse(data=result, message="Budget allocations updated successfully")


@router.get(
    "/budgets/{budget_id}/forecast",
    response_model=GenericResponse[BudgetForecast],
    tags=["Budgets"],
)
async def forecast_budget_eac(
    budget_id: str,
    percent_complete: float = Query(50, ge=0, le=100),
    user: dict = Depends(get_authenticated_user),
    budget_service: BudgetService = Depends(get_budget_service),
):
    """Forecast budget EAC (Estimate at Completion)."""
    from decimal import Decimal
    result = await budget_service.forecast_eac(
        user, budget_id, Decimal(str(percent_complete))
    )
    return GenericResponse(data=result)
