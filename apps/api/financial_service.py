"""
FinancialRecalculationService

Recalculates derived financial state for project budgets.
Aggregates committed and certified values from petty_cash and worker_logs,
then updates the financial_state collection for dashboard consumption.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
from bson import ObjectId, Decimal128


def _to_decimal(value) -> Decimal:
    """
    Safely convert any MongoDB numeric type (Decimal128, int, float, str) to Python Decimal.
    Returns Decimal("0") for None or unconvertible values.
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal128):
        return Decimal(str(value.to_decimal()))
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")

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
        - balance_budget_remaining: original_budget - committed_value
        - over_commit_flag: True if committed_value > original_budget
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

        approved_budget = _to_decimal(budget.get("original_budget", "0"))

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
        committed_value = _to_decimal(committed_result[0].get("total") if committed_result else None)

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
        certified_value = _to_decimal(certified_result[0].get("total") if certified_result else None)

        # Calculate derived values
        balance_remaining = approved_budget - committed_value
        over_commit = committed_value > approved_budget

        # Upsert financial state
        financial_doc = {
            "project_id": project_id,
            "category_id": category_id,
            "original_budget": approved_budget,
            "committed_value": committed_value,
            "certified_value": certified_value,
            "balance_budget_remaining": balance_remaining,
            "over_commit_flag": over_commit,
            "last_recalculated": datetime.now(timezone.utc)
        }

        # Convert Decimal values to Decimal128 for MongoDB storage
        serializable_doc = {
            "project_id": project_id,
            "category_id": category_id,
            "original_budget": Decimal128(str(financial_doc["original_budget"])),
            "committed_value": Decimal128(str(financial_doc["committed_value"])),
            "certified_value": Decimal128(str(financial_doc["certified_value"])),
            "balance_budget_remaining": Decimal128(str(financial_doc["balance_budget_remaining"])),
            "over_commit_flag": financial_doc["over_commit_flag"],
            "last_recalculated": financial_doc["last_recalculated"]
        }

        await self.db.financial_state.update_one(
            {"project_id": project_id, "category_id": category_id},
            {"$set": serializable_doc},
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

    # Hard ceiling: a single project is not expected to exceed this many budget
    # codes.  If this limit is ever reached the recalculation is still correct
    # for the first MAX_BUDGET_CODES rows, but the warning signals that the
    # collection should be reviewed before the next scale boundary.
    _MAX_BUDGET_CODES = 1000

    async def recalculate_all_project_financials(self, project_id, session=None):
        """
        Recalculate financial state for ALL categories in a project.

        Iterates over all budgets for the project and recalculates each one.
        Returns a summary of the project-level totals.

        Safety: caps the cursor at _MAX_BUDGET_CODES rows to prevent application-
        level memory exhaustion as project histories scale.  A warning is emitted
        if the cap is reached so operations can investigate the data volume.
        """
        budgets = await self.db.project_category_budgets.find(
            {"project_id": project_id}
        ).to_list(length=self._MAX_BUDGET_CODES)

        if not budgets:
            logger.warning(f"No budgets found for project={project_id}")
            return {"project_id": project_id, "categories_recalculated": 0}

        if len(budgets) == self._MAX_BUDGET_CODES:
            logger.warning(
                f"recalculate_all_project_financials hit the {self._MAX_BUDGET_CODES}-row "
                f"ceiling for project={project_id}. Some budget codes may have been "
                f"skipped. Investigate project_category_budgets collection volume."
            )

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
                total_budget += result.get("original_budget", Decimal("0"))
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
        Sums original_budget and remaining_budget directly (not derived).
        """
        from bson import Decimal128

        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$group": {
                "_id": None,
                "total_original": {"$sum": "$original_budget"},
                "total_remaining": {"$sum": {"$ifNull": ["$remaining_budget", 0.0]}},
            }},
        ]

        result = await self.db.project_category_budgets.aggregate(
            pipeline, session=session
        ).to_list(length=1)

         # Handle empty aggregation results (no budgets initialized yet)
        if not result:
            master_original = Decimal("0.0")
            master_remaining = Decimal("0.0")
        else:
            row = result[0]
            master_original = _to_decimal(row.get("total_original", 0))
            master_remaining = _to_decimal(row.get("total_remaining", 0))

        # Build robust project query - try ObjectId first, then string lookup
        project_query = {"_id": ObjectId(project_id)} if isinstance(project_id, str) and len(project_id) == 24 else {"_id": project_id}

        # Also support finding by project_id string field if _id lookup fails (backwards compatibility)
        project = await self.db.projects.find_one(project_query, session=session)
        if not project and isinstance(project_id, str):
            project_query = {"project_id": project_id}
            project = await self.db.projects.find_one(project_query, session=session)

        # Update and verify the result
        if not project:
            raise Exception(
                f"Failed to update master budget: project {project_id} not found. "
                f"Possible data integrity issue."
            )

        update_result = await self.db.projects.update_one(
            project_query,
            {"$set": {
                "master_original_budget": Decimal128(str(master_original)),
                "master_remaining_budget": Decimal128(str(master_remaining)),
            }},
            session=session
        )

        if update_result.matched_count == 0:
            raise Exception(
                f"Failed to update master budget: project {project_id} not found after verification. "
                f"Possible data integrity issue."
            )

        if update_result.modified_count == 0:
            logger.warning(
                f"recalculate_master_budget: project found but not modified "
                f"(values unchanged?): project_id={project_id}"
            )

        logger.info(
            f"Master budget recalculated for project={project_id}: "
            f"original={master_original}, remaining={master_remaining}, "
            f"matched={update_result.matched_count}, modified={update_result.modified_count}"
        )

        return {
            "master_original_budget": master_original,
            "master_remaining_budget": master_remaining,
        }

    async def compute_cash_in_hand(self, project_id, category_id, session=None):
        """
        Return the current cash-in-hand for a fund-transfer category.

        The value is read directly from fund_allocations.cash_in_hand, which is
        maintained as an atomic running counter via $inc on every DEBIT and CREDIT
        recorded in cash_transactions.  This is O(1) against a unique-indexed
        document — no aggregation over the transactions collection is needed.

        Falls back to Decimal("0") if no allocation document exists.
        """
        from bson import Decimal128 as _D128

        allocation = await self.db.fund_allocations.find_one(
            {"project_id": project_id, "category_id": category_id},
            {"cash_in_hand": 1},   # projection — only the balance field
            session=session
        )

        if not allocation:
            logger.warning(
                f"compute_cash_in_hand: no fund_allocation found for "
                f"project={project_id}, category={category_id}. Returning 0."
            )
            return Decimal("0")

        raw = allocation.get("cash_in_hand", _D128("0"))
        cash_in_hand = (
            Decimal(str(raw.to_decimal())) if isinstance(raw, _D128)
            else Decimal(str(raw))
        )

        logger.info(
            f"compute_cash_in_hand: project={project_id}, category={category_id}, "
            f"balance={cash_in_hand} (read from fund_allocations)"
        )
        return cash_in_hand

    async def check_threshold_breach(self, project_id, category_id, session=None):
        """
        Check if cash-in-hand has breached the threshold for a category.

        Returns True if cash_in_hand <= threshold.
        Category-aware: determines if Petty Cash or OVH based on budget_type,
        then uses the appropriate threshold field.
        """
        cash_in_hand = await self.compute_cash_in_hand(project_id, category_id, session)

        # Get project thresholds
        # Ensure project_id is handled correctly for _id lookup
        pq = {"_id": ObjectId(project_id)} if isinstance(project_id, str) and len(project_id) == 24 else {"_id": project_id}
        project = await self.db.projects.find_one(pq, session=session)
        if not project:
            # Try string-based lookup
            project = await self.db.projects.find_one({"project_id": project_id}, session=session)
        if not project:
            return False

        # Determine category type (Petty Cash vs OVH) by checking budget_type
        # Support both ObjectId strings and code slugs
        cat_query = {"_id": ObjectId(category_id)} if isinstance(category_id, str) and len(category_id) == 24 else {"_id": category_id}
        category = await self.db.code_master.find_one(cat_query, session=session)
        if not category:
            category = await self.db.code_master.find_one({"code": category_id}, session=session)

        budget_type = category.get("budget_type") if category else None

        # Use appropriate threshold based on category type
        if budget_type == "fund_transfer":
            # Check if this is OVH category (typically has "ovh" or "overhead" in name/code)
            category_name = category.get("category_name", "").lower() if category else ""
            category_code = category.get("code", "").lower() if category else ""
            if "ovh" in category_name or "overhead" in category_name or "ovh" in category_code:
                threshold = Decimal(str(project.get("threshold_ovh", "0")))
            else:
                # Petty Cash
                threshold = Decimal(str(project.get("threshold_petty", "0")))
        else:
            # Non fund-transfer categories don't have thresholds
            return False

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
            return 0  # Never refilled

        last_date = allocation["last_pc_closed_date"]
        if isinstance(last_date, str):
            last_date = datetime.fromisoformat(last_date)

        delta = datetime.now(timezone.utc) - last_date
        return delta.days

    async def validate_financial_document(self, doc_type: str, data: dict, project_id: str, session=None):
        """
        Strict pre-save financial validator.

        Enforces:
        - Project and category existence (6.4.3)
        - Line-item parity (6.4.1)
        - GST/Retention correctness (6.4.2)
        - Budget floors (6.4.5)

        Returns detailed field-specific errors if validation fails.
        """
        errors = []

        # === 6.4.3: Project & Category Validation ===
        # Verify project exists
        project = await self.db.projects.find_one(
            {"_id": ObjectId(project_id)} if len(project_id) == 24 else {"project_id": project_id},
            session=session
        )
        if not project:
            errors.append({"field": "project_id", "message": f"Project {project_id} does not exist"})

        # Verify category exists in code_master
        category_id = data.get("category_id")
        if category_id:
            category = await self.db.code_master.find_one(
                {"_id": ObjectId(category_id)} if len(category_id) == 24 else {"code": category_id},
                session=session
            )
            if not category:
                errors.append({"field": "category_id", "message": f"Category {category_id} does not exist in code master"})
            else:
                # Verify category is valid for project (exists in project_category_budgets)
                budget = await self.db.project_category_budgets.find_one(
                    {"project_id": project_id, "category_id": category_id},
                    session=session
                )
                if not budget:
                    errors.append({"field": "category_id", "message": f"Category {category_id} is not assigned to this project"})
        else:
            errors.append({"field": "category_id", "message": "category_id is required."})

        # Verify vendor exists (for Work Orders)
        vendor_id = data.get("vendor_id")
        if vendor_id and doc_type == "WORK_ORDER":
            vendor = await self.db.vendors.find_one(
                {"_id": ObjectId(vendor_id)} if len(vendor_id) == 24 else {"_id": vendor_id},
                session=session
            )
            if not vendor:
                errors.append({"field": "vendor_id", "message": f"Vendor {vendor_id} does not exist"})

        # === 6.4.1: Line Item Validation ===
        line_items = data.get("line_items", [])
        if not line_items:
            errors.append({"field": "line_items", "message": "Document must contain at least one line item."})

        calculated_subtotal = Decimal("0")
        for idx, item in enumerate(line_items):
            qty = Decimal(str(item.get("qty", "0")))
            rate = Decimal(str(item.get("rate", "0")))
            expected_row_total = self.round_half_up(qty * rate)
            payload_row_total = Decimal(str(item.get("total", "0")))

            # Validate individual line item total
            if self.round_half_up(payload_row_total) != expected_row_total:
                errors.append({
                    "field": f"line_items[{idx}].total",
                    "message": f"Row {idx+1}: Line item total mismatch. Expected {expected_row_total} (qty={qty} x rate={rate}), got {payload_row_total}"
                })

            calculated_subtotal += expected_row_total

        # Validate subtotal parity
        payload_subtotal = Decimal(str(data.get("subtotal", calculated_subtotal)))
        if self.round_half_up(payload_subtotal) != self.round_half_up(calculated_subtotal):
            errors.append({
                "field": "subtotal",
                "message": f"Subtotal parity error. Line items sum to {calculated_subtotal}, but payload says {payload_subtotal}"
            })

        # === 6.4.2: GST + Retention Validation ===
        discount = Decimal(str(data.get("discount", "0")))
        total_before_tax = calculated_subtotal - discount

        # Get project tax rates for validation
        cgst_rate = Decimal(str(project.get("project_cgst_percentage", "9.0"))) if project else Decimal("9.0")
        sgst_rate = Decimal(str(project.get("project_sgst_percentage", "9.0"))) if project else Decimal("9.0")

        expected_cgst = self.round_half_up(total_before_tax * cgst_rate / Decimal("100"))
        expected_sgst = self.round_half_up(total_before_tax * sgst_rate / Decimal("100"))
        expected_grand_total = self.round_half_up(total_before_tax + expected_cgst + expected_sgst)

        # Validate GST amounts
        payload_cgst = Decimal(str(data.get("cgst", expected_cgst)))
        payload_sgst = Decimal(str(data.get("sgst", expected_sgst)))
        payload_grand_total = Decimal(str(data.get("grand_total", expected_grand_total)))

        if self.round_half_up(payload_cgst) != expected_cgst:
            errors.append({"field": "cgst", "message": f"CGST mismatch. Expected {expected_cgst} ({cgst_rate}% of {total_before_tax}), got {payload_cgst}"})

        if self.round_half_up(payload_sgst) != expected_sgst:
            errors.append({"field": "sgst", "message": f"SGST mismatch. Expected {expected_sgst} ({sgst_rate}% of {total_before_tax}), got {payload_sgst}"})

        if self.round_half_up(payload_grand_total) != expected_grand_total:
            errors.append({
                "field": "grand_total",
                "message": f"Grand total mismatch. Expected {expected_grand_total} (subtotal {calculated_subtotal} - discount {discount} + CGST {expected_cgst} + SGST {expected_sgst}), got {payload_grand_total}"
            })

        # === RETENTION MATH (6.4.2 extended) ===
        retention_percent = Decimal(str(data.get("retention_percent", "0")))
        expected_retention_amount = self.round_half_up(expected_grand_total * retention_percent / Decimal("100"))
        expected_total_payable = expected_grand_total - expected_retention_amount

        payload_retention_amount = Decimal(str(data.get("retention_amount", expected_retention_amount)))
        payload_total_payable = Decimal(str(data.get("total_payable", expected_total_payable)))

        if self.round_half_up(payload_retention_amount) != expected_retention_amount:
            errors.append({
                "field": "retention_amount",
                "message": f"Retention amount mismatch. Expected {expected_retention_amount} ({retention_percent}% of {expected_grand_total}), got {payload_retention_amount}"
            })

        if self.round_half_up(payload_total_payable) != expected_total_payable:
            errors.append({
                "field": "total_payable",
                "message": f"Total payable mismatch. Expected {expected_total_payable} (grand_total {expected_grand_total} - retention {expected_retention_amount}), got {payload_total_payable}"
            })

        # Validate actual_payable if present
        actual_payable = data.get("actual_payable")
        if actual_payable is not None:
            payload_actual_payable = Decimal(str(actual_payable))
            if self.round_half_up(payload_actual_payable) != expected_total_payable:
                errors.append({
                    "field": "actual_payable",
                    "message": f"Actual payable mismatch. Expected {expected_total_payable}, got {payload_actual_payable}"
                })

        # === 6.4.5: Budget Floor Check ===
        if doc_type == "BUDGET_UPDATE":
            new_amount = Decimal(str(data.get("original_budget", "0")))
            existing_committed = Decimal(str(data.get("committed_amount", "0")))
            if new_amount < existing_committed:
                errors.append({
                    "field": "original_budget",
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
