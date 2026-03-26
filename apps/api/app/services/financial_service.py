import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from bson import ObjectId, Decimal128
from fastapi import HTTPException, status

def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal128):
        return Decimal(str(value.to_decimal()))
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")

logger = logging.getLogger(__name__)

class FinancialService:
    def __init__(self, db):
        self.db = db

    async def recalculate_project_code_financials(self, project_id: str, category_id: str, session=None):
        budget = await self.db.project_category_budgets.find_one({
            "project_id": project_id,
            "category_id": category_id
        }, session=session)

        if not budget:
            return None

        approved_budget = _to_decimal(budget.get("original_budget", "0"))

        committed_pipeline = [
            {"$match": {
                "project_id": project_id,
                "category_id": category_id,
                "status": {"$nin": ["Cancelled"]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
        ]
        committed_result = await self.db.work_orders.aggregate(committed_pipeline, session=session).to_list(length=1)
        committed_value = _to_decimal(committed_result[0].get("total") if committed_result else None)

        certified_pipeline = [
            {"$match": {
                "project_id": project_id,
                "category_id": category_id,
                "status": "Closed"
            }},
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
        ]
        certified_result = await self.db.payment_certificates.aggregate(certified_pipeline, session=session).to_list(length=1)
        certified_value = _to_decimal(certified_result[0].get("total") if certified_result else None)

        balance_remaining = approved_budget - committed_value
        over_commit = committed_value > approved_budget

        serializable_doc = {
            "project_id": project_id,
            "category_id": category_id,
            "original_budget": Decimal128(str(approved_budget)),
            "committed_value": Decimal128(str(committed_value)),
            "certified_value": Decimal128(str(certified_value)),
            "balance_budget_remaining": Decimal128(str(balance_remaining)),
            "over_commit_flag": over_commit,
            "last_recalculated": datetime.now(timezone.utc)
        }

        await self.db.financial_state.update_one(
            {"project_id": project_id, "category_id": category_id},
            {"$set": serializable_doc},
            upsert=True,
            session=session
        )

        return serializable_doc

    async def recalculate_all_project_financials(self, project_id: str, session=None):
        budgets = await self.db.project_category_budgets.find({"project_id": project_id}).to_list(length=1000)
        
        totals = {
            "total_budget": Decimal("0"),
            "total_committed": Decimal("0"),
            "total_certified": Decimal("0"),
            "categories_recalculated": 0
        }

        for b in budgets:
            cat_id = b.get("category_id")
            if not cat_id: continue
            
            res = await self.recalculate_project_code_financials(project_id, cat_id, session=session)
            if res:
                totals["total_budget"] += _to_decimal(res["original_budget"])
                totals["total_committed"] += _to_decimal(res["committed_value"])
                totals["total_certified"] += _to_decimal(res["certified_value"])
                totals["categories_recalculated"] += 1

        return {
            "project_id": project_id,
            **totals,
            "total_remaining": totals["total_budget"] - totals["total_committed"]
        }

    @staticmethod
    def round_half_up(value: Decimal, precision: int = 2) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        quantize_str = "0." + "0" * (precision - 1) + "1" if precision > 0 else "1"
        return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
