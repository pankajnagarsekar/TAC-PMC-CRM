"""
Baseline Comparison Engine.
Computes variances between two historical snapshots or current vs baseline.

Constitution §2.2 / Phase 4, Session 4.3:
    - SV (Schedule Variance) = current_finish - baseline_finish
    - CV (Cost Variance) = current_cost - baseline_cost
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from execution.scheduler.models.schedule_baselines import BaselineComparisonResult, ScheduleBaseline
from execution.scheduler.models.shared_types import PyObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

class BaselineComparisonService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def compare_baselines(
        self, 
        project_id: str, 
        baseline_a_num: int, 
        baseline_b_num: Optional[int] = None
    ) -> List[BaselineComparisonResult]:
        """
        Compares Baseline A (older) with Baseline B (newer/current).
        If B is None, compares A with the CURRENT active schedule.
        """
        # 1. Fetch Baseline A
        cursor_a = await self.db.schedule_baselines.find_one({
            "project_id": PyObjectId(project_id),
            "baseline_number": baseline_a_num
        })
        if not cursor_a:
             return []
        
        baseline_a = ScheduleBaseline(**cursor_a)
        map_a = {str(t["task_id"]): t for t in baseline_a.snapshot_data}

        # 2. Fetch Baseline B or Current Tasks
        map_b = {}
        if baseline_b_num:
            cursor_b = await self.db.schedule_baselines.find_one({
                "project_id": PyObjectId(project_id),
                "baseline_number": baseline_b_num
            })
            if cursor_b:
                baseline_b = ScheduleBaseline(**cursor_b)
                map_b = {str(t["task_id"]): t for t in baseline_b.snapshot_data}
        else:
            # Get current tasks
            current_tasks = await self.db.project_schedules.find({
                "project_id": project_id, 
                "is_deleted": False
            }).to_list(length=10000)
            map_b = {str(t["_id"]): t for t in current_tasks}

        # 3. Compute Variances
        results = []
        for task_id, task_a in map_a.items():
            task_b = map_b.get(task_id)
            if not task_b:
                continue

            # Schedule Variance (Days)
            start_a = task_a.get("scheduled_start")
            finish_a = task_a.get("scheduled_finish")
            start_b = task_b.get("scheduled_start")
            finish_b = task_b.get("scheduled_finish")
            
            # Cost Variance
            cost_a = Decimal(str(task_a.get("baseline_cost", "0")))
            cost_b = Decimal(str(task_b.get("baseline_cost") or task_b.get("scheduled_cost") or "0"))
            
            var_pct = 0.0
            if cost_a > 0:
                var_pct = float((cost_b - cost_a) / cost_a * 100)

            results.append(BaselineComparisonResult(
                task_id=task_id,
                wbs_code=task_a.get("wbs_code", ""),
                task_name=task_a.get("task_name", ""),
                baseline_a_start=start_a,
                baseline_a_finish=finish_a,
                baseline_b_start=start_b,
                baseline_b_finish=finish_b,
                schedule_variance_days=0, 
                baseline_a_cost=cost_a,
                baseline_b_cost=cost_b,
                cost_variance_percent=var_pct
            ))

        return results
