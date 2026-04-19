import logging
from decimal import Decimal


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
    FundAllocationRepository,
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
        self.fund_allocations_repo = FundAllocationRepository(db)

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

        from bson import ObjectId
        p_id_obj = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        c_id_obj = ObjectId(category_id) if ObjectId.is_valid(category_id) else category_id

        committed_pipeline = [
            {
                "$match": {
                    "project_id": {"$in": [project_id, p_id_obj]},
                    "category_id": {"$in": [category_id, c_id_obj]},
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
                    "project_id": {"$in": [project_id, p_id_obj]},
                    "category_id": {"$in": [category_id, c_id_obj]},
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
        budgets = await self.budget_repo.list({"project_id": project_id}, limit=1000, session=session)

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
                
                # CALC-4: For fund transfer categories, Certified amount acts as a commitment
                cat = await self.code_master_repo.get_by_id(cat_id, session=session)
                if not cat:
                    cat = await self.code_master_repo.find_one({"code": cat_id}, session=session)
                
                if cat and cat.get("budget_type") == "fund_transfer":
                    totals["total_committed"] += FinancialEngine.to_decimal(
                        res["certified_value"]
                    )
                else:
                    totals["total_committed"] += FinancialEngine.to_decimal(
                        res["committed_value"]
                    )
                
                totals["total_certified"] += FinancialEngine.to_decimal(
                    res["certified_value"]
                )
                totals["categories_recalculated"] += 1

        # Final snapshot for executive dashboard
        master_snapshot = {
            "project_id": project_id,
            "category_id": "MASTER",
            "original_budget": FinancialEngine.to_d128(totals["total_budget"]),
            "committed_value": FinancialEngine.to_d128(totals["total_committed"]),
            "certified_value": FinancialEngine.to_d128(totals["total_certified"]),
            "balance_remaining": FinancialEngine.to_d128(
                totals["total_budget"] - totals["total_committed"]
            ),
            "recalculated_at": now(),
            "logic_version": FinancialEngine.DOMAIN_LOGIC_VERSION,
        }

        await self.financial_state_repo.update_one(
            {"project_id": project_id, "category_id": "MASTER"},
            {"$set": master_snapshot},
            session=session,
            upsert=True,
        )

        # Invalidate Dashboard Cache (BUG-009)
        try:
            from app.modules.reporting.application.dashboard_service import DashboardService
            DashboardService.invalidate_project_cache(project_id)
        except Exception as e:
            logger.warning(f"DASHBOARD_CACHE_INVALIDATE_FAILED for {project_id}: {str(e)}")

        return master_snapshot

    async def check_threshold_breach(
        self, project_id: str, category_id: str, session=None
    ) -> bool:
        """System Gate: Prevent unauthorized spending on depleted funds."""
        allocation = await self.fund_allocations_repo.find_one(
            {"project_id": project_id, "category_id": category_id},
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
        elif doc_type == "PAYMENT_CERTIFICATE":
            if not data.get("line_items"):
                raise ValidationError("Payment Certificate requires at least one line item")
            if data.get("fund_request"):
                if data.get("work_order_id"):
                    raise ValidationError("Fund request cannot be linked to a Work Order")
                if not data.get("category_id"):
                    raise ValidationError("Fund request requires a category")
            else:
                if not data.get("work_order_id"):
                    raise ValidationError("Non-fund request requires a Work Order")
                if not data.get("vendor_id"):
                    raise ValidationError("Non-fund request requires a vendor")
        # Add more doc_type validations as needed

    async def create_budget(
        self,
        user: dict,
        project_id: str,
        category_id: str,
        original_budget: Decimal,
        session=None,
    ) -> dict:
        """Authoritative creation of a category budget with master sync (Point H3)."""
        # 1. Validation
        if original_budget < 0:
            raise ValidationError("Budget cannot be negative.")

        # 2. Persist
        budget_doc = {
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "category_id": category_id,
            "original_budget": FinancialEngine.to_d128(original_budget),
            "committed_amount": FinancialEngine.to_d128(Decimal("0.0")),
            "remaining_budget": FinancialEngine.to_d128(original_budget),
            "version": 1,
            "created_at": now(),
            "updated_at": now(),
        }
        
        await self.budget_repo.create(budget_doc, session=session)

        # 3. Trigger Master Recalculation (H3)
        return await self.recalculate_master_budget(project_id, session=session)

    async def update_budget(
        self,
        user: dict,
        project_id: str,
        category_id: str,
        original_budget: Decimal,
        session=None,
    ) -> dict:
        """Atomic Update for Category Budget with validation (Track H1)."""
        organisation_id = user["organisation_id"]

        # 1. Fetch current status (Recalculate first to be sure)
        status = await self.recalculate_project_code_financials(
            project_id, category_id, session=session
        )
        if not status:
            # Fallback: check if budget actually exists but status isn't derived yet
            existing = await self.budget_repo.get_by_project_and_category(project_id, category_id, session=session)
            if not existing:
                raise ValidationError(f"Budget for category {category_id} not found.")
            committed = 0
        else:
            committed = FinancialEngine.to_decimal(status.get("committed_value", 0))

        # 2. H1: Backend Validation
        if original_budget < 0:
            raise ValidationError("Budget cannot be negative.")

        if original_budget < committed:
            raise ValidationError(
                f"Budget cannot be reduced below committed amount of ₹{committed:,.2f}"
            )

        # 3. Update the budget record
        update_data = {
            "original_budget": FinancialEngine.to_d128(original_budget),
            "updated_at": now(),
        }
        await self.budget_repo.update_one(
            {"project_id": project_id, "category_id": category_id},
            {"$set": update_data},
            session=session,
        )

        # 4. Trigger Master Recalculation (H3)
        return await self.recalculate_master_budget(project_id, session=session)
