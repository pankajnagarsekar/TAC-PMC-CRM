import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

from bson import Decimal128

from app.modules.contracting.infrastructure.repository import WorkOrderRepository
from app.modules.financial.infrastructure.repository import (
    FinancialStateRepository,
    PCRepository,
)

# Repositories from other contexts
from app.modules.project.infrastructure.repository import (
    ProjectRepository,
    BudgetRepository,
    ScheduleRepository,
)
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.site_operations.infrastructure.repository import DPRRepository

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Sovereign Dashboard Provider.
    Optimized for consistent view-model delivery using authoritative read-models.
    """

    def __init__(self, db):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.wo_repo = WorkOrderRepository(db)
        self.fin_state_repo = FinancialStateRepository(db)
        self.schedule_repo = ScheduleRepository(db)
        self.dpr_repo = DPRRepository(db)
        self.pc_repo = PCRepository(db)

    def _parse_date(self, date_str: Any) -> datetime:
        if not date_str:
            return datetime.max.replace(tzinfo=timezone.utc)
        if isinstance(date_str, datetime):
            if date_str.tzinfo is None:
                return date_str.replace(tzinfo=timezone.utc)
            return date_str
        date_str = str(date_str).replace("/", "-")
        for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime.max.replace(tzinfo=timezone.utc)

    async def _resolve_project(self, project_id: str) -> Dict[str, Any]:
        """Resolves project by either ObjectId or project_id string."""
        from bson import ObjectId
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            # Try searching by the domain project_id string
            project = await self.project_repo.find_one({"project_id": project_id})
        
        if not project:
            from app.modules.shared.domain.exceptions import NotFoundError
            raise NotFoundError("Project", project_id)
        return project

    async def get_project_dashboard_stats(
        self, project_id: str, organisation_id: str
    ) -> Dict[str, Any]:
        """Uses authoritative FinancialState read-model for rapid delivery."""
        # Resolve canonical project details
        project = await self._resolve_project(project_id)
        canonical_id = project.get("project_id") or str(project.get("id"))

        # 1. Fetch Authoritative Snapshot with organisation isolation
        master_state = await self.fin_state_repo.find_one(
            {"project_id": canonical_id, "organisation_id": organisation_id, "code_id": None}
        )

        if not master_state:
            # Fallback to base lookup
            master_state = await self.fin_state_repo.find_one(
                {"project_id": canonical_id, "code_id": None}
            )

        if not master_state:
            logger.warning(
                f"DASHBOARD_CONSISTENCY: Master record missing for {canonical_id}. Recomputing."
            )
            agg = await self.fin_state_repo.aggregate(
                [
                    {
                        "$match": {
                            "project_id": canonical_id,
                            "organisation_id": organisation_id,
                            "code_id": {"$ne": None},
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                            "budget": {"$sum": "$original_budget"},
                            "committed": {"$sum": "$committed_value"},
                        }
                    },
                ]
            ).to_list(1)
            master_budget = agg[0]["budget"] if agg else Decimal128("0.0")
            total_committed = agg[0]["committed"] if agg else Decimal128("0.0")
        else:
            master_budget = master_state.get("original_budget", Decimal128("0.0"))
            total_committed = master_state.get("committed_value", Decimal128("0.0"))

        # 2. Project Overview Metrics
        total_phases = await self.budget_repo.count(
            {"project_id": canonical_id, "organisation_id": organisation_id}
        )
        active_items_count = await self.wo_repo.count(
            {"project_id": canonical_id, "organisation_id": organisation_id, "status": {"$in": ["Pending", "Draft"]}}
        )

        # 3. Overdue Milestones & Schedule Metrics
        schedule = await self.schedule_repo.find_one(
            {"project_id": canonical_id, "organisation_id": organisation_id}
        )
        if not schedule:
             schedule = await self.schedule_repo.find_one({"project_id": canonical_id})
        
        overdue_milestones, variance, critical_path_status = (
            0,
            Decimal("0.0"),
            "ON TRACK",
        )
        now_dt = datetime.now(timezone.utc)

        if schedule and "tasks" in schedule:
            tasks = schedule["tasks"]
            total_pv, total_ev = Decimal("0.0"), Decimal("0.0")
            for t in tasks:
                prog_pct = t.get("percentComplete") or t.get("progress") or 0
                prog = Decimal(str(prog_pct)) / Decimal("100.0")
                cost = FinancialEngine.to_decimal(t.get("cost"))
                total_pv += cost
                total_ev += cost * prog
                
                is_m = t.get("isMilestone") or t.get("is_milestone") or t.get("duration") == 0
                if is_m:
                    finish = self._parse_date(t.get("finish"))
                    if finish < now_dt and prog_pct < 100:
                        overdue_milestones += 1
                
                if (t.get("is_critical") or t.get("isCritical")) and prog < 1:
                    finish = self._parse_date(t.get("finish"))
                    if finish < now_dt:
                        critical_path_status = "DELAYED"
            
            if total_pv > 0:
                variance = ((total_ev - total_pv) / total_pv) * 100

        # 4. Compliance & Efficiency
        resolved_tasks = await self.wo_repo.count(
            {"project_id": canonical_id, "status": {"$in": ["Closed", "Completed"]}}
        )
        yesterday = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        dpr_recent = await self.db.worker_logs.count_documents(
            {"project_id": canonical_id, "created_at": {"$gte": yesterday}}
        )

        total_log_tasks = active_items_count + resolved_tasks
        compliance = (
            Decimal(str(resolved_tasks)) / Decimal(str(max(1, total_log_tasks)))
        ) * 100
        if dpr_recent == 0 and compliance > 10:
            compliance -= 5

        # 5. Task Manager
        pending_wos = await self.wo_repo.list(
            {"project_id": canonical_id, "status": {"$in": ["Pending", "Draft"]}},
            sort=[("updated_at", -1)],
            limit=3,
        )
        task_manager_items = [
            {
                "id": wo.get("wo_ref") or f"WO-{str(wo.get('id'))[:6]}",
                "label": "Approve Work Order",
                "priority": ("Financial" if FinancialEngine.to_decimal(wo.get("grand_total")) > 100000 else "Routine"),
                "color": ("text-primary" if FinancialEngine.to_decimal(wo.get("grand_total")) > 100000 else "text-zinc-400"),
            }
            for wo in pending_wos
        ]
        if not task_manager_items:
            task_manager_items.append({"id": "SYS", "label": "No urgent actions", "priority": "Low", "color": "text-zinc-500"})

        return {
            "project_id": canonical_id,
            "overview": {
                "total_phases": total_phases,
                "active_items": active_items_count,
                "overdue_milestones": overdue_milestones,
                "master_budget": float(FinancialEngine.to_decimal(master_budget)),
                "total_committed": float(FinancialEngine.to_decimal(total_committed)),
            },
            "schedule_status": {
                "variance": float(round(variance, 1)),
                "critical_path_status": critical_path_status,
            },
            "task_log": {
                "open_tasks": active_items_count,
                "resolved_tasks": resolved_tasks,
                "compliance_rate": float(round(compliance, 1)),
            },
            "task_manager": task_manager_items,
        }

    async def get_financials(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch project category financials from authoritative read-model."""
        project = await self._resolve_project(project_id)
        canonical_id = project.get("project_id") or str(project.get("id"))
        
        financials = await self.fin_state_repo.list(
            {"project_id": canonical_id, "category_id": {"$ne": None}},
            limit=500,
            sort=[("category_id", 1)],
        )
        return financials

    async def get_vendor_payables(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch pending payables per vendor for a project."""
        project = await self._resolve_project(project_id)
        canonical_id = project.get("project_id") or str(project.get("id"))

        pipeline = [
            {"$match": {"project_id": canonical_id, "status": "Closed"}},
            {
                "$group": {
                    "_id": "$vendor_id",
                    "vendor_name": {"$first": "$vendor_name"},
                    "total_certified": {"$sum": "$grand_total"},
                    "paid_amount": {"$sum": "$paid_amount"},
                }
            },
            {
                "$project": {
                    "vendor_id": "$_id",
                    "vendor_name": 1,
                    "net_payable": {
                        "$subtract": [
                            "$total_certified",
                            {"$ifNull": ["$paid_amount", 0]},
                        ]
                    },
                }
            },
            {"$match": {"net_payable": {"$gt": 0}}},
            {"$sort": {"net_payable": -1}},
        ]

        results = await self.db.payment_certificates.aggregate(pipeline).to_list(100)
        return results
