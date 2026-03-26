from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

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
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def generate_report(
        self,
        project_id: str,
        report_type: ReportType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
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

    async def _project_summary_report(self, project_id: str) -> Dict[str, Any]:
        pipeline = [
            {"$match": {"project_id": project_id}},
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
            budget = float(self._to_decimal(item.get("original_budget")))
            committed = float(self._to_decimal(item.get("committed_value")))
            certified = float(self._to_decimal(item.get("certified_value")))
            remaining = float(self._to_decimal(item.get("balance_budget_remaining")))

            rows.append([item.get("category_code"), item.get("category_name"), budget, committed, certified, remaining, "TBD"])
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
            "metadata": {"generated_at": datetime.now(timezone.utc).isoformat(), "row_count": len(rows)}
        }

    async def _work_order_tracker_report(self, project_id: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        match_stage = {"project_id": project_id}
        if start_date or end_date:
            match_stage["created_at"] = {k: v for k, v in [("$gte", start_date), ("$lte", end_date)] if v}

        pipeline = [
            {"$match": match_stage},
            {"$lookup": {"from": "code_master", "localField": "category_id", "foreignField": "_id", "as": "category"}},
            {"$lookup": {"from": "vendors", "localField": "vendor_id", "foreignField": "_id", "as": "vendor"}},
            {
                "$project": {
                    "wo_ref": 1,
                    "category_code": {"$arrayElemAt": ["$category.code", 0]},
                    "vendor_name": {"$arrayElemAt": ["$vendor.name", 0]},
                    "grand_total": 1,
                    "retention_amount": 1,
                    "created_at": 1,
                }
            },
            {"$sort": {"created_at": -1}},
        ]
        wo_data = await self.db.work_orders.aggregate(pipeline).to_list(None)
        rows = []
        total_amount = Decimal("0")
        for wo in wo_data:
            amount = self._to_decimal(wo.get("grand_total"))
            ret_amount = self._to_decimal(wo.get("retention_amount"))
            rows.append([wo.get("category_code", ""), wo.get("wo_ref", ""), wo.get("vendor_name", ""), float(amount), float(ret_amount), wo.get("created_at").strftime("%Y-%m-%d"), "TBD"])
            total_amount += amount
        return {"title": "Work Order Tracker", "rows": rows, "totals": {"total_amount": float(total_amount)}}

    async def _payment_certificate_tracker_report(self, project_id: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        match_stage = {"project_id": project_id}
        if start_date or end_date: match_stage["created_at"] = {k: v for k, v in [("$gte", start_date), ("$lte", end_date)] if v}
        pipeline = [
            {"$match": match_stage},
            {"$lookup": {"from": "code_master", "localField": "category_id", "foreignField": "_id", "as": "category"}},
            {"$lookup": {"from": "vendors", "localField": "vendor_id", "foreignField": "_id", "as": "vendor"}},
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
            amount = self._to_decimal(pc.get("grand_total"))
            rows.append([pc.get("category_code", ""), pc.get("pc_ref", ""), pc.get("vendor_name", ""), float(amount), pc.get("created_at").strftime("%Y-%m-%d"), float(amount) if pc.get("status") == "Closed" else 0.0, "Pending"])
            total_certified += amount
        return {"title": "Payment Certificate Tracker", "rows": rows, "totals": {"total_certified": float(total_certified)}}

    async def _petty_cash_tracker_report(self, project_id: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        match_stage = {"project_id": project_id, "work_order_id": None}
        if start_date or end_date: match_stage["created_at"] = {k: v for k, v in [("$gte", start_date), ("$lte", end_date)] if v}
        pcs = await self.db.payment_certificates.find(match_stage).sort("created_at", 1).to_list(None)
        rows = []
        total_value = Decimal("0")
        for pc in pcs:
            amount = self._to_decimal(pc.get("grand_total"))
            rows.append([pc.get("created_at").strftime("%Y-%m-%d"), pc.get("pc_ref", ""), float(amount), "Refill Request"])
            total_value += amount
        return {"title": "Petty Cash & OVH Tracker", "rows": rows, "totals": {"total_funds_received": float(total_value)}}

    async def _csa_report(self, project_id: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$lookup": {"from": "code_master", "localField": "category_id", "foreignField": "_id", "as": "category"}},
            {"$match": {"category.code": "CSA"}},
            {"$project": {"wo_ref": 1, "category_code": {"$arrayElemAt": ["$category.code", 0]}, "description": "$notes", "created_at": 1}}
        ]
        items = await self.db.work_orders.aggregate(pipeline).to_list(None)
        rows = [[p.get("category_code", "CSA"), p.get("wo_ref"), p.get("description") or "Asset", 1, p.get("created_at").strftime("%Y-%m-%d")] for p in items]
        return {"title": "CSA Report", "rows": rows, "totals": {"total_count": len(rows)}}

    async def _progress_report(self, project_id: str, window: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        # Implementation simplified for parity
        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$lookup": {"from": "code_master", "localField": "category_id", "foreignField": "_id", "as": "category"}},
            {"$lookup": {"from": "vendors", "localField": "vendor_id", "foreignField": "_id", "as": "vendor"}},
            {"$project": {"wo_ref": 1, "category_code": {"$arrayElemAt": ["$category.code", 0]}, "vendor_name": {"$arrayElemAt": ["$vendor.name", 0]}, "status": 1}}
        ]
        wos = await self.db.work_orders.aggregate(pipeline).to_list(None)
        rows = [[w.get("category_code"), w.get("wo_ref"), w.get("vendor_name"), 1.0 if w.get("status") == "Closed" else 0.5, w.get("status")] for w in wos]
        return {"title": f"{window.title()} Progress Report", "rows": rows}

    def _to_decimal(self, value: Any) -> Decimal:
        if isinstance(value, Decimal): return value
        if hasattr(value, "to_decimal"): return value.to_decimal()
        try: return Decimal(str(value))
        except: return Decimal("0")
