from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import HTTPException
from decimal import Decimal
from bson import Decimal128

from app.core.reporting_service import ReportingService as CoreReportingService
from app.core.export_service import ExportService
from app.repositories.financial_repo import BudgetRepository, WorkOrderRepository, FinancialStateRepository
from app.repositories.site_repo import WorkerLogRepository

class ReportingService:
    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker
        self.core_service = CoreReportingService(db)
        self.budget_repo = BudgetRepository(db)
        self.wo_repo = WorkOrderRepository(db)
        self.fin_state_repo = FinancialStateRepository(db)
        self.worker_log_repo = WorkerLogRepository(db)

    async def get_report(self, user: dict, project_id: str, report_type: str, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        
        if not ExportService.validate_report_type(report_type):
            raise HTTPException(status_code=400, detail="Invalid report type.")

        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        return await self.core_service.generate_report(
            project_id=project_id,
            report_type=report_type,
            start_date=start_dt,
            end_date=end_dt
        )

    async def get_dashboard_stats(self, user: dict, project_id: str) -> Dict[str, Any]:
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
        
        def to_decimal(val):
            if val is None: return Decimal("0.0")
            if isinstance(val, Decimal128): return val.to_decimal()
            try: return Decimal(str(val))
            except: return Decimal("0.0")

        for b in budgets:
            cid = str(b.get("category_id"))
            master_budget += to_decimal(b.get("original_budget"))
            total_committed += to_decimal(fin_map.get(cid, {}).get("committed_value"))

        # 2. Project Log & Compliance
        resolved_tasks = await self.wo_repo.count({
            "project_id": project_id, 
            "status": {"$in": ["Closed", "Completed"]}
        })
        
        now = datetime.now(timezone.utc)
        yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0)
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

        # 3. Task Manager - Latest 3 Actionable Items
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
                "id": wo.get("wo_ref") or f"WO-{str(wo['id'])[:6]}",
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
                "master_budget": float(master_budget),
                "total_committed": float(total_committed)
            },
            "task_log": {
                "open_tasks": active_items_count,
                "resolved_tasks": resolved_tasks,
                "compliance_rate": float(round(compliance_rate, 1))
            },
            "task_manager": task_manager_items
        }
