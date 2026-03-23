"""
Reporting Service - MongoDB aggregation pipelines for financial reports
Generates authoritative report data per spec (no frontend aggregation)
"""

from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection


ReportType = Literal[
    "project_summary",
    "work_order_tracker",
    "payment_certificate_tracker",
    "petty_cash_tracker",
    "csa_report",
    "weekly_progress",
    "15_days_progress",
    "monthly_progress"
]


class ReportingService:
    """
    MongoDB-native reporting engine using aggregation pipelines.
    All calculations are backend authority - no frontend aggregation.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def generate_report(
        self,
        project_id: str,
        report_type: ReportType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate report data using MongoDB aggregation.
        
        Args:
            project_id: Project ID
            report_type: Type of report to generate
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary with {title, rows, totals, metadata}
        """
        
        if report_type == "project_summary":
            return await self._project_summary_report(project_id)
        elif report_type == "work_order_tracker":
            return await self._work_order_tracker_report(project_id, start_date, end_date)
        elif report_type == "payment_certificate_tracker":
            return await self._payment_certificate_tracker_report(project_id, start_date, end_date)
        elif report_type == "petty_cash_tracker":
            return await self._petty_cash_tracker_report(project_id, start_date, end_date)
        elif report_type == "csa_report":
            return await self._csa_report(project_id, start_date, end_date)
        elif report_type == "weekly_progress":
            return await self._progress_report(project_id, "weekly", start_date, end_date)
        elif report_type == "15_days_progress":
            return await self._progress_report(project_id, "15days", start_date, end_date)
        elif report_type == "monthly_progress":
            return await self._progress_report(project_id, "monthly", start_date, end_date)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    async def materialize_report(
        self,
        project_id: str,
        report_type: ReportType,
    ) -> str:
        """
        Materialize a report into a dedicated collection using $merge.
        Useful for heavy queries that don't change often.
        """
        collection_name = f"materialized_{report_type}"
        
        # This is a generic implementation for project_summary as an example
        if report_type == "project_summary":
            pipeline = [
                {"$match": {"project_id": project_id}},
                {
                    "$group": {
                        "_id": "$category_id",
                        "project_id": {"$first": "$project_id"},
                        "original_budget": {"$first": "$original_budget"},
                        "committed_amount": {"$sum": "$committed_amount"},
                        "remaining_budget": {"$first": "$remaining_budget"},
                        "updated_at": {"$max": datetime.now(timezone.utc)} # Mock
                    }
                },
                {
                    "$merge": {
                        "into": collection_name,
                        "on": "_id",
                        "whenMatched": "replace",
                        "whenNotMatched": "insert"
                    }
                }
            ]
            await self.db.project_category_budgets.aggregate(pipeline).to_list(None)
            return collection_name
        
        return "not_implemented"

    async def _project_summary_report(self, project_id: str) -> Dict[str, Any]:
        """
        Project-level financial summary: budget vs committed vs certified per category.
        Aligned with template: CODE | Description | Budget | Committed | Certified | Remaining | Deadline
        """
        # We pull from financial_state as it's the authoritative aggregate
        pipeline = [
            {"$match": {"project_id": project_id}},
            # Add a flag if category_id looks like a 24-char hex ObjectId
            {
                "$addFields": {
                    "curr_cid": "$category_id",
                    "is_oid_candidate": {
                        "$regexMatch": {
                            "input": {"$toString": "$category_id"},
                            "regex": "^[0-9a-fA-F]{24}$"
                        }
                    }
                }
            },
            # Universal lookup across ID, code, and code_short
            {
                "$lookup": {
                    "from": "code_master",
                    "let": {"cid": "$curr_cid", "is_oid": "$is_oid_candidate"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$or": [
                                        {"$eq": ["$_id", "$$cid"]},
                                        {"$eq": ["$code", "$$cid"]},
                                        {"$eq": ["$code_short", "$$cid"]},
                                        {
                                            "$and": [
                                                {"$eq": ["$$is_oid", True]},
                                                {"$eq": ["$_id", {"$toObjectId": "$$cid"}]}
                                            ]
                                        }
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "matched_categories"
                }
            },
            {
                "$addFields": {
                    "category": {"$arrayElemAt": ["$matched_categories", 0]}
                }
            },
            {
                "$project": {
                    "original_budget": 1,
                    "committed_value": 1,
                    "certified_value": 1,
                    "balance_budget_remaining": 1,
                    "category_name": {"$ifNull": ["$category.category_name", {"$ifNull": ["$category.code_description", "$category_id"]}]},
                    "category_code": {"$ifNull": ["$category.code", {"$ifNull": ["$category.code_short", "N/A"]}]}
                }
            },
            {"$sort": {"category_code": 1}},
        ]

        financial_data = await self.db.financial_state.aggregate(pipeline).to_list(None)

        rows = []
        totals = {"budget": 0.0, "committed": 0.0, "certified": 0.0, "remaining": 0.0}

        for item in financial_data:
            # Aligned with FE: [CODE, Description, Budget, Committed, Certified, Remaining, Deadline]
            
            category_name = item.get("category_name")
            category_code = item.get("category_code")

            # Defensive float conversion
            try:
                budget = float(item.get("original_budget") or 0)
                committed = float(item.get("committed_value") or 0)
                certified = float(item.get("certified_value") or 0)
                remaining = float(item.get("balance_budget_remaining") or 0)
            except (ValueError, TypeError):
                budget = committed = certified = remaining = 0.0

            rows.append([
                category_code,
                category_name,
                budget,
                committed,
                certified,
                remaining,
                "TBD"  # Deadline placeholder
            ])

            totals["budget"] += budget
            totals["committed"] += committed
            totals["certified"] += certified
            totals["remaining"] += remaining

        return {
            "title": "Project Financial Summary",
            "project_id": project_id,
            "columns": ["CODE", "Description", "Budget", "Committed", "Certified", "Remaining", "Deadline"],
            "rows": rows,
            "totals": totals,
            "metadata": {
                "project_id": project_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "row_count": len(rows),
            }
        }

    async def _work_order_tracker_report(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Work Order tracking: reference, category, vendor, amount, status, date.
        Template: CODE | WO Refn | Vendor | WO Value | Retention Value | Start Date | End Date
        """
        match_stage = {"project_id": project_id}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            match_stage["created_at"] = date_filter

        pipeline = [
            {"$match": match_stage},
            {
                "$lookup": {
                    "from": "categories",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {
                "$lookup": {
                    "from": "vendors",
                    "localField": "vendor_id",
                    "foreignField": "_id",
                    "as": "vendor",
                }
            },
            {
                "$project": {
                    "wo_ref": 1,
                    "category_code": {"$arrayElemAt": ["$category.code", 0]},
                    "vendor_name": {"$arrayElemAt": ["$vendor.name", 0]},
                    "grand_total": 1,
                    "retention_amount": 1,
                    "status": 1,
                    "created_at": 1,
                }
            },
            {"$sort": {"created_at": -1}},
        ]

        wo_data = await self.db.work_orders.aggregate(pipeline).to_list(None)

        rows = []
        total_amount = Decimal("0")

        for wo in wo_data:
            amount = self._to_decimal(wo.get("grand_total", 0))
            ret_amount = self._to_decimal(wo.get("retention_amount", 0))
            created_at = wo.get("created_at", datetime.now(timezone.utc))
            
            rows.append([
                wo.get("category_code", ""),
                wo.get("wo_ref", ""),
                wo.get("vendor_name", ""),
                float(amount),
                float(ret_amount),
                created_at.strftime("%Y-%m-%d"), # Start
                "TBD", # End Date
            ])
            total_amount += amount

        return {
            "title": "Work Order Tracker",
            "rows": rows,
            "totals": {"total_amount": float(total_amount)},
            "metadata": {
                "project_id": project_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "row_count": len(rows),
            }
        }

    async def _payment_certificate_tracker_report(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Payment Certificate tracking: reference, WO ref, vendor, amount, status.
        Template: CODE | PC Refn | Vendor | PC Value | PC Date | Payment Value | Payment Date
        """
        match_stage = {"project_id": project_id}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            match_stage["created_at"] = date_filter

        pipeline = [
            {"$match": match_stage},
            {
                "$lookup": {
                    "from": "categories",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {
                "$lookup": {
                    "from": "vendors",
                    "localField": "vendor_id",
                    "foreignField": "_id",
                    "as": "vendor",
                }
            },
            {
                "$project": {
                    "pc_ref": 1,
                    "category_code": {"$arrayElemAt": ["$category.code", 0]},
                    "vendor_name": {"$arrayElemAt": ["$vendor.name", 0]},
                    "grand_total": 1,
                    "status": 1,
                    "created_at": 1,
                }
            },
            {"$sort": {"created_at": -1}},
        ]

        pc_data = await self.db.payment_certificates.aggregate(pipeline).to_list(None)

        rows = []
        total_certified = Decimal("0")

        for pc in pc_data:
            amount = self._to_decimal(pc.get("grand_total", 0))
            created_at = pc.get("created_at", datetime.now(timezone.utc))
            
            rows.append([
                pc.get("category_code", ""),
                pc.get("pc_ref", ""),
                pc.get("vendor_name", ""),
                float(amount),
                created_at.strftime("%Y-%m-%d"), # PC Date
                float(amount) if pc.get("status") == "Closed" else 0.0, # Payment Value
                created_at.strftime("%Y-%m-%d") if pc.get("status") == "Closed" else "Pending", # Payment Date
            ])
            total_certified += amount

        return {
            "title": "Payment Certificate Tracker",
            "rows": rows,
            "totals": {"total_certified": float(total_certified)},
            "metadata": {
                "project_id": project_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "row_count": len(rows),
            }
        }

    async def _petty_cash_tracker_report(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Petty Cash and OVH tracking report (funding focus).
        Template: Date | PC Refn | PC Value | Bill / Invoice
        """
        # We fetch Payment Certificates that were fund requests (Petty/OVH)
        match_stage = {
            "project_id": project_id,
            "work_order_id": None, # Fund requests have no WO
        }
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            match_stage["created_at"] = date_filter

        pcs = await self.db.payment_certificates.find(match_stage).sort("created_at", 1).to_list(None)

        rows = []
        total_value = Decimal("0")

        for pc in pcs:
            amount = self._to_decimal(pc.get("grand_total", 0))
            created_at = pc.get("created_at", datetime.now(timezone.utc))
            
            rows.append([
                created_at.strftime("%Y-%m-%d"),
                pc.get("pc_ref", ""),
                float(amount),
                "Refill / Fund Request", # Bill/Invoice placeholder
            ])
            total_value += amount

        return {
            "title": "Petty Cash & OVH Tracker",
            "rows": rows,
            "totals": {"total_funds_received": float(total_value)},
            "metadata": {
                "project_id": project_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "row_count": len(rows),
            }
        }

    async def _csa_report(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Category-Specific Activity report (CSA).
        Template: CODE | WO Refn | Description | Qty | Received Date
        """
        # Group by category but for CSA specifically (Client Supplied Assets)
        # In this system, CSA is often tracked via specialized DPRs or specific WOs
        pipeline = [
            {"$match": {"project_id": project_id}},
            {
                "$lookup": {
                    "from": "categories",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {"$match": {"category.code": "CSA"}}, # Filter for CSA only
            {
                "$project": {
                    "wo_ref": 1,
                    "category_code": {"$arrayElemAt": ["$category.code", 0]},
                    "description": "$notes", # Or line items
                    "created_at": 1,
                }
            }
        ]

        csa_items = await self.db.work_orders.aggregate(pipeline).to_list(None)

        rows = []
        for item in csa_items:
            rows.append([
                item.get("category_code", "CSA"),
                item.get("wo_ref", ""),
                item.get("description") or "Asset Provision",
                1, # Qty
                item.get("created_at", datetime.now(timezone.utc)).strftime("%Y-%m-%d"),
            ])

        return {
            "title": "Category-Specific Activity Report",
            "rows": rows,
            "totals": {"total_count": len(rows)},
            "metadata": {
                "project_id": project_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "row_count": len(rows),
            }
        }

    async def _progress_report(
        self,
        project_id: str,
        window: Literal["weekly", "15days", "monthly"],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Progress reports for different time windows: weekly, 15-day, monthly.
        Template: CODE | WO Refn | Vendor | % Completed | Comments
        """
        # Calculate date range
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        if not start_date:
            if window == "weekly":
                start_date = end_date - timedelta(days=7)
            elif window == "15days":
                start_date = end_date - timedelta(days=15)
            else:  # monthly
                start_date = end_date - timedelta(days=30)

        # We'll list activity by category/WO active in this period
        pipeline = [
            {"$match": {"project_id": project_id}},
            {
                "$lookup": {
                    "from": "categories",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {
                "$lookup": {
                    "from": "vendors",
                    "localField": "vendor_id",
                    "foreignField": "_id",
                    "as": "vendor",
                }
            },
            {
                "$project": {
                    "wo_ref": 1,
                    "category_code": {"$arrayElemAt": ["$category.code", 0]},
                    "vendor_name": {"$arrayElemAt": ["$vendor.name", 0]},
                    "status": 1,
                }
            }
        ]

        wos = await self.db.work_orders.aggregate(pipeline).to_list(None)
        
        rows = []
        for wo in wos:
            # In a real system, we'd check DPRs for % completion in this window
            # For now, we simulate or use status
            progress = 1.0 if wo.get("status") in ["Completed", "Closed"] else 0.5
            
            rows.append([
                wo.get("category_code", ""),
                wo.get("wo_ref", ""),
                wo.get("vendor_name", ""),
                progress,
                f"Status: {wo.get('status')}", # Comments
            ])

        return {
            "title": f"{window.title()} Progress Report",
            "rows": rows,
            "metadata": {
                "project_id": project_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "row_count": len(rows),
            }
        }

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """Convert value to Decimal safely"""
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except:
            return Decimal("0")
