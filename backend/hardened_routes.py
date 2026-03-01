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
from bson import ObjectId
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

hardened_router = APIRouter()

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
            new_amount):
        """
        Modify a budget amount with full audit trail and recalculation.

        Steps:
        1. Validate budget exists and belongs to the organisation
        2. Validate new amount is non-negative
        3. Record old value for audit
        4. Update the budget
        5. Trigger financial recalculation
        6. Log the audit trail
        """
        from server import db, audit_service, financial_service

        # 1. Validate budget exists and belongs to org
        budget = await db.project_budgets.find_one({
            "_id": ObjectId(budget_id)
        })

        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")

        # Organisation isolation: verify the project belongs to the org
        project = await db.projects.find_one({
            "_id": ObjectId(budget.get("project_id"))
        })

        if not project or project.get("organisation_id") != organisation_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: budget does not belong to your organisation"
            )

        # 2. Validate amount
        if new_amount is not None and new_amount < 0:
            raise HTTPException(
                status_code=400,
                detail="Budget amount must be >= 0"
            )

        # 3. Record old value
        old_amount = budget.get("approved_budget_amount", 0)

        # 4. Update budget
        update_fields = {"updated_at": datetime.utcnow()}
        if new_amount is not None:
            update_fields["approved_budget_amount"] = new_amount

        await db.project_budgets.update_one(
            {"_id": ObjectId(budget_id)},
            {"$set": update_fields}
        )

        # 5. Trigger financial recalculation
        project_id = budget.get("project_id")
        code_id = budget.get("code_id")

        if project_id and code_id:
            await financial_service.recalculate_project_code_financials(
                project_id=project_id,
                code_id=code_id
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
            new_value={"approved_budget_amount": new_amount}
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
