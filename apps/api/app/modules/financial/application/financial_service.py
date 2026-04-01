import logging


from app.core.time import now
from app.modules.contracting.infrastructure.repository import (
    VendorRepository,
    WorkOrderRepository,
)

# Note: Repositories from other contexts
from app.modules.project.infrastructure.repository import (
    BudgetRepository,
    ProjectRepository,
)
from app.modules.shared.domain.financial_engine import FinancialEngine

from ..domain.models import FinancialState
from ..infrastructure.repository import (
    CodeMasterRepository,
    FinancialStateRepository,
    PCRepository,
)
from app.modules.shared.domain.exceptions import ValidationError

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

    async def recalculate_project_code_financials(
        self, project_id: str, category_id: str, session=None
    ):
        """Standard recurrence pattern for project-category financial health."""
        budget = await self.budget_repo.get_by_project_and_category(
            project_id, category_id, session=session
        )
        if not budget:
            return None

        approved_budget = FinancialEngine.to_decimal(budget.get("original_budget", "0"))

        committed_pipeline = [
            {
                "$match": {
                    "project_id": project_id,
                    "category_id": category_id,
                    "status": {"$nin": ["Cancelled"]},
                }
            },
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}},
        ]
        committed_result = await self.wo_repo.aggregate(
            committed_pipeline, session=session
        ).to_list(length=1)
        committed_value = FinancialEngine.to_decimal(
            committed_result[0].get("total") if committed_result else None
        )

        certified_pipeline = [
            {
                "$match": {
                    "project_id": project_id,
                    "category_id": category_id,
                    "status": "Closed",
                }
            },
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}},
        ]
        certified_result = await self.pc_repo.aggregate(
            certified_pipeline, session=session
        ).to_list(length=1)
        certified_value = FinancialEngine.to_decimal(
            certified_result[0].get("total") if certified_result else None
        )

        # Use Domain Aggregate for Invariants and Calculations
        state = FinancialState(
            {
                "project_id": project_id,
                "category_id": category_id,
                "original_budget": approved_budget,
                "committed_value": committed_value,
                "certified_value": certified_value,
            }
        )

        serializable_doc = {
            "project_id": project_id,
            "category_id": category_id,
            "code_id": category_id,
            "original_budget": FinancialEngine.to_d128(state.original_budget),
            "committed_value": FinancialEngine.to_d128(state.committed_value),
            "certified_value": FinancialEngine.to_d128(state.certified_value),
            "balance_budget_remaining": FinancialEngine.to_d128(
                state.balance_remaining
            ),
            "over_commit_flag": state.is_over_committed,
            "logic_version": FinancialEngine.DOMAIN_LOGIC_VERSION,
            "last_recalculated": now(),
        }

        await self.financial_state_repo.update_one(
            {"project_id": project_id, "category_id": category_id},
            {"$set": serializable_doc},
            session=session,
            upsert=True,
        )

        return serializable_doc

    async def recalculate_master_budget(self, project_id: str, session=None):
        """Aggregates all project categories into a single Master Snapshot."""
        budgets = await self.budget_repo.list({"project_id": project_id}, limit=1000)

        totals = {
            "total_budget": FinancialEngine.round(0),
            "total_committed": FinancialEngine.round(0),
            "total_certified": FinancialEngine.round(0),
            "categories_recalculated": 0,
        }

        for b in budgets:
            cat_id = b.get("category_id")
            if not cat_id:
                continue

            res = await self.recalculate_project_code_financials(
                project_id, cat_id, session=session
            )
            if res:
                totals["total_budget"] += FinancialEngine.to_decimal(
                    res["original_budget"]
                )
                totals["total_committed"] += FinancialEngine.to_decimal(
                    res["committed_value"]
                )
                totals["total_certified"] += FinancialEngine.to_decimal(
                    res["certified_value"]
                )
                totals["categories_recalculated"] += 1

        master_doc = {
            "project_id": project_id,
            "category_id": None,
            "original_budget": FinancialEngine.to_d128(totals["total_budget"]),
            "committed_value": FinancialEngine.to_d128(totals["total_committed"]),
            "certified_value": FinancialEngine.to_d128(totals["total_certified"]),
            "balance_budget_remaining": FinancialEngine.to_d128(
                totals["total_budget"] - totals["total_committed"]
            ),
            "categories_recalculated": totals["categories_recalculated"],
            "logic_version": FinancialEngine.DOMAIN_LOGIC_VERSION,
            "last_recalculated": now(),
        }

        await self.financial_state_repo.update_one(
            {"project_id": project_id, "category_id": None},
            {"$set": master_doc},
            session=session,
            upsert=True,
        )

        return master_doc

    async def check_threshold_breach(
        self, project_id: str, category_id: str, session=None
    ) -> bool:
        """System Gate: Prevent unauthorized spending on depleted funds."""
        allocation = await self.db.fund_allocations.find_one(
            {"project_id": project_id, "category_id": category_id},
            {"cash_in_hand": 1},
            session=session,
        )
        if not allocation:
            return False

        cash_in_hand = FinancialEngine.to_decimal(allocation.get("cash_in_hand", 0))
        project = await self.project_repo.get_by_id(project_id, session=session)
        if not project:
            return False

        category = await self.code_master_repo.get_by_id(category_id, session=session)
        if not category:
            category = await self.code_master_repo.find_one(
                {"code": category_id}, session=session
            )

        if category and category.get("budget_type") == "fund_transfer":
            cat_name = category.get("category_name", "").lower()
            threshold = FinancialEngine.to_decimal(
                project.get("threshold_ovh", "0")
                if "ovh" in cat_name
                else project.get("threshold_petty", "0")
            )

            # Domain logic delegate
            state = FinancialState(
                {"project_id": project_id, "category_id": category_id}
            )
            return state.is_threshold_breached(cash_in_hand, threshold)

        return False

    async def validate_financial_document(self, doc_type: str, data: dict, project_id: str):
        """Validate financial document data before creation (BUG-29)."""
        if doc_type == "WORK_ORDER":
            if not data.get("line_items"):
                raise ValidationError("Work order requires at least one line item")
            if not data.get("vendor_id"):
                raise ValidationError("Work order requires a vendor")
            if not data.get("category_id"):
                raise ValidationError("Work order requires a category")
        # Add more doc_type validations as needed
