import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.modules.shared.domain.exceptions import ValidationError
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Sovereign Scheduler Controller.
    Orchestrates deterministic scheduling logic.
    """

    def __init__(self, db):
        self.db = db
        self.collection = db["project_schedules"]


    async def run_scheduler_script(self, script_name: str, input_data: dict) -> dict:
        """Orchestrate calls to standalone, deterministic Python scripts (Async)."""
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )  # apps/api/app
        script_path = os.path.join(base_dir, "modules", "scheduler", script_name)

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            input_json = json.dumps(input_data).encode()
            stdout, stderr = await process.communicate(input=input_json)
            
            stdout_str = stdout.decode()
            stderr_str = stderr.decode()

            if process.returncode != 0:
                error_msg = (
                    f"Scheduler execution error for {script_name}: {stderr_str or stdout_str}"
                )
                logger.error(f"SCHEDULER_SUBPROCESS_FAIL: {error_msg}")
                logger.error(f"STDOUT: {stdout_str}")
                logger.error(f"STDERR: {stderr_str}")
                raise ValidationError(error_msg)

            return json.loads(stdout_str)
        except Exception as e:
            raise ValidationError(str(e))

    async def calculate_schedule(
        self, project_id: str, tasks: List[Dict[str, Any]], project_start: str
    ) -> Dict[str, Any]:
        if not project_id:
             raise ValidationError("CRITICAL: Calculation aborted - project_id is None or empty")

        input_payload = {"tasks": tasks, "project_start": project_start}
        
        # DEBUG: Save payload to file to inspect what's being sent
        try:
            with open("last_scheduler_payload.json", "w") as f:
                json.dump(serialize_doc(input_payload), f)
        except:
            pass

        task_count = len(tasks) if tasks is not None else 0
        logger.info(f"SCHEDULER: Calculating for project {project_id} with {task_count} tasks starting at {project_start}")
        
        if task_count == 0:
            return {
                "tasks": [],
                "critical_path": [],
                "total_duration_days": 0,
                "status": "success",
                "calculation_version": f"empty_{int(datetime.now().timestamp())}",
                "system_state": "active",
                "schedule_version": 1
            }

        # DIRECT CALL: Avoid subprocess overhead and Windows pipe issues
        from app.modules.scheduler.calculate_critical_path import run_calculation
        # Serialize first to strip ObjectId/datetime from MongoDB task documents
        clean_payload = serialize_doc(input_payload)
        results = run_calculation(clean_payload)

        if "error" in results:
            raise ValidationError(results["error"])

        return serialize_doc(results)

    async def save_schedule(
        self, project_id: str, organisation_id: str, user_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        schedule_doc = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "tasks": data.get("tasks", []),
            "project_start": data.get("project_start"),
            "total_cost": data.get("total_cost"),
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc),
        }

        await self.collection.update_one(
            {"project_id": project_id, "organisation_id": organisation_id},
            {"$set": schedule_doc},
            upsert=True,
        )
        return {"message": "Project schedule saved successfully"}

    async def delete_task(
        self, project_id: str, organisation_id: str, task_id: str
    ) -> Dict[str, Any]:
        """Permanently remove a task and update project schedule."""
        schedule = await self.load_schedule(project_id, organisation_id)
        if not schedule or "tasks" not in schedule:
            raise ValidationError("Schedule not found")

        original_count = len(schedule["tasks"])
        schedule["tasks"] = [t for t in schedule["tasks"] if t.get("task_id") != task_id]

        if len(schedule["tasks"]) == original_count:
             return {"message": "Task not found in schedule", "count": original_count}

        await self.collection.update_one(
            {"project_id": project_id, "organisation_id": organisation_id},
            {
                "$set": {
                    "tasks": schedule["tasks"],
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return {"message": "Task deleted successfully", "count": len(schedule["tasks"])}

    async def load_schedule(
        self, project_id: str, organisation_id: str
    ) -> Dict[str, Any]:
        """Authoritative schedule retrieval with resilience."""
        from bson import ObjectId

        try:
            # Handle both string and ObjectId project_id for legacy compatibility
            query = {
                "$or": [
                    {"project_id": project_id},
                    {"project_id": ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id}
                ],
                "organisation_id": organisation_id
            }
            
            schedule = await self.collection.find_one(query)

            if not schedule:
                # Try project_id without organisation_id if it's a migration case
                schedule = await self.collection.find_one({"project_id": project_id})
                if schedule:
                    logger.warning(f"Found schedule for {project_id} without organisation_id check")

            if not schedule:
                return {
                    "project_id": project_id,
                    "tasks": [],
                    "project_start": None,
                    "total_cost": 0,
                }

            return serialize_doc(schedule)
        except Exception as e:
            logger.error(f"FATAL_SCHEDULER_LOAD: {str(e)}")
            # Fallback to default instead of 500 to keep UI functional
            return {
                "project_id": project_id,
                "tasks": [],
                "error": f"Internal Error: {str(e)}"
            }

    async def compare_baselines(
        self, project_id: str, organisation_id: str, baseline_a: int, baseline_b: int = None
    ) -> List[Dict[str, Any]]:
        # Fetch current schedule
        schedule = await self.load_schedule(project_id, organisation_id)
        tasks = schedule.get("tasks", [])
        
        results = []
        for t in tasks:
            b_start = t.get("baseline_start") or t.get("scheduled_start")
            b_finish = t.get("baseline_finish") or t.get("scheduled_finish")
            s_start = t.get("scheduled_start")
            s_finish = t.get("scheduled_finish")
            
            variance = 0
            if b_finish and s_finish:
                fmt = "%Y-%m-%d"
                try:
                    bf = datetime.strptime(b_finish[:10], fmt)
                    sf = datetime.strptime(s_finish[:10], fmt)
                    variance = (sf - bf).days
                except:
                    pass
            
            results.append({
                "task_id": str(t.get("task_id", "")),
                "baseline_a_start": b_start,
                "baseline_a_finish": b_finish,
                "baseline_b_start": s_start,
                "baseline_b_finish": s_finish,
                "schedule_variance_days": variance
            })
            
        return results
