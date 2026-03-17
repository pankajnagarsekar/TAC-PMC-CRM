"""
Hardened Financial Engine

Provides atomic, audited budget modifications with invariant enforcement.
All budget mutations go through this engine to ensure:
1. Organisation isolation
2. Audit trail
3. Financial state recalculation
"""

import logging
from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Query
from core.database import db_manager
from auth import get_current_user
from decimal import Decimal
from bson import Decimal128
from models import ProjectBudget, ProjectBudgetCreate, ProjectBudgetUpdate, DerivedFinancialState
from reporting_routes import serialize_doc

logger = logging.getLogger(__name__)

hardened_router = APIRouter(prefix="/api/v2", tags=["Hardened Engine"])


@hardened_router.get("/projects/{project_id}/financials", response_model=List[DerivedFinancialState])
async def get_project_financials(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get joined financial state for all categories in a project.
    Includes versions for optimistic concurrency control.
    """
    from server import db, permission_checker
    
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id, require_write=False)
    
    # 1. Get all budgets for the project (contains the primary versioning)
    budgets = await db.project_category_budgets.find({"project_id": project_id}).to_list(length=500)
    
    # 2. Get all financial state records for the project
    states = await db.financial_state.find({"project_id": project_id}).to_list(length=500)
    state_map = {s.get("category_id"): s for s in states}
    
    # 3. Join them
    results = []
    for b in budgets:
        cid = b.get("category_id")
        fs = state_map.get(cid, {})
        
        # Merge data into DerivedFinancialState structure
        result = {
            "project_id": project_id,
            "category_id": cid,
            "original_budget": b.get("original_budget", 0),
            "committed_value": fs.get("committed_value", 0),
            "certified_value": fs.get("certified_value", 0),
            "balance_budget_remaining": fs.get("balance_budget_remaining", b.get("original_budget", 0)),
            "over_commit_flag": fs.get("over_commit_flag", False),
            "last_updated": fs.get("last_recalculated") or b.get("updated_at") or datetime.utcnow(),
            "version": b.get("version", 1)
        }
        results.append(result)
    
    return [serialize_doc(r) for r in results]


@hardened_router.get("/projects/{project_id}/vendor-payables")
async def get_project_vendor_payables(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Aggregate vendor payables per vendor for the project.
    """
    from server import db, permission_checker
    
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id, require_write=False)
    
    pipeline = [
        {"$match": {"project_id": project_id}},
        {
            "$group": {
                "_id": "$vendor_id",
                "total_certified": {
                    "$sum": {
                        "$cond": [{"$eq": ["$entry_type", "PC_CERTIFIED"]}, "$amount", 0]
                    }
                },
                "total_paid": {
                    "$sum": {
                        "$cond": [{"$eq": ["$entry_type", "PAYMENT_MADE"]}, "$amount", 0]
                    }
                },
                "total_retention": {
                    "$sum": {
                        "$cond": [{"$eq": ["$entry_type", "RETENTION_HELD"]}, "$amount", 0]
                    }
                },
            }
        },
    ]
    
    results = await db.vendor_ledger.aggregate(pipeline).to_list(length=500)
    
    vendor_payables = []
    for r in results:
        vendor_id = r.get("_id")
        vendor = await db.vendors.find_one({"_id": ObjectId(vendor_id)})
        
        total_certified = float(r.get("total_certified", 0))
        total_paid = float(r.get("total_paid", 0))
        total_retention = float(r.get("total_retention", 0))
        net_payable = total_certified - total_paid - total_retention
        
        vendor_payables.append({
            "vendor_id": str(vendor_id) if vendor_id else None,
            "vendor_name": vendor.get("name") if vendor else "Unknown",
            "total_certified": total_certified,
            "total_paid": total_paid,
            "total_retention": total_retention,
            "total_payable": net_payable,
        })
    
    return vendor_payables


@hardened_router.get("/projects/{project_id}/cash-summary")
async def get_cash_summary(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get cash summary per category with threshold and countdown.
    """
    from server import db, permission_checker
    from decimal import Decimal
    from bson import Decimal128
    
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id, require_write=False)
    
    project = await db.projects.find_one({"project_id": project_id})
    organisation_id = user.get("organisation_id")
    
    default_threshold = Decimal("1000.0")
    
    categories = await db.categories.find({
        "organisation_id": organisation_id,
        "budget_type": "fund_transfer"
    }).to_list(length=100)
    
    allocations = await db.fund_allocations.find({"project_id": project_id}).to_list(length=100)
    allocation_by_cat = {str(a.get("category_id")): a for a in allocations}
    
    categories_data = []
    total_cash_in_hand = Decimal("0")
    latest_pc_close = None
    
    for cat in categories:
        cat_id = str(cat.get("_id"))
        allocation = allocation_by_cat.get(cat_id)
        
        if not allocation:
            continue
        
        threshold = Decimal(str(project.get(
            "threshold_petty" if "petty" in cat.get("name", "").lower() else "threshold_ovh",
            default_threshold
        )))
        
        cash_in_hand = Decimal(str(float(allocation.get("allocation_remaining", Decimal128("0")).to_decimal())))
        total_cash_in_hand += cash_in_hand
        
        last_pc_date = allocation.get("last_pc_closed_date")
        days_since_last_pc_close = None
        
        if last_pc_date:
            days_since_last_pc_close = (datetime.utcnow() - last_pc_date).days
            if latest_pc_close is None or last_pc_date > latest_pc_close:
                latest_pc_close = last_pc_date
        
        categories_data.append({
            "category_id": cat_id,
            "category_name": cat.get("name", "Unknown"),
            "cash_in_hand": float(cash_in_hand),
            "allocation_remaining": float(allocation.get("allocation_remaining", Decimal128("0")).to_decimal()),
            "allocation_total": float(allocation.get("allocation_original", Decimal128("0")).to_decimal()),
            "threshold": float(threshold),
            "days_since_last_pc_close": days_since_last_pc_close,
            "is_negative": cash_in_hand < 0,
            "is_below_threshold": cash_in_hand <= threshold,
        })
    
    days_since_last_pc_close_overall = None
    if latest_pc_close:
        days_since_last_pc_close_overall = (datetime.utcnow() - latest_pc_close).days
    
    return {
        "categories": categories_data,
        "summary": {
            "total_cash_in_hand": float(total_cash_in_hand),
            "days_since_last_pc_close": days_since_last_pc_close_overall,
        }
    }


# Late-initialized references (set by server.py on startup)
_db = None
_audit_service = None
_financial_service = None


def init_hardened_engine(db, audit_service, financial_service):
    """Initialize the hardened engine with database and service references."""
    global _db, _audit_service, _financial_service
    _db = db
    _audit_service = audit_service
    _financial_service = financial_service


class _HardenedEngine:
    async def modify_budget(
        self, budget_id, organisation_id, user_id, new_amount, expected_version: int
    ):
        from server import audit_service, financial_service
        
        async with db_manager.transaction_session() as session:
            # 1. Validate budget exists and belongs to org
            budget = await db_manager.db.project_category_budgets.find_one(
                {"_id": ObjectId(budget_id)},
                session=session
            )
            
            if not budget:
                raise HTTPException(status_code=404, detail="Budget not found")
            
            # Version Validation for Optimistic Concurrency
            current_version = budget.get("version", 1)
            if current_version != expected_version:
                raise HTTPException(
                    status_code=409,
                    detail={"error": "concurrency_conflict", "message": "This budget was modified in another session. Please reload and try again."}
                )
            
            # Organisation isolation
            project = await db_manager.db.projects.find_one(
                {"_id": ObjectId(budget.get("project_id"))},
                session=session
            )
            
            if not project or project.get("organisation_id") != organisation_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: budget does not belong to your organisation"
                )
            
            # 2. Validate amount constraints
            if new_amount is not None:
                if new_amount < 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Budget amount must be >= 0"
                    )
                
                committed_amount = Decimal(str(budget.get("committed_amount", "0")))
                if new_amount < committed_amount:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot reduce budget below committed amount (₹{committed_amount})"
                    )
            
            # 3. Record old value
            old_amount = budget.get("original_budget", 0)
            
            # 4. Update budget
            update_fields = {"updated_at": datetime.utcnow()}
            if new_amount is not None:
                update_fields["original_budget"] = new_amount
                # Also recalculate remaining budget locally
                committed = Decimal(str(budget.get("committed_amount", "0")))
                update_fields["remaining_budget"] = Decimal128(str(new_amount - committed))
            
            await db_manager.db.project_category_budgets.update_one(
                {"_id": ObjectId(budget_id)},
                {"$set": update_fields, "$inc": {"version": 1}},
                session=session
            )
            
            # 5. Trigger financial recalculation
            project_id = budget.get("project_id")
            category_id = budget.get("category_id")
            
            if project_id and category_id:
                await financial_service.recalculate_project_code_financials(
                    project_id=project_id,
                    category_id=category_id,
                    session=session
                )
            
            # 6. Audit log with FULL JSON snapshots
            # Fetch updated budget for complete snapshot
            updated_budget = await db_manager.db.project_category_budgets.find_one(
                {"_id": ObjectId(budget_id)},
                session=session
            )
            
            await audit_service.log_action(
                organisation_id=organisation_id,
                module_name="BUDGET_MANAGEMENT",
                entity_type="BUDGET",
                entity_id=budget_id,
                action_type="UPDATE",
                user_id=user_id,
                old_value=serialize_doc(budget),  # FULL JSON snapshot per spec 6.1.2
                new_value=serialize_doc(updated_budget),  # FULL JSON snapshot per spec 6.1.2
                session=session
            )
            
            logger.info(
                f"Budget {budget_id} modified: {old_amount} -> {new_amount} "
                f"by user {user_id}"
            )
            
            return {
                "budget_id": budget_id,
                "old_amount": old_amount,
                "new_amount": new_amount,
                "recalculated": True
            }


hardened_engine = _HardenedEngine()


@hardened_router.put("/budgets/{budget_id}")
async def update_budget_hardened(
    budget_id: str,
    budget_data: ProjectBudgetUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Hardened update of a project budget with transaction and audit."""
    from server import permission_checker
    
    user = await permission_checker.get_authenticated_user(current_user)
    
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await permission_checker.check_web_crm_access(user)
    await permission_checker.check_client_readonly(user)
    await permission_checker.check_admin_role(user)
    
    return await hardened_engine.modify_budget(
        budget_id=budget_id,
        organisation_id=user["organisation_id"],
        user_id=user["user_id"],
        new_amount=budget_data.original_budget,
        expected_version=budget_data.version
    )


@hardened_router.post("/projects/{project_id}/initialize-budgets")
async def initialize_project_budgets(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Initialize a project with all categories with 0 budget.
    Ensures financial state is created for all codes.
    """
    from server import db, permission_checker, financial_service
    
    user = await permission_checker.get_authenticated_user(current_user)
    
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await permission_checker.check_web_crm_access(user)
    await permission_checker.check_client_readonly(user)
    await permission_checker.check_admin_role(user)
    
    # 1. Get all codes
    codes = await db.code_master.find({"active_status": True}).to_list(length=None)
    
    async with db_manager.transaction_session() as session:
        fund_transfer_count = 0
        
        for code in codes:
            category_id = str(code["_id"])
            
            # Check if exists
            existing = await db.project_category_budgets.find_one({
                "project_id": project_id,
                "category_id": category_id
            }, session=session)
            
            if not existing:
                budget_doc = {
                    "project_id": project_id,
                    "category_id": category_id,
                    "original_budget": Decimal128("0.0"),
                    "committed_amount": Decimal128("0.0"),
                    "remaining_budget": Decimal128("0.0"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "version": 1
                }
                await db.project_category_budgets.insert_one(budget_doc, session=session)
            
            # 3.1.2: Auto-create fund_allocations for fund_transfer categories
            # Use original_budget from the category budget (which may be set by user after init)
            budget_type = code.get("budget_type", "commitment")
            
            if budget_type == "fund_transfer":
                existing_allocation = await db.fund_allocations.find_one({
                    "project_id": project_id,
                    "category_id": category_id
                }, session=session)
                
                if not existing_allocation:
                    # Get original_budget from project_category_budgets if it exists
                    category_budget = await db.project_category_budgets.find_one({
                        "project_id": project_id,
                        "category_id": category_id
                    }, session=session)
                    
                    original_budget = float(category_budget.get("original_budget", Decimal128("0")).to_decimal()) if category_budget else 0.0
                    
                    allocation_doc = {
                        "project_id": project_id,
                        "category_id": category_id,
                        "allocation_original": Decimal128(str(original_budget)),
                        "allocation_received": Decimal128("0.0"),
                        "allocation_remaining": Decimal128(str(original_budget)),  # Per spec: allocation_remaining = original_budget
                        "last_pc_closed_date": None,
                        "version": 1,
                        "created_at": datetime.utcnow()
                    }
                    await db.fund_allocations.insert_one(allocation_doc, session=session)
                    fund_transfer_count += 1
        
        # Recalculate everything for this project
        # Note: financial_service.recalculate_all_project_financials does not yet accept session
        await financial_service.recalculate_all_project_financials(project_id)
        
        # Compute master budgets after initialization
        await financial_service.recalculate_master_budget(project_id, session=session)
    
    return {
        "status": "success",
        "message": f"Initialized budgets for {len(codes)} categories",
        "fund_allocations_created": fund_transfer_count
    }
