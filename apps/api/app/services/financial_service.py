import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from bson import ObjectId, Decimal128
from fastapi import HTTPException, status

from app.repositories.financial_repo import BudgetRepository, WorkOrderRepository, PCRepository, FinancialStateRepository, CodeMasterRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.vendor_repo import VendorRepository

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
        self.budget_repo = BudgetRepository(db)
        self.wo_repo = WorkOrderRepository(db)
        self.pc_repo = PCRepository(db)
        self.financial_state_repo = FinancialStateRepository(db)
        self.code_master_repo = CodeMasterRepository(db)
        self.project_repo = ProjectRepository(db)
        self.vendor_repo = VendorRepository(db)

    async def recalculate_project_code_financials(self, project_id: str, category_id: str, session=None):
        budget = await self.budget_repo.get_by_project_and_category(project_id, category_id, session=session)

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
        committed_result = await self.wo_repo.aggregate(committed_pipeline, session=session)
        committed_value = _to_decimal(committed_result[0].get("total") if committed_result else None)

        certified_pipeline = [
            {"$match": {
                "project_id": project_id,
                "category_id": category_id,
                "status": "Closed"
            }},
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
        ]
        certified_result = await self.pc_repo.aggregate(certified_pipeline, session=session)
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

        await self.financial_state_repo.update_one(
            {"project_id": project_id, "category_id": category_id},
            {"$set": serializable_doc},
            session=session
        )

        return serializable_doc

    async def recalculate_all_project_financials(self, project_id: str, session=None):
        budgets = await self.budget_repo.list({"project_id": project_id}, limit=1000)
        
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

    async def recalculate_master_budget(self, project_id: str, session=None):
        """
        Recalculate and store the master budget for a project (aggregated across all categories).
        Called whenever a Work Order or Payment Certificate changes to maintain financial integrity.
        """
        result = await self.recalculate_all_project_financials(project_id, session=session)

        # Store master budget document (no category_id, just project totals)
        master_doc = {
            "project_id": project_id,
            "category_id": None,  # Master budget covers all categories
            "total_budget": Decimal128(str(result["total_budget"])),
            "total_committed": Decimal128(str(result["total_committed"])),
            "total_certified": Decimal128(str(result["total_certified"])),
            "total_remaining": Decimal128(str(result["total_remaining"])),
            "categories_recalculated": result["categories_recalculated"],
            "last_recalculated": datetime.now(timezone.utc)
        }

        await self.financial_state_repo.update_one(
            {"project_id": project_id, "category_id": None},
            {"$set": master_doc},
            session=session,
            upsert=True
        )

        return result

    async def compute_cash_in_hand(self, project_id: str, category_id: str, session=None) -> Decimal:
        """
        Return the current cash-in-hand for a fund-transfer category.
        """
        allocation = await self.db.fund_allocations.find_one(
            {"project_id": project_id, "category_id": category_id},
            {"cash_in_hand": 1},
            session=session
        )

        if not allocation:
            return Decimal("0")

        return _to_decimal(allocation.get("cash_in_hand", 0))

    async def check_threshold_breach(self, project_id: str, category_id: str, session=None) -> bool:
        """
        Check if cash-in-hand has breached the threshold for a category.
        """
        cash_in_hand = await self.compute_cash_in_hand(project_id, category_id, session)
        project = await self.project_repo.get_by_id(project_id, session=session)
        if not project:
            return False

        category = await self.code_master_repo.get_by_id(category_id, session=session)
        if not category:
            # Try by code slug
            category = await self.code_master_repo.find_one({"code": category_id}, session=session)
        
        budget_type = category.get("budget_type") if category else None

        if budget_type == "fund_transfer":
            category_name = category.get("category_name", "").lower() if category else ""
            category_code = category.get("code", "").lower() if category else ""
            if "ovh" in category_name or "overhead" in category_name or "ovh" in category_code:
                threshold = _to_decimal(project.get("threshold_ovh", "0"))
            else:
                threshold = _to_decimal(project.get("threshold_petty", "0"))
            return cash_in_hand <= threshold
        
        return False

    async def compute_15_day_countdown(self, project_id: str, category_id: str, session=None) -> int:
        """
        Calculates days since fund_allocations.last_pc_closed_date.
        """
        allocation = await self.db.fund_allocations.find_one({
            "project_id": project_id,
            "category_id": category_id
        }, session=session)

        if not allocation or not allocation.get("last_pc_closed_date"):
            return 0

        last_date = allocation["last_pc_closed_date"]
        if isinstance(last_date, str):
            last_date = datetime.fromisoformat(last_date)

        delta = datetime.now(timezone.utc) - last_date
        return delta.days

    async def validate_financial_document(self, doc_type: str, data: dict, project_id: str, session=None):
        """
        Strict pre-save financial validator.
        """
        errors = []

        # 1. Project & Category Validation
        project = await self.project_repo.get_by_id(project_id, session=session)
        if not project:
            errors.append({"field": "project_id", "message": f"Project {project_id} does not exist"})

        category_id = data.get("category_id")
        if category_id:
            category = await self.code_master_repo.get_by_id(category_id, session=session)
            if not category:
                # Try by code slug
                category = await self.code_master_repo.find_one({"code": category_id}, session=session)
            
            if not category:
                errors.append({"field": "category_id", "message": f"Category {category_id} does not exist in code master"})
            else:
                # Use category_id as string for comparison if needed
                cat_id_to_check = str(category.get("_id") or category_id)
                budget = await self.budget_repo.get_by_project_and_category(project_id, cat_id_to_check, session=session)
                if not budget:
                    # Try with original category_id
                    budget = await self.budget_repo.get_by_project_and_category(project_id, category_id, session=session)
                
                if not budget:
                    errors.append({"field": "category_id", "message": f"Category {category_id} is not assigned to this project"})
        else:
            errors.append({"field": "category_id", "message": "category_id is required."})

        # 2. Vendor Validation
        vendor_id = data.get("vendor_id")
        if vendor_id and doc_type == "WORK_ORDER":
            vendor = await self.vendor_repo.get_by_id(vendor_id, session=session)
            if not vendor:
                errors.append({"field": "vendor_id", "message": f"Vendor {vendor_id} does not exist"})

        # 3. Line Item Validation
        line_items = data.get("line_items", [])
        if not line_items:
            errors.append({"field": "line_items", "message": "Document must contain at least one line item."})

        calculated_subtotal = Decimal("0")
        for idx, item in enumerate(line_items):
            qty = Decimal(str(item.get("qty", "0")))
            rate = Decimal(str(item.get("rate", "0")))
            expected_row_total = self.round_half_up(qty * rate)
            payload_row_total = Decimal(str(item.get("total", "0")))

            if self.round_half_up(payload_row_total) != expected_row_total:
                errors.append({
                    "field": f"line_items[{idx}].total",
                    "message": f"Row {idx+1}: Line item total mismatch. Expected {expected_row_total}, got {payload_row_total}"
                })

            calculated_subtotal += expected_row_total

        # 4. GST + Retention Validation
        discount = Decimal(str(data.get("discount", "0")))
        total_before_tax = calculated_subtotal - discount

        cgst_rate = _to_decimal(project.get("project_cgst_percentage", "9.0")) if project else Decimal("9.0")
        sgst_rate = _to_decimal(project.get("project_sgst_percentage", "9.0")) if project else Decimal("9.0")

        expected_cgst = self.round_half_up(total_before_tax * cgst_rate / Decimal("100"))
        expected_sgst = self.round_half_up(total_before_tax * sgst_rate / Decimal("100"))
        expected_grand_total = self.round_half_up(total_before_tax + expected_cgst + expected_sgst)

        payload_grand_total = Decimal(str(data.get("grand_total", expected_grand_total)))
        if self.round_half_up(payload_grand_total) != expected_grand_total:
            errors.append({
                "field": "grand_total",
                "message": f"Grand total mismatch. Expected {expected_grand_total}, got {payload_grand_total}"
            })

        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})

        return True

    @staticmethod
    def round_half_up(value: Decimal, precision: int = 2) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        quantize_str = "0." + "0" * (precision - 1) + "1" if precision > 0 else "1"
        return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
