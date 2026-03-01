"""
FinancialRecalculationService

Recalculates derived financial state for project budgets.
Aggregates committed and certified values from petty_cash and worker_logs,
then updates the financial_state collection for dashboard consumption.
"""
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class FinancialRecalculationService:
    def __init__(self, db):
        self.db = db

    async def recalculate_project_code_financials(self, project_id, code_id):
        """
        Recalculate financial state for a specific project + code combination.

        Aggregates:
        - committed_value: sum of approved petty_cash entries for this project
        - certified_value: sum of petty_cash entries with status 'approved'
        - balance_budget_remaining: approved_budget_amount - committed_value
        - over_commit_flag: True if committed_value > approved_budget_amount
        """
        # Get the budget for this project+code
        budget = await self.db.project_budgets.find_one({
            "project_id": project_id,
            "code_id": code_id
        })

        if not budget:
            logger.warning(
                f"No budget found for project={project_id}, code={code_id}")
            return None

        approved_budget = budget.get("approved_budget_amount", 0)

        # Aggregate petty cash committed (all non-rejected entries)
        committed_pipeline = [
            {"$match": {
                "project_id": project_id,
                "status": {"$nin": ["rejected"]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        committed_result = await self.db.petty_cash.aggregate(
            committed_pipeline).to_list(length=1)
        committed_value = committed_result[0]["total"] if committed_result else 0

        # Aggregate certified (only approved entries)
        certified_pipeline = [
            {"$match": {
                "project_id": project_id,
                "status": "approved"
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        certified_result = await self.db.petty_cash.aggregate(
            certified_pipeline).to_list(length=1)
        certified_value = certified_result[0]["total"] if certified_result else 0

        # Calculate derived values
        balance_remaining = approved_budget - committed_value
        over_commit = committed_value > approved_budget

        # Upsert financial state
        financial_doc = {
            "project_id": project_id,
            "code_id": code_id,
            "approved_budget_amount": approved_budget,
            "committed_value": committed_value,
            "certified_value": certified_value,
            "balance_budget_remaining": balance_remaining,
            "over_commit_flag": over_commit,
            "last_recalculated": datetime.utcnow()
        }

        await self.db.financial_state.update_one(
            {"project_id": project_id, "code_id": code_id},
            {"$set": financial_doc},
            upsert=True
        )

        logger.info(
            f"Recalculated financials for project={project_id}, "
            f"code={code_id}: budget={approved_budget}, "
            f"committed={committed_value}, certified={certified_value}, "
            f"remaining={balance_remaining}, over_commit={over_commit}"
        )

        return financial_doc

    async def recalculate_all_project_financials(self, project_id):
        """
        Recalculate financial state for ALL codes in a project.

        Iterates over all budgets for the project and recalculates each one.
        Returns a summary of the project-level totals.
        """
        budgets = await self.db.project_budgets.find(
            {"project_id": project_id}
        ).to_list(length=None)

        if not budgets:
            logger.warning(f"No budgets found for project={project_id}")
            return {"project_id": project_id, "codes_recalculated": 0}

        total_budget = 0
        total_committed = 0
        total_certified = 0
        codes_recalculated = 0

        for budget in budgets:
            code_id = budget.get("code_id")
            if not code_id:
                continue

            result = await self.recalculate_project_code_financials(
                project_id, code_id)

            if result:
                total_budget += result.get("approved_budget_amount", 0)
                total_committed += result.get("committed_value", 0)
                total_certified += result.get("certified_value", 0)
                codes_recalculated += 1

        logger.info(
            f"Recalculated all financials for project={project_id}: "
            f"{codes_recalculated} codes, total_budget={total_budget}, "
            f"total_committed={total_committed}"
        )

        return {
            "project_id": project_id,
            "codes_recalculated": codes_recalculated,
            "total_budget": total_budget,
            "total_committed": total_committed,
            "total_certified": total_certified,
            "total_remaining": total_budget - total_committed,
        }
