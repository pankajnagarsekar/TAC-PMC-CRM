from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List
import logging
from bson import Decimal128

from app.repositories.financial_repo import BudgetRepository, WorkOrderRepository, FinancialStateRepository
from app.repositories.project_repo import ScheduleRepository
from app.repositories.site_repo import DPRRepository
from app.core.financial_utils import to_decimal

logger = logging.getLogger(__name__)

class DashboardService:
    def __init__(self, db):
        self.db = db
        self.budget_repo = BudgetRepository(db)
        self.wo_repo = WorkOrderRepository(db)
        self.fin_state_repo = FinancialStateRepository(db)
        self.schedule_repo = ScheduleRepository(db)
        self.dpr_repo = DPRRepository(db)

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.max.replace(tzinfo=timezone.utc)
        
        date_str = date_str.replace("/", "-")
        for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime.max.replace(tzinfo=timezone.utc)

    async def get_project_dashboard_stats(self, project_id: str, organisation_id: str) -> Dict[str, Any]:
        """
        Returns aggregated statistics for the dashboard.
        """
        # 1. Project Overview & Financial Totals
        total_phases = await self.budget_repo.count_documents({"project_id": project_id})
        active_items_count = await self.wo_repo.count_documents({
            "project_id": project_id, 
            "status": {"$in": ["Pending", "Draft"]}
        })
        
        # Calculate Project-Wide Totals
        budgets = await self.budget_repo.list({"project_id": project_id}, limit=500)
        financials = await self.fin_state_repo.list({"project_id": project_id}, limit=500)
        fin_map = {str(f.get("category_id")): f for f in financials}
        
        master_budget = Decimal("0.0")
        total_committed = Decimal("0.0")
        
        for b in budgets:
            cid = str(b.get("category_id"))
            master_budget += to_decimal(b.get("original_budget"))
            total_committed += to_decimal(fin_map.get(cid, {}).get("committed_value"))

        # 2. Overdue Milestones & Schedule Metrics
        schedule = await self.schedule_repo.find_one({"project_id": project_id})
        overdue_milestones = 0
        critical_path_status = "ON TRACK"
        variance = Decimal("0.0")
        
        now = datetime.now(timezone.utc)
        
        if schedule and "tasks" in schedule:
            tasks = schedule["tasks"]
            total_pv = Decimal("0.0")
            total_ev = Decimal("0.0")
            
            for t in tasks:
                is_milestone = t.get("isMilestone") or t.get("is_milestone") or t.get("duration") == 0
                finish_date = self._parse_date(t.get("finish"))
                progress_val = t.get("percentComplete") or t.get("progress") or 0
                progress = Decimal(str(progress_val)) / Decimal("100.0")
                is_critical = t.get("is_critical") or t.get("isCritical") or False
                cost = to_decimal(t.get("cost"))
                
                if is_milestone and finish_date < now and progress_val < 100:
                    overdue_milestones += 1
                
                total_pv += cost
                total_ev += (cost * progress)
                
                if is_critical and progress < Decimal("1.0") and finish_date < now:
                    critical_path_status = "DELAYED"

            if total_pv > Decimal("0.0"):
                variance = ((total_ev - total_pv) / total_pv) * Decimal("100.0")

        # 3. Project Log & Compliance
        open_tasks = active_items_count
        resolved_tasks = await self.wo_repo.count_documents({
            "project_id": project_id, 
            "status": {"$in": ["Closed", "Completed"]}
        })
        
        yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0)
        dpr_recent = await self.dpr_repo.count_documents({
            "project_id": project_id,
            "created_at": {"$gte": yesterday}
        })
        
        total_log_tasks = open_tasks + resolved_tasks
        compliance_rate = Decimal("100.0")
        if total_log_tasks > 0:
            compliance_rate = (Decimal(str(resolved_tasks)) / Decimal(str(total_log_tasks))) * Decimal("100.0")
        
        if dpr_recent == 0 and compliance_rate > Decimal("10"):
            compliance_rate -= Decimal("5.0")

        # 4. Task Manager - Latest 3 Actionable Items
        task_manager_items = []
        pending_wos = await self.wo_repo.list(
            {"project_id": project_id, "status": {"$in": ["Pending", "Draft"]}},
            sort=[("updated_at", -1)],
            limit=3
        )
        for wo in pending_wos:
            grand_total = to_decimal(wo.get("grand_total"))
            priority = "Routine"
            if grand_total > Decimal("100000"): priority = "Financial"
            
            task_manager_items.append({
                "id": wo.get("wo_ref") or f"WO-{str(wo.get('id', ''))[:6]}",
                "label": f"Approve Work Order",
                "priority": priority,
                "color": "text-primary" if priority == "Financial" else "text-zinc-400"
            })

        if len(task_manager_items) < 3:
            task_manager_items.append({
                "id": "BETA",
                "label": "RFI Management coming soon",
                "priority": "System",
                "color": "text-zinc-500"
            })

        return {
            "project_id": project_id,
            "overview": {
                "total_phases": total_phases,
                "active_items": active_items_count,
                "overdue_milestones": overdue_milestones,
                "master_budget": float(master_budget),
                "total_committed": float(total_committed)
            },
            "schedule_status": {
                "variance": float(round(variance, 1)),
                "critical_path_status": critical_path_status
            },
            "task_log": {
                "open_tasks": open_tasks,
                "resolved_tasks": resolved_tasks,
                "compliance_rate": float(round(compliance_rate, 1))
            },
            "task_manager": task_manager_items
        }
