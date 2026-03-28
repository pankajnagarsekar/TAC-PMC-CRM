import logging
from typing import Dict, Any, List, Optional
from bson import Decimal128
from fastapi import HTTPException, status

from ..infrastructure.repository import (
    PCRepository, FinancialStateRepository, CodeMasterRepository
)
# Note: Repositories from other contexts
from app.modules.project.infrastructure.repository import ProjectRepository, BudgetRepository
from app.modules.contracting.infrastructure.repository import WorkOrderRepository, VendorRepository

from app.core.time import now
from app.core.financial_utils import to_decimal, to_d128
from app.modules.shared.domain.financial_engine import FinancialEngine

logger = logging.getLogger(__name__)

class FinancialService:
    """
    Sovereign Logic Orchestrator for Financial Domain.
    Delegates all mathematical logic to the FinancialEngine.
    """
    def __init__(self, db):
        self.db = db
        self.budget_repo = BudgetRepository(db)
        self.wo_repo = WorkOrderRepository(db)
        self.pc_repo = PCRepository(db)
        self.financial_state_repo = FinancialStateRepository(db)
        self.code_master_repo = CodeMasterRepository(db)
        self.project_repo = ProjectRepository(db)
        self.vendor_repo = VendorRepository(db)

    async def recalculate_project_code_financials(self, project_id: str, category_id: str, session=None):
        """Standard recurrence pattern for project-category financial health."""
        budget = await self.budget_repo.get_by_project_and_category(project_id, category_id, session=session)
        if not budget:
            return None

        approved_budget = to_decimal(budget.get("original_budget", "0"))

        committed_pipeline = [
            {"$match": {
                "project_id": project_id,
                "category_id": category_id,
                "status": {"$nin": ["Cancelled"]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
        ]
        committed_result = await self.wo_repo.aggregate(committed_pipeline, session=session)
        committed_value = to_decimal(committed_result[0].get("total") if committed_result else None)

        certified_pipeline = [
            {"$match": {
                "project_id": project_id,
                "category_id": category_id,
                "status": "Closed"
            }},
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
        ]
        certified_result = await self.pc_repo.aggregate(certified_pipeline, session=session)
        certified_value = to_decimal(certified_result[0].get("total") if certified_result else None)

        balance_remaining = FinancialEngine.round(approved_budget - committed_value)
        over_commit = committed_value > approved_budget

        serializable_doc = {
            "project_id": project_id,
            "category_id": category_id,
            "original_budget": to_d128(approved_budget),
            "committed_value": to_d128(committed_value),
            "certified_value": to_d128(certified_value),
            "balance_budget_remaining": to_d128(balance_remaining),
            "over_commit_flag": over_commit,
            "logic_version": FinancialEngine.DOMAIN_LOGIC_VERSION,
            "last_recalculated": now()
        }

        await self.financial_state_repo.update_one(
            {"project_id": project_id, "category_id": category_id},
            {"$set": serializable_doc},
            session=session,
            upsert=True
        )

        return serializable_doc

    async def recalculate_master_budget(self, project_id: str, session=None):
        """Aggregates all project categories into a single Master Snapshot."""
        budgets = await self.budget_repo.list({"project_id": project_id}, limit=1000)
        
        totals = {
            "total_budget": FinancialEngine.round(0),
            "total_committed": FinancialEngine.round(0),
            "total_certified": FinancialEngine.round(0),
            "categories_recalculated": 0
        }

        for b in budgets:
            cat_id = b.get("category_id")
            if not cat_id: continue
            
            res = await self.recalculate_project_code_financials(project_id, cat_id, session=session)
            if res:
                totals["total_budget"] += to_decimal(res["original_budget"])
                totals["total_committed"] += to_decimal(res["committed_value"])
                totals["total_certified"] += to_decimal(res["certified_value"])
                totals["categories_recalculated"] += 1

        master_doc = {
            "project_id": project_id,
            "category_id": None,
            "original_budget": to_d128(totals["total_budget"]),
            "committed_value": to_d128(totals["total_committed"]),
            "certified_value": to_d128(totals["total_certified"]),
            "balance_budget_remaining": to_d128(totals["total_budget"] - totals["total_committed"]),
            "categories_recalculated": totals["categories_recalculated"],
            "logic_version": FinancialEngine.DOMAIN_LOGIC_VERSION,
            "last_recalculated": now()
        }

        await self.financial_state_repo.update_one(
            {"project_id": project_id, "category_id": None},
            {"$set": master_doc},
            session=session,
            upsert=True
        )

        return master_doc

    async def check_threshold_breach(self, project_id: str, category_id: str, session=None) -> bool:
        """System Gate: Prevent unauthorized spending on depleted funds."""
        allocation = await self.db.fund_allocations.find_one(
            {"project_id": project_id, "category_id": category_id},
            {"cash_in_hand": 1},
            session=session
        )
        if not allocation: return False

        cash_in_hand = to_decimal(allocation.get("cash_in_hand", 0))
        project = await self.project_repo.get_by_id(project_id, session=session)
        if not project: return False

        category = await self.code_master_repo.get_by_id(category_id, session=session)
        if not category:
            category = await self.code_master_repo.find_one({"code": category_id}, session=session)
        
        if category and category.get("budget_type") == "fund_transfer":
            cat_name = category.get("category_name", "").lower()
            threshold = to_decimal(project.get("threshold_ovh", "0") if "ovh" in cat_name else project.get("threshold_petty", "0"))
            return cash_in_hand <= threshold
        
        return False
