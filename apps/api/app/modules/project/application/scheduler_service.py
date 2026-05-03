import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.modules.shared.domain.exceptions import ValidationError, DataFreezeError
from app.core.utils import serialize_doc
from app.modules.scheduler.baseline_manager import BaselineManager

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Sovereign Scheduler Controller.
    Orchestrates deterministic scheduling logic.
    """

    def __init__(self, db, audit_service=None, undo_redo_service=None):
        self.db = db
        self.collection = db["project_schedules"]
        self.audit_service = audit_service
        self.baseline_manager = BaselineManager(db)
        self.undo_redo_service = undo_redo_service

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
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_json),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                process.kill()
                error_msg = f"Scheduler execution timeout for {script_name} (exceeded 30s)"
                logger.error(f"SCHEDULER_TIMEOUT: {error_msg}")
                raise ValidationError(error_msg)

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

        # Load project calendar
        calendar = await self.db.project_calendars.find_one({"project_id": project_id})
        if not calendar:
            # Default Goa-style calendar (Mon-Sat)
            calendar = {
                "project_id": project_id,
                "working_days": [0, 1, 2, 3, 4, 5],
                "shift_start": "08:00",
                "shift_end": "17:00",
                "lunch_start": "13:00",
                "lunch_end": "14:00",
                "exceptions": []
            }

        input_payload = {
            "tasks": tasks,
            "project_start": project_start,
            "calendar": calendar
        }

        # DEBUG: Save payload to file to inspect what's being sent
        # Removed debug write to "last_scheduler_payload.json" for production stability

        task_count = len(tasks) if tasks is not None else 0
        logger.info(
            f"SCHEDULER: Calculating for project {project_id} with {task_count} tasks "
            f"starting at {project_start}"
        )

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

        # 1. VALIDATION & BASELINE ENFORCEMENT (BUG-014/015)
        self._validate_tasks(tasks)

        # SECURE OFF-THREAD CALL: Prevent event loop blocking for CPU-bound engine
        import asyncio
        from app.modules.scheduler.calculate_critical_path import run_calculation

        # Serialize first to strip ObjectId/datetime from MongoDB task documents
        clean_payload = serialize_doc(input_payload)
        results = await asyncio.to_thread(run_calculation, clean_payload)

        if "error" in results:
            raise ValidationError(results["error"])

        return serialize_doc(results)

    async def save_schedule(
        self, project_id: str, organisation_id: str, user_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save schedule with undo/redo snapshot capture (after-capture pattern)."""
        tasks = data.get("tasks", [])

        # 1. VALIDATION (BUG-014/015)
        self._validate_tasks(tasks)

        schedule_doc = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "tasks": tasks,
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

        # Capture snapshot for undo/redo after successful save
        if self.undo_redo_service:
            new_tasks = data.get("tasks", [])
            if new_tasks:  # only capture if there are tasks
                await self.undo_redo_service.capture_snapshot(
                    project_id=project_id,
                    org_id=organisation_id,
                    user_id=user_id,
                    change_type="SAVE_SCHEDULE",
                    summary=f"Schedule saved ({len(new_tasks)} tasks)",
                    tasks=new_tasks,
                )

        # Audit Logging (Fixed Phase 7: Audit Log incomplete)
        if self.audit_service:
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="SCHEDULER",
                entity_type="SCHEDULE",
                entity_id=project_id,
                action_type="SAVE",
                user_id=user_id,
                project_id=project_id,
                new_value={"task_count": len(tasks), "total_cost": data.get("total_cost")},
            )

        return {"message": "Project schedule saved successfully"}

    async def save_schedule_raw(
        self, project_id: str, organisation_id: str, user_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save schedule WITHOUT undo/redo snapshot capture.
        Used internally by undo/redo routes to avoid capture loop.
        """
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
        self, project_id: str, organisation_id: str, task_id: str, user_id: str = None
    ) -> Dict[str, Any]:
        """Permanently remove a task and update project schedule."""
        return await self.delete_tasks_bulk(project_id, organisation_id, [task_id], user_id)

    async def delete_tasks_bulk(
        self, project_id: str, organisation_id: str, task_ids: List[str], user_id: str = None
    ) -> Dict[str, Any]:
        """Permanently remove multiple tasks and update project schedule."""
        schedule = await self.load_schedule(project_id, organisation_id)
        if not schedule or "tasks" not in schedule:
            raise ValidationError("Schedule not found")

        original_count = len(schedule["tasks"])
        ids_to_delete = set(task_ids)

        # Capture before-state snapshot for undo
        if self.undo_redo_service and user_id:
            await self.undo_redo_service.capture_snapshot(
                project_id=project_id,
                org_id=organisation_id,
                user_id=user_id,
                change_type="DELETE_TASKS_BULK",
                summary=f"Deleted {len(ids_to_delete)} tasks",
                tasks=schedule.get("tasks", []),
            )

        # Filter out tasks to delete
        schedule["tasks"] = [t for t in schedule["tasks"] if str(t.get("task_id")) not in ids_to_delete]

        deleted_count = original_count - len(schedule["tasks"])
        if deleted_count == 0:
            return {"message": "No tasks found to delete", "count": 0}

        await self.collection.update_one(
            {"project_id": project_id, "organisation_id": organisation_id},
            {
                "$set": {
                    "tasks": schedule["tasks"],
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return {"message": "Tasks deleted successfully", "count": deleted_count}

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
                # No fallback without org_id - security first
                # If schedule not found with org_id, return empty rather than bypass security
                pass

            if not schedule:
                return {
                    "project_id": project_id,
                    "tasks": [],
                    "project_start": None,
                    "total_cost": 0,
                }

            serialized = serialize_doc(schedule)
            tasks = serialized.get("tasks", [])

            # 1. Collect all unique assignee_ids
            all_assignee_ids = set()
            for task in tasks:
                if task.get("assignee_ids"):
                    all_assignee_ids.update([str(aid) for aid in task["assignee_ids"]])

            # 2. Fetch user details (name/initials)
            user_map = {}
            if all_assignee_ids:
                from bson import ObjectId
                # Handle both string and ObjectId
                id_query = []
                for aid in all_assignee_ids:
                    id_query.append(aid)
                    if ObjectId.is_valid(aid):
                        id_query.append(ObjectId(aid))

                users_cursor = self.db.users.find({"_id": {"$in": id_query}}, {"full_name": 1, "email": 1})
                async for u in users_cursor:
                    uid = str(u["_id"])
                    user_map[uid] = {
                        "name": u.get("full_name") or u.get("email", "Unknown"),
                        "initial": (u.get("full_name") or "U")[0].upper() if u.get("full_name") else "?"
                    }

            # 3. Normalize and enrich tasks
            for task in tasks:
                # Normalize task_id to string (seed data uses integers; frontend expects strings)
                if "task_id" in task and not isinstance(task["task_id"], str):
                    task["task_id"] = str(task["task_id"])

                # Enrich assignees
                if task.get("assignee_ids"):
                    task["assignee_details"] = [
                        user_map.get(str(aid), {"name": str(aid), "initial": "?"})
                        for aid in task["assignee_ids"]
                    ]

                # Normalize predecessor task_ids too
                for pred in task.get("predecessors", []) or []:
                    if isinstance(pred, dict) and "task_id" in pred and not isinstance(pred["task_id"], str):
                        pred["task_id"] = str(pred["task_id"])
            return serialized
        except Exception as e:
            logger.error(f"FATAL_SCHEDULER_LOAD: {str(e)}")
            # Fallback to default instead of 500 to keep UI functional
            return {
                "project_id": project_id,
                "tasks": [],
                "project_start": None,
                "total_cost": 0,
            }

    async def sync_financials(self, project_id: str, organisation_id: str, session=None) -> None:
        """
        Synchronizes the authoritative financial state with the scheduler tasks array.
        (Track H1: Data Linking).
        """
        financial_state_repo = self.db["financial_state"]

        # Load all states for this project
        cursor = financial_state_repo.find({"project_id": project_id}, session=session)
        states = await cursor.to_list(length=100)
        state_map = {s["category_id"]: s for s in states}
        master_state = state_map.get("MASTER")

        # Load schedule from DB directly to avoid recursive calls
        query = {"project_id": project_id, "organisation_id": organisation_id}
        schedule = await self.collection.find_one(query, session=session)
        if not schedule:
            return

        tasks = schedule.get("tasks", [])
        modified = False

        for task in tasks:
            # Root/Summary task mapping (Master)
            if str(task.get("task_id")) == "0" and master_state:
                new_val = float(master_state.get("committed_value", 0))
                if task.get("wo_value") != new_val:
                    task["wo_value"] = new_val
                    modified = True

            # Granular category mapping via external_ref_id or wbs_code
            mapping_id = task.get("external_ref_id") or task.get("wbs_code")
            if mapping_id and mapping_id in state_map:
                cat_state = state_map[mapping_id]
                new_val = float(cat_state.get("committed_value", 0))
                if task.get("wo_value") != new_val:
                    task["wo_value"] = new_val
                    modified = True

        if modified:
            await self.collection.update_one(
                {"project_id": project_id, "organisation_id": organisation_id},
                {"$set": {"tasks": tasks, "updated_at": datetime.now(timezone.utc)}},
                session=session
            )
            logger.info(f"SCHEDULER_SYNC: Financial data updated for project {project_id}")

    async def lock_baseline(
        self,
        project_id: str,
        organisation_id: str,
        user_id: str,
        baseline_version: int = 1,
    ) -> Dict[str, Any]:
        """
        Lock the current schedule as a baseline.

        Args:
            project_id: Project to lock
            organisation_id: Organization context
            user_id: User locking baseline
            baseline_version: Baseline version (default: 1)

        Returns:
            Lock status and snapshot info
        """
        schedule = await self.load_schedule(project_id, organisation_id)
        tasks = schedule.get("tasks", [])

        if not tasks:
            raise ValidationError("Cannot lock baseline with empty schedule")

        result = await self.baseline_manager.lock_baseline(
            project_id,
            organisation_id,
            user_id,
            tasks,
            baseline_version
        )

        # Persist locked tasks back to schedule
        locked_tasks = [
            {
                **task,
                "baseline_locked": True,
                "baseline_version": baseline_version,
                "baseline_locked_at": datetime.now(timezone.utc),
                "baseline_locked_by": user_id,
                "baseline_start": task.get("scheduled_start"),
                "baseline_finish": task.get("scheduled_finish"),
            }
            for task in tasks
        ]

        await self.collection.update_one(
            {"project_id": project_id, "organisation_id": organisation_id},
            {
                "$set": {
                    "tasks": locked_tasks,
                    "baseline_version": baseline_version,
                    "baseline_locked_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

        # Audit Logging
        if self.audit_service:
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="SCHEDULER",
                entity_type="BASELINE",
                entity_id=project_id,
                action_type="LOCK",
                user_id=user_id,
                project_id=project_id,
                new_value=result,
            )

        return result

    async def unlock_baseline(
        self,
        project_id: str,
        organisation_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Unlock the current baseline to allow further modifications.

        Args:
            project_id: Project to unlock
            organisation_id: Organization context
            user_id: User unlocking baseline

        Returns:
            Unlock status
        """
        schedule = await self.load_schedule(project_id, organisation_id)
        tasks = schedule.get("tasks", [])

        result = await self.baseline_manager.unlock_baseline(
            project_id,
            organisation_id,
            user_id,
            tasks
        )

        # Persist unlocked tasks back to schedule
        unlocked_tasks = [
            {**task, "baseline_locked": False}
            for task in tasks
        ]

        await self.collection.update_one(
            {"project_id": project_id, "organisation_id": organisation_id},
            {
                "$set": {
                    "tasks": unlocked_tasks,
                    "updated_at": datetime.now(timezone.utc),
                }
            }
        )

        # Audit Logging
        if self.audit_service:
            await self.audit_service.log_action(
                organisation_id=organisation_id,
                module_name="SCHEDULER",
                entity_type="BASELINE",
                entity_id=project_id,
                action_type="UNLOCK",
                user_id=user_id,
                project_id=project_id,
                new_value=result,
            )

        return result

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
                except Exception as e:
                    logger.warning(f"Failed to calculate variance for task {t.get('task_id')}: {e}")

            results.append({
                "task_id": str(t.get("task_id", "")),
                "baseline_a_start": b_start,
                "baseline_a_finish": b_finish,
                "baseline_b_start": s_start,
                "baseline_b_finish": s_finish,
                "schedule_variance_days": variance
            })

        return results

    def _validate_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Core validation for task hierarchy and baseline constraints (BUG-014/015/020/021)."""
        valid_task_ids = {str(t.get("task_id")) for t in tasks if t.get("task_id")}

        for t in tasks:
            tid = str(t.get("task_id", "unknown"))
            pid = t.get("parent_id")

            # 1. Orphan Check: If a parent is specified, it MUST exist in the payload
            if pid and str(pid) not in valid_task_ids:
                logger.warning(f"SCHEDULER_REPAIR: Task {tid} referenced missing parent {pid}. Removing broken link.")
                t["parent_id"] = None

            # 2. Description/Name Check (BUG-020/021): Prevent tasks with empty names
            # Resilience Policy: If a name is missing, seed it with a default rather than crashing the engine.
            # This prevents the 'clearing names' loop where a single bad record blocks all updates.
            name = t.get("task_name") or t.get("task_description")
            if not name or not str(name).strip():
                # For drafts, using a placeholder is acceptable
                status_val = t.get("task_status", "draft")
                default_name = f"Unnamed Task ({tid})" if status_val != "draft" else "New Draft Task"
                t["task_name"] = default_name
                logger.warning(f"SCHEDULER_RECOVERY: Seeding missing name for task {tid} with '{default_name}'")

            # 3. Baseline Check: Modifications to locked tasks are strictly forbidden
            if t.get("baseline_locked"):
                logger.warning(f"BASELINE_LOCK_VIOLATION: Attempted change to Task {tid}")
                raise DataFreezeError(
                    "TASK",
                    f"Baseline (v{t.get('baseline_version', '1')})"
                )

    async def recalculate_for_calendar_change(self, project_id: str, organisation_id: str) -> Dict[str, Any]:
        """Authoritative trigger for re-calculating critical path after calendar updates."""
        schedule = await self.load_schedule(project_id, organisation_id)
        if not schedule or not schedule.get("tasks"):
            return {"message": "No tasks to recalculate"}

        tasks = schedule["tasks"]
        project_start = schedule.get("project_start") or datetime.now().strftime("%Y-%m-%d")

        # 1. Recalculate with new calendar (which calculate_schedule will fetch)
        results = await self.calculate_schedule(project_id, tasks, project_start)

        # 2. Persist results
        await self.save_schedule(
            project_id,
            organisation_id,
            "SYSTEM_CALENDAR_UPDATE",
            results
        )

        return results
