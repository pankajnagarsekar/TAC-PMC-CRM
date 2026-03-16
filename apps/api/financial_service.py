"""
FinancialRecalculationService

Recalculates derived financial state for project budgets.
Aggregates committed and certified values from petty_cash and worker_logs,
then updates the financial_state collection for dashboard consumption.
"""
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
from bson import ObjectId


logger = logging.getLogger(__name__)


class FinancialRecalculationService:
    def __init__(self, db):
        self.db = db

    async def recalculate_project_code_financials(self, project_id, category_id, session=None):
        """
        Recalculate financial state for a specific project + category combination.

        Aggregates:
        - committed_value: sum of approved Work Orders for this category
        - certified_value: sum of certified Payment Certificates for this category
        - balance_budget_remaining: approved_budget_amount - committed_value
        - over_commit_flag: True if committed_value > approved_budget_amount
        """
        # Get the budget for this project+category
        budget = await self.db.project_category_budgets.find_one({
            "project_id": project_id,
            "category_id": category_id
        }, session=session)

        if not budget:
            logger.warning(
                f"No budget found for project={project_id}, category={category_id}")
            return None

        approved_budget = Decimal(str(budget.get("approved_budget_amount", "0")))

        # Aggregate Work Order committed (all non-Cancelled entries)
        committed_pipeline = [
            {"$match": {
                "project_id": project_id,
                "category_id": category_id,
                "status": {"$nin": ["Cancelled"]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
        ]
        committed_result = await self.db.work_orders.aggregate(
            committed_pipeline, session=session).to_list(length=1)
        committed_value = Decimal(str(committed_result[0]["total"])) if committed_result else Decimal("0")

        # Aggregate Payment Certificates certified (only Closed entries)
        certified_pipeline = [
            {"$match": {
                "project_id": project_id,
                "category_id": category_id,
                "status": "Closed"
            }},
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
        ]
        certified_result = await self.db.payment_certificates.aggregate(
            certified_pipeline, session=session).to_list(length=1)
        certified_value = Decimal(str(certified_result[0]["total"])) if certified_result else Decimal("0")

        # Calculate derived values
        balance_remaining = approved_budget - committed_value
        over_commit = committed_value > approved_budget

        # Upsert financial state
        financial_doc = {
            "project_id": project_id,
            "category_id": category_id,
            "approved_budget_amount": approved_budget,
            "committed_value": committed_value,
            "certified_value": certified_value,
            "balance_budget_remaining": balance_remaining,
            "over_commit_flag": over_commit,
            "last_recalculated": datetime.utcnow()
        }

        await self.db.financial_state.update_one(
            {"project_id": project_id, "category_id": category_id},
            {"$set": financial_doc},
            upsert=True,
            session=session
        )

        logger.info(
            f"Recalculated financials for project={project_id}, "
            f"category={category_id}: budget={approved_budget}, "
            f"committed={committed_value}, certified={certified_value}, "
            f"remaining={balance_remaining}, over_commit={over_commit}"
        )

        return financial_doc

    async def recalculate_all_project_financials(self, project_id, session=None):
        """
        Recalculate financial state for ALL categories in a project.

        Iterates over all budgets for the project and recalculates each one.
        Returns a summary of the project-level totals.
        """
        budgets = await self.db.project_category_budgets.find(
            {"project_id": project_id}
        ).to_list(length=None)

        if not budgets:
            logger.warning(f"No budgets found for project={project_id}")
            return {"project_id": project_id, "categories_recalculated": 0}

        total_budget = Decimal("0")
        total_committed = Decimal("0")
        total_certified = Decimal("0")
        categories_recalculated = 0

        for budget in budgets:
            category_id = budget.get("category_id")
            if not category_id:
                continue

            result = await self.recalculate_project_code_financials(
                project_id, category_id, session=session)

            if result:
                total_budget += result.get("approved_budget_amount", Decimal("0"))
                total_committed += result.get("committed_value", Decimal("0"))
                total_certified += result.get("certified_value", Decimal("0"))
                categories_recalculated += 1

        logger.info(
            f"Recalculated all financials for project={project_id}: "
            f"{categories_recalculated} categories, total_budget={total_budget}, "
            f"total_committed={total_committed}"
        )

        return {
            "project_id": project_id,
            "categories_recalculated": categories_recalculated,
            "total_budget": total_budget,
            "total_committed": total_committed,
            "total_certified": total_certified,
            "total_remaining": total_budget - total_committed,
        }

    async def recalculate_master_budget(self, project_id, session=None):
        """
        Sum all project_category_budgets → update project master totals.
        Called after any budget initialization or modification.
        """
        from bson import Decimal128

        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$group": {
                "_id": None,
                "total_original": {"$sum": "$approved_budget_amount"},
                "total_committed": {"$sum": {"$ifNull": ["$committed_amount", Decimal128("0.0")]}},
            }},
        ]

        result = await self.db.project_category_budgets.aggregate(
            pipeline, session=session
        ).to_list(length=1)

        if result:
            master_original = Decimal(str(result[0]["total_original"]))
            master_committed = Decimal(str(result[0]["total_committed"]))
            master_remaining = master_original - master_committed
        else:
            master_original = Decimal("0")
            master_remaining = Decimal("0")

        await self.db.projects.update_one(
            {"_id": project_id} if not isinstance(project_id, str)
            else {"$or": [{"_id": ObjectId(project_id) if len(project_id) == 24 else project_id}, {"project_id": project_id}]},
            {"$set": {
                "master_original_budget": Decimal128(str(master_original)),
                "master_remaining_budget": Decimal128(str(master_remaining)),
            }},
            session=session
        )

        logger.info(
            f"Master budget recalculated for project={project_id}: "
            f"original={master_original}, remaining={master_remaining}"
        )

        return {
            "master_original_budget": master_original,
            "master_remaining_budget": master_remaining,
        }

    async def compute_cash_in_hand(self, project_id, category_id, session=None):
        """
        Compute cash-in-hand for a fund-transfer category (Petty Cash / OVH).
        cash_in_hand = SUM(CREDIT) - SUM(DEBIT) from cash_transactions.
        """
        pipeline = [
            {"$match": {
                "project_id": project_id,
                "category_id": category_id,
            }},
            {"$group": {
                "_id": "$type",
                "total": {"$sum": "$amount"},
            }},
        ]

        results = await self.db.cash_transactions.aggregate(
            pipeline, session=session
        ).to_list(length=10)

        credits = Decimal("0")
        debits = Decimal("0")
        for r in results:
            if r["_id"] == "CREDIT":
                credits = Decimal(str(r["total"]))
            elif r["_id"] == "DEBIT":
                debits = Decimal(str(r["total"]))

        cash_in_hand = credits - debits

        logger.info(
            f"Cash-in-hand for project={project_id}, category={category_id}: "
            f"credits={credits}, debits={debits}, balance={cash_in_hand}"
        )

        return cash_in_hand

    async def check_threshold_breach(self, project_id, category_id):
        """
        Check if cash-in-hand has breached the threshold for a category.
        Returns True if cash_in_hand <= threshold.
        """
        cash_in_hand = await self.compute_cash_in_hand(project_id, category_id)

        # Get project thresholds
        project = await self.db.projects.find_one({"_id": project_id})
        if not project:
            # Try string-based lookup
            project = await self.db.projects.find_one({"project_id": project_id})

        if not project:
            return False

        # Determine threshold based on category type
        threshold = Decimal(str(project.get("threshold_petty", "0")))

        return cash_in_hand <= threshold

    async def compute_15_day_countdown(self, project_id, category_id, session=None):
        """
        Calculates days since fund_allocations.last_pc_closed_date.
        Used for the 15-day refill cycle monitoring.
        """
        allocation = await self.db.fund_allocations.find_one({
            "project_id": project_id,
            "category_id": category_id
        }, session=session)

        if not allocation or not allocation.get("last_pc_closed_date"):
            return 0 # Never refilled

        last_date = allocation["last_pc_closed_date"]
        if isinstance(last_date, str):
            last_date = datetime.fromisoformat(last_date)
        
        delta = datetime.utcnow() - last_date
        return delta.days

    async def validate_financial_document(self, doc_type: str, data: dict, project_id: str, session=None):
        """
        Strict pre-save financial validator.
        Enforces line-item parity, GST/Retention correctness, and budget floors.
        Returns detailed field-specific errors if validation fails.
        """
        errors = []
        line_items = data.get("line_items", [])
        
        if not line_items:
            errors.append({"field": "line_items", "message": "Document must contain at least one line item."})
        else:
            calculated_subtotal = Decimal("0")
            for idx, item in enumerate(line_items):
                qty = Decimal(str(item.get("qty", "0")))
                rate = Decimal(str(item.get("rate", "0")))
                row_total = self.round_half_up(qty * rate)
                calculated_subtotal += row_total

            # 6.4.1: validate SUM(line_items) equals submitted subtotal
            payload_subtotal = Decimal(str(data.get("subtotal", calculated_subtotal)))
            if self.round_half_up(payload_subtotal) != self.round_half_up(calculated_subtotal):
                 errors.append({
                     "field": "subtotal", 
                     "message": f"Subtotal parity error. Line items sum to {calculated_subtotal}, but payload says {payload_subtotal}"
                 })

            # 6.4.2: validate GST/Retention
            discount = Decimal(str(data.get("discount", "0")))
            cgst = Decimal(str(data.get("cgst", "0")))
            sgst = Decimal(str(data.get("sgst", "0")))
            
            expected_grand_total = self.round_half_up(calculated_subtotal - discount + cgst + sgst)
            payload_grand_total = Decimal(str(data.get("grand_total", expected_grand_total)))
            
            if self.round_half_up(payload_grand_total) != expected_grand_total:
                 errors.append({
                     "field": "grand_total", 
                     "message": f"Grand total mismatch. Expected {expected_grand_total}, but payload says {payload_grand_total}"
                 })

        # 6.4.3: Category validity
        category_id = data.get("category_id")
        if not category_id:
             errors.append({"field": "category_id", "message": "category_id is required."})

        # 6.4.5: Budget floor check
        if doc_type == "BUDGET_UPDATE":
             new_amount = Decimal(str(data.get("approved_budget_amount", "0")))
             existing_committed = Decimal(str(data.get("committed_amount", "0")))
             if new_amount < existing_committed:
                  errors.append({
                      "field": "approved_budget_amount", 
                      "message": f"Budget floor violation. New amount {new_amount} is less than already committed {existing_committed}"
                  })

        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})

        logger.info(f"Financial validation passed for {doc_type} in project {project_id}")
        return True

    @staticmethod
    def round_half_up(value: Decimal, precision: int = 2) -> Decimal:
        """
        Explicit Round-Half-Up monetary rounding helper.
        Compliant with Tech Arch §3.1.
        """
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        # Create the decimal format string like "0.01" or "0.001" based on precision
        quantize_str = "0." + "0" * (precision - 1) + "1" if precision > 0 else "1"
        return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
