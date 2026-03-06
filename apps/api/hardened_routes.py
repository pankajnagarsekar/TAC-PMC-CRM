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
    budgets = await db.project_budgets.find({"project_id": project_id}).to_list(length=500)
    
    # 2. Get all financial state records for the project
    states = await db.financial_state.find({"project_id": project_id}).to_list(length=500)
    state_map = {s.get("category_id") or s.get("code_id"): s for s in states}
    
    # 3. Join them
    results = []
    for b in budgets:
        cid = b.get("category_id") or b.get("code_id")
        fs = state_map.get(cid, {})
        
        # Merge data into DerivedFinancialState structure
        result = {
            "project_id": project_id,
            "code_id": cid,
            "approved_budget_amount": b.get("approved_budget_amount", 0),
            "committed_value": fs.get("committed_value", 0),
            "certified_value": fs.get("certified_value", 0),
            "balance_budget_remaining": fs.get("balance_budget_remaining", b.get("approved_budget_amount", 0)),
            "over_commit_flag": fs.get("over_commit_flag", False),
            "last_updated": fs.get("last_recalculated") or b.get("updated_at") or datetime.utcnow(),
            "version": b.get("version", 1)
        }
        results.append(result)
        
    return [serialize_doc(r) for r in results]


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
            self,
            budget_id,
            organisation_id,
            user_id,
            new_amount,
            expected_version: int):
        from server import audit_service, financial_service
        
        async with db_manager.transaction_session() as session:
            # 1. Validate budget exists and belongs to org
            budget = await db_manager.db.project_budgets.find_one({
                "_id": ObjectId(budget_id)
            }, session=session)

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
            project = await db_manager.db.projects.find_one({
                "_id": ObjectId(budget.get("project_id"))
            }, session=session)

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
            old_amount = budget.get("approved_budget_amount", 0)

            # 4. Update budget
            update_fields = {"updated_at": datetime.utcnow()}
            if new_amount is not None:
                update_fields["approved_budget_amount"] = new_amount
                # Also recalculate remaining budget locally
                committed = Decimal(str(budget.get("committed_amount", "0")))
                update_fields["remaining_budget"] = Decimal128(str(new_amount - committed))

            await db_manager.db.project_budgets.update_one(
                {"_id": ObjectId(budget_id)},
                {"$set": update_fields, "$inc": {"version": 1}},
                session=session
            )

            # 5. Trigger financial recalculation
            project_id = budget.get("project_id")
            code_id = budget.get("code_id")

            if project_id and code_id:
                await financial_service.recalculate_project_code_financials(
                    project_id=project_id,
                    code_id=code_id,
                    session=session
                )

            # 6. Audit log
            await audit_service.log_action(
                organisation_id=organisation_id,
                module_name="BUDGET_MANAGEMENT",
                entity_type="BUDGET",
                entity_id=budget_id,
                action_type="UPDATE",
                user_id=user_id,
                old_value={"approved_budget_amount": old_amount},
                new_value={"approved_budget_amount": new_amount},
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
    await permission_checker.check_admin_role(user)

    return await hardened_engine.modify_budget(
        budget_id=budget_id,
        organisation_id=user["organisation_id"],
        user_id=user["user_id"],
        new_amount=budget_data.approved_budget_amount,
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
    await permission_checker.check_admin_role(user)

    # 1. Get all codes
    codes = await db.code_master.find({"active_status": True}).to_list(length=None)

    async with db_manager.transaction_session() as session:
        for code in codes:
            code_id = str(code["_id"])
            # Check if exists
            existing = await db.project_budgets.find_one({
                "project_id": project_id,
                "code_id": code_id
            }, session=session)

            if not existing:
                budget_doc = {
                    "project_id": project_id,
                    "code_id": code_id,
                    "approved_budget_amount": Decimal128("0.0"),
                    "committed_amount": Decimal128("0.0"),
                    "remaining_budget": Decimal128("0.0"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "version": 1
                }
                await db.project_budgets.insert_one(budget_doc, session=session)

        # Recalculate everything for this project
        # Note: financial_service.recalculate_all_project_financials does not yet accept session
        await financial_service.recalculate_all_project_financials(project_id)
        # Compute master budgets after initialization
        await financial_service.recalculate_master_budget(project_id, session=session)

    return {"status": "success", "message": f"Initialized budgets for {len(codes)} categories"}
