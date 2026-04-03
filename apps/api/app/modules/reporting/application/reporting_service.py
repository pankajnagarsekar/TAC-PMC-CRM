import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Literal, Optional

from app.core.export_service import ExportService
from app.core.time import now
from app.modules.contracting.infrastructure.repository import WorkOrderRepository
from app.modules.financial.infrastructure.repository import FinancialStateRepository

# Repositories from other contexts
from app.modules.project.infrastructure.repository import BudgetRepository
from app.modules.shared.domain.exceptions import ValidationError
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.site_operations.infrastructure.repository import WorkerLogRepository

logger = logging.getLogger(__name__)

ReportType = Literal[
    "project_summary",
    "work_order_tracker",
    "payment_certificate_tracker",
    "petty_cash_tracker",
    "csa_report",
    "weekly_progress",
    "15_days_progress",
    "monthly_progress",
]


class ReportingService:
    """
    Sovereign Reporting Orchestrator (Unified Engine).
    Merged Core engine and Service facade into one authoritative class.
    """

    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker
        self.budget_repo = BudgetRepository(db)
        self.wo_repo = WorkOrderRepository(db)
        self.fin_state_repo = FinancialStateRepository(db)
        self.worker_log_repo = WorkerLogRepository(db)

    async def get_report(
        self,
        user: dict,
        project_id: str,
        report_type: ReportType,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Dict[str, Any]:
        """Entry point for generating project reports."""
        await self.permission_checker.check_project_access(user, project_id)

        if not ExportService.validate_report_type(report_type):
            raise ValidationError(f"Invalid report type: {report_type}")

        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        if report_type == "project_summary":
            return await self._project_summary_report(project_id)
        elif report_type == "work_order_tracker":
            return await self._work_order_tracker_report(project_id, start_dt, end_dt)
        elif report_type == "payment_certificate_tracker":
            return await self._payment_certificate_tracker_report(
                project_id, start_dt, end_dt
            )
        elif report_type == "petty_cash_tracker":
            return await self._petty_cash_tracker_report(project_id, start_dt, end_dt)
        elif report_type == "scheduler_gantt":
            return await self._scheduler_gantt_report(project_id)
 
        window = "weekly"
        if "15_days" in report_type:
            window = "15days"
        elif "monthly" in report_type:
            window = "monthly"
        return await self._progress_report(project_id, window, start_dt, end_dt)
 
    async def _scheduler_gantt_report(self, project_id: str) -> Dict[str, Any]:
        """Prepares hierarchical Gantt data with pixel offsets for PDF rendering."""
        from app.modules.project.application.scheduler_service import SchedulerService
        from datetime import timedelta
        import math
 
        sched_service = SchedulerService(self.db)
        # Pull latest schedule
        # Note: organisation_id is required by repo but we might need to bypass for internal report
        # For now we'll assume we can get it from projects collection
        project = await self.db.projects.find_one({"project_id": project_id})
        org_id = project.get("organisation_id") if project else None
        
        schedule = await sched_service.load_schedule(project_id, org_id)
        tasks_raw = schedule.get("tasks", [])
        
        if not tasks_raw:
            return {"tasks": [], "months": [], "quarters": [], "day_width_px": 5}
 
        # 1. Timeline bounds
        fmt = "%Y-%m-%d"
        starts = []
        finishes = []
        for t in tasks_raw:
            if t.get("scheduled_start"):
                starts.append(datetime.strptime(t["scheduled_start"][:10], fmt))
            if t.get("scheduled_finish"):
                finishes.append(datetime.strptime(t["scheduled_finish"][:10], fmt))
        
        project_start = min(starts) if starts else datetime.now()
        # Round project start to beginning of month for cleaner timeline
        timeline_start = project_start.replace(day=1)
        project_finish = max(finishes) if finishes else project_start + timedelta(days=30)
 
        day_width = 4 # pixels per day
        
        # 2. task processing
        processed_tasks = []
        task_map = {t["task_id"]: t for t in tasks_raw}
        
        def get_depth(t_id, depth=0):
            task = task_map.get(t_id)
            if not task or not task.get("parent_id"):
                return depth
            return get_depth(task["parent_id"], depth + 1)
 
        for t in tasks_raw:
            t_start = datetime.strptime(t["scheduled_start"][:10], fmt) if t.get("scheduled_start") else timeline_start
            t_finish = datetime.strptime(t["scheduled_finish"][:10], fmt) if t.get("scheduled_finish") else t_start
            
            offset_days = (t_start - timeline_start).days
            duration_days = (t_finish - t_start).days + 1
            
            # Predecessors CSV
            preds = t.get("predecessors", [])
            pred_ids = [p.get("task_id") if isinstance(p, dict) else str(p) for p in preds]
            # Convert internal task IDs to row numbers (1-indexed matching PDF)
            pred_rows = []
            for pid in pred_ids:
                for idx, r_t in enumerate(tasks_raw):
                    if r_t["task_id"] == pid:
                        pred_rows.append(str(idx + 1))
                        break
 
            pt = t.copy()
            pt["depth"] = get_depth(t["task_id"])
            pt["start_offset_px"] = offset_days * day_width
            pt["width_px"] = max(duration_days * day_width, 1)
            pt["predecessors_csv"] = ", ".join(pred_rows)
            pt["cost_formatted"] = ExportService.format_currency(t.get("wo_value") or 0)
            pt["is_summary"] = bool(t.get("is_summary"))
            processed_tasks.append(pt)
 
        # 3. Timeline Markers (Months & Quarters)
        months = []
        quarters = []
        curr = timeline_start
        total_days = (project_finish - timeline_start).days + 60 # buffer
        
        last_q = -1
        while (curr - timeline_start).days < total_days:
            # Month
            m_label = curr.strftime("%b '%y")
            m_offset = (curr - timeline_start).days * day_width
            
            # Determine days in this month
            import calendar
            days_in_m = calendar.monthrange(curr.year, curr.month)[1]
            m_width = days_in_m * day_width
            
            months.append({"label": m_label, "offset": m_offset, "width": m_width})
            
            # Quarter
            q_num = (curr.month - 1) // 3 + 1
            if q_num != last_q:
                q_label = f"Qtr {q_num}, {curr.year}"
                quarters.append({"label": q_label, "offset": m_offset, "width": 0}) # Width updated later
                if len(quarters) > 1:
                    quarters[-2]["width"] = m_offset - quarters[-2]["offset"]
                last_q = q_num
            
            # Move to next month
            if curr.month == 12:
                curr = curr.replace(year=curr.year + 1, month=1)
            else:
                curr = curr.replace(month=curr.month + 1)
        
        # Last quarter width
        if quarters:
            quarters[-1]["width"] = (curr - timeline_start).days * day_width - quarters[-1]["offset"]
 
        return {
            "project_name": project.get("name") if project else "Project",
            "now": now().strftime("%d-%m-%y"),
            "baseline_name": "R0 (Current)",
            "tasks": processed_tasks,
            "months": months,
            "quarters": quarters,
            "day_width_px": day_width,
            "total_timeline_width": (curr - timeline_start).days * day_width
        }

    async def get_dashboard_stats(self, user: dict, project_id: str) -> Dict[str, Any]:
        """High-level statistics for project dashboard."""
        await self.permission_checker.check_project_access(user, project_id)

        from bson import ObjectId
        resilient_id = {"$in": [project_id, ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id]}

        total_phases = await self.budget_repo.count({"project_id": resilient_id})
        active_items_count = await self.wo_repo.count(
            {"project_id": resilient_id, "status": {"$in": ["Pending", "Draft"]}}
        )

        budgets = await self.budget_repo.list({"project_id": resilient_id}, limit=500)
        financials = await self.fin_state_repo.list(
            {"project_id": resilient_id}, limit=500
        )
        fin_map = {}
        for f in financials:
            cid = f.get("category_id") or f.get("code_id")
            if cid:
                fin_map[str(cid)] = f
        master_budget = Decimal("0.0")
        total_committed = Decimal("0.0")

        for b in budgets:
            category_id = b.get("category_id")
            if not category_id:
                continue

            cid = str(category_id)
            master_budget += FinancialEngine.to_decimal(b.get("original_budget"))
            total_committed += FinancialEngine.to_decimal(
                fin_map.get(cid, {}).get("committed_value")
            )

        resolved_tasks = await self.wo_repo.count(
            {"project_id": resilient_id, "status": {"$in": ["Closed", "Completed"]}}
        )

        ts_now = now()
        yesterday = ts_now.replace(hour=0, minute=0, second=0, microsecond=0)
        dpr_recent = await self.worker_log_repo.count(
            {"project_id": resilient_id, "created_at": {"$gte": yesterday}}
        )

        total_log_tasks = active_items_count + resolved_tasks
        compliance_rate = Decimal("100.0")
        if total_log_tasks > 0:
            compliance_rate = (
                Decimal(str(resolved_tasks)) / Decimal(str(total_log_tasks))
            ) * Decimal("100.0")

        if dpr_recent == 0 and compliance_rate > Decimal("10"):
            compliance_rate -= Decimal("5.0")

        return {
            "project_id": project_id,
            "overview": {
                "total_phases": total_phases,
                "active_items": active_items_count,
                "master_budget": str(master_budget),
                "total_committed": str(total_committed),
            },
            "task_log": {
                "open_tasks": active_items_count,
                "resolved_tasks": resolved_tasks,
                "compliance_rate": float(round(compliance_rate, 1)),
            },
        }

    async def get_projects_overview(self, user: dict) -> Dict[str, Any]:
        """Provides a bird's-eye view of all projects for the admin dashboard."""
        await self.permission_checker.check_admin_role(user)

        projects = await self.db.projects.find(
            {"organisation_id": user["organisation_id"], "is_deleted": {"$ne": True}}
        ).to_list(100)

        results = []
        ts_now = now()
        today_start = ts_now.replace(hour=0, minute=0, second=0, microsecond=0)

        for proj in projects:
            p_id = proj["project_id"]

            from bson import ObjectId
            p_id_resilient = {"$in": [p_id, ObjectId(p_id) if ObjectId.is_valid(p_id) else p_id]}

            # 1. Financial Stats
            master_state = await self.fin_state_repo.find_one(
                {"project_id": p_id_resilient, "code_id": None}
            )
            # 2. DPR & Worker Stats
            dpr_total = await self.worker_log_repo.count({"project_id": p_id_resilient})
            dpr_today = await self.worker_log_repo.count(
                {"project_id": p_id_resilient, "created_at": {"$gte": today_start}}
            )
            dpr_pending = await self.worker_log_repo.count(
                {"project_id": p_id_resilient, "status": "Pending"}
            )

            worker_stats = await self.db.worker_logs.aggregate(
                [
                    {
                        "$match": {
                            "project_id": p_id_resilient,
                            "created_at": {"$gte": today_start},
                        }
                    },
                    {"$group": {"_id": None, "total": {"$sum": "$worker_count"}}},
                ]
            ).to_list(1)
            recent_workers = worker_stats[0]["total"] if worker_stats else 0

            # 3. Cash & Categories breakdown
            allocations = await self.db.fund_allocations.find(
                {"project_id": p_id_resilient}
            ).to_list(100)
            categories_data = []
            petty_cash_total = Decimal("0.0")

            for alloc in allocations:
                cat_id = alloc.get("category_id")
                category = await self.db.code_master.find_one({"_id": ObjectId(cat_id) if ObjectId.is_valid(cat_id) else cat_id})
                cat_name = category.get("category_name") if category else f"Category {cat_id}"
                
                cash_in_hand = FinancialEngine.to_decimal(alloc.get("cash_in_hand", 0))
                petty_cash_total += cash_in_hand
                categories_data.append(
                    {
                        "code_id": str(cat_id),
                        "code_name": cat_name,
                        "approved_budget": float(
                            FinancialEngine.to_decimal(
                                alloc.get("allocation_original", 0)
                            )
                        ),
                        "committed": float(
                            FinancialEngine.to_decimal(alloc.get("total_expenses", 0))
                        ),
                        "certified": 0.0,
                        "remaining": float(
                            FinancialEngine.to_decimal(
                                alloc.get("allocation_remaining", 0)
                            )
                        ),
                    }
                )

            results.append(
                {
                    "project_id": p_id,
                    "project_name": proj.get("name") or proj.get("project_name"),
                    "project_code": proj.get("project_code"),
                    "status": proj.get("status", "Active"),
                    "completion_pct": float(
                        FinancialEngine.to_decimal(proj.get("completion_percentage", 0))
                    ),
                    "budget": {
                        "total_master": (
                            float(
                                FinancialEngine.to_decimal(
                                    master_state.get("original_budget", 0)
                                )
                            )
                            if master_state
                            else 0.0
                        ),
                        "total_committed": (
                            float(
                                FinancialEngine.to_decimal(
                                    master_state.get("committed_value", 0)
                                )
                            )
                            if master_state
                            else 0.0
                        ),
                        "total_certified": (
                            float(
                                FinancialEngine.to_decimal(
                                    master_state.get("certified_value", 0)
                                )
                            )
                            if master_state
                            else 0.0
                        ),
                        "total_remaining": (
                            float(
                                FinancialEngine.to_decimal(
                                    master_state.get("balance_budget_remaining", 0)
                                )
                            )
                            if master_state
                            else 0.0
                        ),
                        "categories": categories_data,
                    },
                    "petty_cash_total": float(petty_cash_total),
                    "dprs": {
                        "total": dpr_total,
                        "today": dpr_today,
                        "pending_approvals": dpr_pending,
                    },
                    "workers": {"recent_total": recent_workers},
                }
            )

        return {
            "projects": results,
            "summary": {
                "total_projects": len(results),
                "total_pending_dprs": sum(
                    p["dprs"]["pending_approvals"] for p in results
                ),
                "total_active_workers": sum(
                    p["workers"]["recent_total"] for p in results
                ),
            },
        }

    async def _project_summary_report(self, project_id: str) -> Dict[str, Any]:
        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$addFields": {"cid_obj": {"$toObjectId": "$category_id"}}},
            {
                "$lookup": {
                    "from": "code_master",
                    "localField": "cid_obj",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {
                "$project": {
                    "original_budget": 1,
                    "committed_value": 1,
                    "certified_value": 1,
                    "balance_budget_remaining": 1,
                    "category_name": {"$arrayElemAt": ["$category.category_name", 0]},
                    "category_code": {"$arrayElemAt": ["$category.code", 0]},
                }
            },
            {"$sort": {"category_code": 1}},
        ]

        financial_data = await self.db.financial_state.aggregate(pipeline).to_list(None)
        rows = []
        totals = {
            "budget": Decimal("0"),
            "committed": Decimal("0"),
            "certified": Decimal("0"),
            "remaining": Decimal("0"),
        }

        for item in financial_data:
            budget = FinancialEngine.to_decimal(item.get("original_budget") or 0)
            committed = FinancialEngine.to_decimal(item.get("committed_value") or 0)
            certified = FinancialEngine.to_decimal(item.get("certified_value") or 0)
            remaining = FinancialEngine.to_decimal(item.get("balance_budget_remaining") or 0)

            rows.append(
                [
                    item.get("category_code") or "N/A",
                    item.get("category_name") or "Unnamed Category",
                    ExportService.format_currency(budget),
                    ExportService.format_currency(committed),
                    ExportService.format_currency(certified),
                    ExportService.format_currency(remaining),
                    "Active",
                ]
            )
            totals["budget"] += budget
            totals["committed"] += committed
            totals["certified"] += certified
            totals["remaining"] += remaining

        return {
            "title": "Project Financial Summary",
            "project_id": project_id,
            "rows": rows,
            "totals": {k: str(v) for k, v in totals.items()},
            "metadata": {"generated_at": now().isoformat(), "row_count": len(rows)},
        }

    async def _work_order_tracker_report(
        self,
        project_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> Dict[str, Any]:
        match_stage = {"project_id": project_id}
        if start_date or end_date:
            match_stage["created_at"] = {
                k: v for k, v in [("$gte", start_date), ("$lte", end_date)] if v
            }

        pipeline = [
            {"$match": match_stage},
            {"$addFields": {
                "cid_obj": {"$toObjectId": "$category_id"},
                "vid_obj": {"$toObjectId": "$vendor_id"}
            }},
            {
                "$lookup": {
                    "from": "code_master",
                    "localField": "cid_obj",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {
                "$lookup": {
                    "from": "vendors",
                    "localField": "vid_obj",
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
                    "created_at": 1,
                }
            },
            {"$sort": {"created_at": -1}},
        ]
        wo_data = await self.db.work_orders.aggregate(pipeline).to_list(None)
        rows = []
        total_amount = Decimal("0")
        for wo in wo_data:
            amount = FinancialEngine.to_decimal(wo.get("grand_total") or 0)
            ret_amount = FinancialEngine.to_decimal(wo.get("retention_amount") or 0)
            c_at = wo.get("created_at")
            date_str = c_at.strftime("%Y-%m-%d") if c_at else "N/A"

            rows.append(
                [
                    wo.get("category_code") or "N/A",
                    wo.get("wo_ref") or "N/A",
                    wo.get("vendor_name") or "Unknown",
                    ExportService.format_currency(amount),
                    ExportService.format_currency(ret_amount),
                    date_str,
                    "Active",
                ]
            )
            total_amount += amount
        return {
            "title": "Work Order Tracker",
            "rows": rows,
            "totals": {"total_amount": str(total_amount)},
        }

    async def _payment_certificate_tracker_report(
        self,
        project_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> Dict[str, Any]:
        match_stage = {"project_id": project_id}
        if start_date or end_date:
            match_stage["created_at"] = {
                k: v for k, v in [("$gte", start_date), ("$lte", end_date)] if v
            }
        pipeline = [
            {"$match": match_stage},
            {"$addFields": {
                "cid_obj": {"$toObjectId": "$category_id"},
                "vid_obj": {"$toObjectId": "$vendor_id"}
            }},
            {
                "$lookup": {
                    "from": "code_master",
                    "localField": "cid_obj",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {
                "$lookup": {
                    "from": "vendors",
                    "localField": "vid_obj",
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
            amount = FinancialEngine.to_decimal(pc.get("grand_total") or 0)
            c_at = pc.get("created_at")
            date_str = c_at.strftime("%Y-%m-%d") if c_at else "N/A"
            
            rows.append(
                [
                    pc.get("category_code") or "N/A",
                    pc.get("pc_ref") or "N/A",
                    pc.get("vendor_name") or "Unknown",
                    ExportService.format_currency(amount),
                    date_str,
                    ExportService.format_currency(amount) if pc.get("status") == "Closed" else "₹ 0.00",
                    pc.get("status") or "Draft",
                ]
            )
            total_certified += amount
        return {
            "title": "Payment Certificate Tracker",
            "rows": rows,
            "totals": {"total_certified": str(total_certified)},
        }

    async def _petty_cash_tracker_report(
        self,
        project_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> Dict[str, Any]:
        match_stage = {"project_id": project_id, "work_order_id": None}
        if start_date or end_date:
            match_stage["created_at"] = {
                k: v for k, v in [("$gte", start_date), ("$lte", end_date)] if v
            }
        pcs = (
            await self.db.payment_certificates.find(match_stage)
            .sort("created_at", 1)
            .to_list(None)
        )
        rows = []
        total_value = Decimal("0")
        for pc in pcs:
            amount = FinancialEngine.to_decimal(pc.get("grand_total") or 0)
            c_at = pc.get("created_at")
            date_str = c_at.strftime("%Y-%m-%d") if c_at else "N/A"
            
            rows.append(
                [
                    date_str,
                    pc.get("pc_ref") or "N/A",
                    ExportService.format_currency(amount),
                    "Refill Request",
                ]
            )
            total_value += amount
        return {
            "title": "Petty Cash & OVH Tracker",
            "rows": rows,
            "totals": {"total_funds_received": str(total_value)},
        }

    async def _csa_report(
        self,
        project_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> Dict[str, Any]:
        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$addFields": {"cid_obj": {"$toObjectId": "$category_id"}}},
            {
                "$lookup": {
                    "from": "code_master",
                    "localField": "cid_obj",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {"$match": {"category.code": "CSA"}},
            {
                "$project": {
                    "wo_ref": 1,
                    "category_code": {"$arrayElemAt": ["$category.code", 0]},
                    "description": "$notes",
                    "created_at": 1,
                }
            },
        ]
        items = await self.db.work_orders.aggregate(pipeline).to_list(None)
        rows = [
            [
                p.get("category_code", "CSA"),
                p.get("wo_ref"),
                p.get("description") or "Asset",
                1,
                p.get("created_at").strftime("%Y-%m-%d"),
            ]
            for p in items
        ]
        return {
            "title": "CSA Report",
            "rows": rows,
            "totals": {"total_count": len(rows)},
        }

    async def _progress_report(
        self,
        project_id: str,
        window: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> Dict[str, Any]:
        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$addFields": {
                "cid_obj": {"$toObjectId": "$category_id"},
                "vid_obj": {"$toObjectId": "$vendor_id"}
            }},
            {
                "$lookup": {
                    "from": "code_master",
                    "localField": "cid_obj",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {
                "$lookup": {
                    "from": "vendors",
                    "localField": "vid_obj",
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
            },
        ]
        wos = await self.db.work_orders.aggregate(pipeline).to_list(None)
        rows = [
            [
                w.get("category_code"),
                w.get("wo_ref"),
                w.get("vendor_name"),
                1.0 if w.get("status") == "Closed" else 0.5,
                w.get("status"),
            ]
            for w in wos
        ]
        return {"title": f"{window.title()} Progress Report", "rows": rows}
