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

    def __init__(self, db, audit_service, scheduler_service=None):
        self.db = db
        self.audit_service = audit_service
        self.scheduler_service = scheduler_service
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
        # Ensure ID consistency (BUG-001 Mitigation)
        project_id = str(project_id)
        category_id = str(category_id)

        budget = await self.budget_repo.get_by_project_and_category(
            project_id, category_id, session=session
        )
        approved_budget = FinancialEngine.to_decimal(budget.get("original_budget", "0")) if budget else Decimal("0.00")

        from bson import ObjectId
        p_id_obj = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        c_id_obj = ObjectId(category_id) if ObjectId.is_valid(category_id) else category_id

        # BUG-002: Committed strictly maps to Grand Total of non-cancelled WOs
        # OR non-cancelled PCs for fund_transfer categories (BUG-004)
        cat = await self.code_master_repo.get_by_id(category_id, session=session)
        if not cat:
            cat = await self.code_master_repo.find_one({"code": category_id}, session=session)

        is_fund_transfer = cat and cat.get("budget_type") == "fund_transfer"

        if is_fund_transfer:
            # For Petty Cash/SOH, PCs ARE the commitment
            committed_pipeline = [
                {
                    "$match": {
                        "project_id": {"$in": [project_id, p_id_obj]},
                        "category_id": {"$in": [category_id, c_id_obj]},
                        "status": {"$nin": ["Cancelled"]},  # Include Draft/Approved as commitment
                    }
                },
                {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}},
            ]
            committed_result = await self.pc_repo.aggregate(
                committed_pipeline, session=session
            ).to_list(length=1)
        else:
            committed_pipeline = [
                {
                    "$match": {
                        "project_id": {"$in": [project_id, p_id_obj]},
                        "category_id": {"$in": [category_id, c_id_obj]},
                        "status": {"$nin": ["Cancelled", "Draft"]},  # Exclude Draft to prevent speculative commitments
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
                    "status": {"$in": ["Approved", "Payment Raised", "Processing", "Paid"]},
                }
            },
            # BUG-001: Certified strictly maps to Net Payable (net_payable)
            {
                "$group": {
                    "_id": None,
                    "total": {
                        "$sum": {
                            "$ifNull": ["$net_payable", {"$ifNull": ["$total_payable", "$grand_total"]}]
                        }
                    }
                }
            },
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
            "version": budget.get("version", 1) if budget else 1,
        }

        # Authoritative Unique Constraint Enforcement (BUG-001)
        await self.financial_state_repo.delete_many(
            {"project_id": project_id, "category_id": category_id},
            session=session
        )

        await self.financial_state_repo.create(serializable_doc, session=session)

        return serializable_doc

    async def recalculate_master_budget(self, project_id: str, session=None):
        """Aggregates all project categories into a single Master Snapshot."""
        project_id = str(project_id)
        from bson import ObjectId
        p_id_obj = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id

        # 1. Identify all unique categories involved in this project (Budget, WorkOrders, PCs)
        category_ids = set()

        # From Budgets
        budgets = await self.budget_repo.list(
            {"project_id": {"$in": [project_id, p_id_obj]}}, limit=1000, session=session
        )
        for b in budgets:
            if b.get("category_id"):
                category_ids.add(str(b["category_id"]))

        # From Work Orders
        wo_cats = await self.wo_repo.distinct("category_id", {"project_id": {"$in": [project_id, p_id_obj]}})
        for cid in wo_cats:
            if cid:
                category_ids.add(str(cid))

        # From PCs
        pc_cats = await self.pc_repo.distinct("category_id", {"project_id": {"$in": [project_id, p_id_obj]}})
        for cid in pc_cats:
            if cid:
                category_ids.add(str(cid))

        # BUG-005: Ensure we don't treat "MASTER" or the Project ID itself as a category
        category_ids.discard(FinancialEngine.MASTER_CATEGORY)
        category_ids.discard(project_id)
        if ObjectId.is_valid(project_id):
            category_ids.discard(str(ObjectId(project_id)))

        # BUG-001 Cleanup: Purge orphaned/stale financial state entries
        # This ensures "ghost" numbers from old categories or different ID formats are removed.
        await self.financial_state_repo.delete_many(
            {
                "project_id": {"$in": [project_id, p_id_obj]},
                "category_id": {"$nin": list(category_ids) + [FinancialEngine.MASTER_CATEGORY]}
            },
            session=session
        )

        totals = {
            "total_budget": FinancialEngine.round(0),
            "total_committed": FinancialEngine.round(0),
            "total_certified": FinancialEngine.round(0),
            "categories_recalculated": 0,
        }

        for cat_id in category_ids:
            res = await self.recalculate_project_code_financials(
                project_id, cat_id, session=session
            )
            if res:
                totals["total_budget"] += FinancialEngine.to_decimal(
                    res["original_budget"]
                )

                # Committed is already correctly calculated in recalculate_project_code_financials
                # (Whether it's based on WOs or PCs depends on budget_type)
                totals["total_committed"] += FinancialEngine.to_decimal(
                    res["committed_value"]
                )

                totals["total_certified"] += FinancialEngine.to_decimal(
                    res["certified_value"]
                )
                totals["categories_recalculated"] += 1

        # Final snapshot for executive dashboard
        if totals["total_budget"] == Decimal("0") and totals["categories_recalculated"] == 0:
            project = await self.project_repo.get_by_id(project_id, session=session)
            if project:
                totals["total_budget"] = FinancialEngine.to_decimal(project.get("master_original_budget", "0"))

        # BUG-001: Remaining = Budget - max(Committed, Certified)
        master_remaining = totals["total_budget"] - max(totals["total_committed"], totals["total_certified"])

        master_snapshot = {
            "project_id": project_id,
            "category_id": FinancialEngine.MASTER_CATEGORY,
            "original_budget": FinancialEngine.to_d128(totals["total_budget"]),
            "committed_value": FinancialEngine.to_d128(totals["total_committed"]),
            "certified_value": FinancialEngine.to_d128(totals["total_certified"]),
            "balance_remaining": FinancialEngine.to_d128(master_remaining),
            "balance_budget_remaining": FinancialEngine.to_d128(master_remaining),  # Alias for consistency
            "recalculated_at": now(),
            "logic_version": FinancialEngine.DOMAIN_LOGIC_VERSION,
        }

        await self.financial_state_repo.update_one(
            {"project_id": project_id, "category_id": FinancialEngine.MASTER_CATEGORY},
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

        # SYNC: Update Scheduler UI Data (Track H1, BUG-5)
        if self.scheduler_service:
            try:
                # We don't have organisation_id here, but we can try to get it from project
                project = await self.project_repo.get_by_id(project_id, session=session)
                org_id = project.get("organisation_id") if project else None
                if org_id:
                    await self.scheduler_service.sync_financials(
                        project_id, org_id, session=session
                    )
            except Exception as e:
                logger.error(f"SCHEDULER_SYNC_FAILED for {project_id}: {str(e)}")

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
        """Validate financial document data before creation (BUG-29, BUG-009)."""
        line_items = data.get("line_items", [])
        if not line_items or len(line_items) == 0:
            raise ValidationError(f"{doc_type.replace('_', ' ').title()} requires at least one line item.")

        # BUG-009: Authoritative Invariant: Declared Subtotal must match Line Item Sum
        declared_subtotal = FinancialEngine.to_decimal(data.get("subtotal", 0))
        calculated_subtotal = Decimal("0.00")
        for item in line_items:
            qty = FinancialEngine.to_decimal(item.get("qty", 0))
            rate = FinancialEngine.to_decimal(item.get("rate", 0))
            calculated_subtotal += FinancialEngine.round(qty * rate)

        if declared_subtotal != calculated_subtotal and declared_subtotal != Decimal("0.00"):
            # If subtotal is provided but mismatched, fail.
            # If 0.00, we might be in 'creation' where it's not yet set in dict.
            raise ValidationError(
                f"Document subtotal mismatch. Declared: {declared_subtotal}, Calculated: {calculated_subtotal}"
            )

        if doc_type == "WORK_ORDER":
            if not data.get("vendor_id"):
                raise ValidationError("Work order requires a vendor")
            if not data.get("category_id"):
                raise ValidationError("Work order requires a category")
        elif doc_type == "PAYMENT_CERTIFICATE":
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

        budget_doc = await self.budget_repo.create(budget_doc, session=session)

        # BUG-007: Audit Logging
        await self.audit_service.log_financial_event(
            organisation_id=user["organisation_id"],
            entity_type="BUDGET",
            entity_id=str(budget_doc["id"]),
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=project_id,
            new_value=budget_doc,
            session=session,
        )

        # 3. Trigger Master Recalculation (H3)
        return await self.recalculate_master_budget(project_id, session=session)

    async def update_budget(
        self,
        user: dict,
        project_id: str,
        category_id: str,
        original_budget: Decimal,
        expected_version: int,
        reason: str,
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
            budget_id = str(existing["_id"])
        else:
            committed = FinancialEngine.to_decimal(status.get("committed_value", 0))
            # Status should have the budget doc ID as 'id' or '_id'
            budget_id = str(status.get("_id") or status.get("id"))
            if not budget_id or budget_id == "None":
                # Fallback to direct fetch if status doesn't have ID
                existing = await self.budget_repo.get_by_project_and_category(
                    project_id, category_id, session=session
                )
                budget_id = str(existing["_id"])

        # 2. H1: Backend Validation
        if original_budget < 0:
            raise ValidationError("Budget cannot be negative.")

        if original_budget < committed:
            raise ValidationError(
                f"Budget cannot be reduced below committed amount of ₹{committed:,.2f}"
            )

        # 3. Update the budget record with OCC
        update_data = {
            "original_budget": FinancialEngine.to_d128(original_budget),
            "updated_at": now(),
            "version": expected_version + 1,
        }

        result = await self.budget_repo.update(
            budget_id,
            update_data,
            organisation_id=organisation_id,
            expected_version=expected_version,
            session=session
        )

        if not result:
            raise ValidationError("CONFLICT: Budget was modified by another process (Version Mismatch).")

        # BUG-007: Audit Logging
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            project_id=project_id,
            old_value=existing if not status else status,
            new_value=result,
            metadata={"reason": reason},
            session=session,
        )

        # 4. Trigger Master Recalculation (H3)
        return await self.recalculate_master_budget(project_id, session=session)
