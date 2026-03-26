from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from decimal import Decimal, ROUND_HALF_UP
from bson import Decimal128, ObjectId

from app.core.export_service import ExportService
from app.repositories.financial_repo import BudgetRepository, WorkOrderRepository, FinancialStateRepository
from app.repositories.site_repo import WorkerLogRepository
from app.core.time import now

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
    Sovereign Reporting Orchestrator (Unified Engine).
    Fixed CR-10: Merged Core engine and Service facade into one authoritative class.
    """
    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker
        self.budget_repo = BudgetRepository(db)
        self.wo_repo = WorkOrderRepository(db)
        self.fin_state_repo = FinancialStateRepository(db)
        self.worker_log_repo = WorkerLogRepository(db)

    async def get_report(self, user: dict, project_id: str, report_type: ReportType, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        """Entry point for generating project reports."""
        await self.permission_checker.check_project_access(user, project_id)
        
        if not ExportService.validate_report_type(report_type):
            raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")

        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Logic moved from core/reporting_service.py
        if report_type == "project_summary":
            return await self._project_summary_report(project_id)
        elif report_type == "work_order_tracker":
            return await self._work_order_tracker_report(project_id, start_dt, end_dt)
        elif report_type == "payment_certificate_tracker":
            return await self._payment_certificate_tracker_report(project_id, start_dt, end_dt)
        elif report_type == "petty_cash_tracker":
            return await self._petty_cash_tracker_report(project_id, start_dt, end_dt)
        elif report_type == "csa_report":
            return await self._csa_report(project_id, start_dt, end_dt)
        
        # Progress reports fallback
        window = "weekly"
        if "15_days" in report_type: window = "15days"
        elif "monthly" in report_type: window = "monthly"
        return await self._progress_report(project_id, window, start_dt, end_dt)

    async def get_dashboard_stats(self, user: dict, project_id: str) -> Dict[str, Any]:
        """High-level statistics for project dashboard."""
        await self.permission_checker.check_project_access(user, project_id)

        # 1. Project Overview & Financial Totals
        total_phases = await self.budget_repo.count({"project_id": project_id})
        active_items_count = await self.wo_repo.count({
            "project_id": project_id, 
            "status": {"$in": ["Pending", "Draft"]}
        })
        
        budgets = await self.budget_repo.list({"project_id": project_id}, limit=500)
        financials = await self.fin_state_repo.list({"project_id": project_id}, limit=500)
        fin_map = {str(f.get("category_id")): f for f in financials}
        
        master_budget = Decimal("0.0")
        total_committed = Decimal("0.0")
        
        for b in budgets:
            cid = str(b.get("category_id"))
            master_budget += self._to_decimal(b.get("original_budget"))
            total_committed += self._to_decimal(fin_map.get(cid, {}).get("committed_value"))

        # 2. Project Log & Compliance
        resolved_tasks = await self.wo_repo.count({
            "project_id": project_id, 
            "status": {"$in": ["Closed", "Completed"]}
        })
        
        ts_now = now()
        yesterday = ts_now.replace(hour=0, minute=0, second=0, microsecond=0)
        dpr_recent = await self.worker_log_repo.count({
            "project_id": project_id,
            "created_at": {"$gte": yesterday}
        })
        
        total_log_tasks = active_items_count + resolved_tasks
        compliance_rate = Decimal("100.0")
        if total_log_tasks > 0:
            compliance_rate = (Decimal(str(resolved_tasks)) / Decimal(str(total_log_tasks))) * Decimal("100.0")
        
        if dpr_recent == 0 and compliance_rate > Decimal("10"):
            compliance_rate -= Decimal("5.0")

        return {
            "project_id": project_id,
            "overview": {
                "total_phases": total_phases,
                "active_items": active_items_count,
                "master_budget": str(master_budget),
                "total_committed": str(total_committed)
            },
            "task_log": {
                "open_tasks": active_items_count,
                "resolved_tasks": resolved_tasks,
                "compliance_rate": float(round(compliance_rate, 1))
            }
        }

    # --- INTERNAL REPORT GENERATION LOGIC ---

    async def _project_summary_report(self, project_id: str) -> Dict[str, Any]:
        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$lookup": {"from": "code_master", "localField": "category_id", "foreignField": "code", "as": "category"}},
            {
                "$project": {
                    "original_budget": 1,
                    "committed_value": 1,
                    "certified_value": 1,
                    "balance_budget_remaining": 1,
                    "category_name": {"$arrayElemAt": ["$category.category_name", 0]},
                    "category_code": {"$arrayElemAt": ["$category.code", 0]}
                }
            },
            {"$sort": {"category_code": 1}},
        ]

        financial_data = await self.db.financial_state.aggregate(pipeline).to_list(None)
        rows = []
        totals = {"budget": Decimal("0"), "committed": Decimal("0"), "certified": Decimal("0"), "remaining": Decimal("0")}

        for item in financial_data:
            budget = self._to_decimal(item.get("original_budget"))
            committed = self._to_decimal(item.get("committed_value"))
            certified = self._to_decimal(item.get("certified_value"))
            remaining = self._to_decimal(item.get("balance_budget_remaining"))

            rows.append([item.get("category_code"), item.get("category_name"), str(budget), str(committed), str(certified), str(remaining), "TBD"])
            totals["budget"] += budget
            totals["committed"] += committed
            totals["certified"] += certified
            totals["remaining"] += remaining

        return {
            "title": "Project Financial Summary",
            "project_id": project_id,
            "columns": ["CODE", "Description", "Budget", "Committed", "Certified", "Remaining", "Deadline"],
            "rows": rows,
            "totals": {k: str(v) for k, v in totals.items()},
            "metadata": {"generated_at": now().isoformat(), "row_count": len(rows)}
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
            rows.append([wo.get("category_code", ""), wo.get("wo_ref", ""), wo.get("vendor_name", ""), str(amount), str(ret_amount), wo.get("created_at").strftime("%Y-%m-%d"), "TBD"])
            total_amount += amount
        return {"title": "Work Order Tracker", "rows": rows, "totals": {"total_amount": str(total_amount)}}

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
            rows.append([pc.get("category_code", ""), pc.get("pc_ref", ""), pc.get("vendor_name", ""), str(amount), pc.get("created_at").strftime("%Y-%m-%d"), str(amount) if pc.get("status") == "Closed" else "0.00", "Pending"])
            total_certified += amount
        return {"title": "Payment Certificate Tracker", "rows": rows, "totals": {"total_certified": str(total_certified)}}

    async def _petty_cash_tracker_report(self, project_id: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        match_stage = {"project_id": project_id, "work_order_id": None}
        if start_date or end_date: match_stage["created_at"] = {k: v for k, v in [("$gte", start_date), ("$lte", end_date)] if v}
        pcs = await self.db.payment_certificates.find(match_stage).sort("created_at", 1).to_list(None)
        rows = []
        total_value = Decimal("0")
        for pc in pcs:
            amount = self._to_decimal(pc.get("grand_total"))
            rows.append([pc.get("created_at").strftime("%Y-%m-%d"), pc.get("pc_ref", ""), str(amount), "Refill Request"])
            total_value += amount
        return {"title": "Petty Cash & OVH Tracker", "rows": rows, "totals": {"total_funds_received": str(total_value)}}

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
        if isinstance(value, Decimal128): return value.to_decimal()
        try: return Decimal(str(value))
        except: return Decimal("0")
