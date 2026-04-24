from datetime import datetime, timezone
from typing import Any, Dict, List
import asyncio
import logging
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.shared.domain.state_machine import StateMachine
from app.modules.tasks.infrastructure.repository import TaskRepository, TaskAISummaryRepository
from app.modules.tasks.domain.authorization import TaskAuthorizationManager
from app.modules.tasks.domain.exceptions import TaskSummaryGenerationError
from app.modules.tasks.infrastructure.cache_manager import TaskAISummaryCache
from app.modules.tasks.domain.constants import (
    TASK_AI_SUMMARY_CACHE_TTL_SECONDS,
    TASK_AI_SUMMARY_GENERATION_TIMEOUT_SECONDS,
    MAX_TOP_ASSIGNEES_IN_SUMMARY,
)
from app.modules.tasks.schemas.dto import TaskCreate, TaskUpdate
from app.modules.project.infrastructure.repository import ProjectRepository

logger = logging.getLogger(__name__)


class TaskService:
    """
    Task management service implementing domain-driven design patterns.

    This service orchestrates task operations including creation, updates, status transitions,
    and AI summary generation. It enforces:
    - Atomic serial number (sr_no) generation via MongoDB atomic operations
    - State machine-based status transitions with immutable final states
    - Organization scoping for multi-tenancy security
    - Cache invalidation on task mutations
    - Audit trail maintenance for compliance
    """

    def __init__(self, db: AsyncIOMotorDatabase, audit=None, perm=None, snap=None):
        """
        Initialize TaskService.

        Args:
            db: Motor async MongoDB database instance
            audit: Optional audit service for logging state changes
            perm: Optional permission service for role-based access
            snap: Optional snapshot service for state snapshots
        """
        self.db = db
        self.repo = TaskRepository(db)
        self.audit = audit
        self.perm = perm
        self.snap = snap

    async def create_task(self, user: dict, data: TaskCreate) -> Dict[str, Any]:
        """
        Create a new task with atomic sequential sr_no generation.

        Ensures unique sr_no within project scope via MongoDB's atomic find_one_and_update.
        All new tasks start in Open status with empty audit log.

        Args:
            user: Authenticated user dict with organisation_id, user_id, full_name
            data: TaskCreate DTO with task_description, assigned_to_name, priority, etc.

        Returns:
            Created task document with sr_no, status=Open, audit_log=[CREATE entry]

        Raises:
            HTTPException: On database errors
        """
        sr_no = await self.repo.get_next_sr_no(
            user["organisation_id"],
            data.project_id,
        )

        task_dict = data.model_dump()
        task_dict.update({
            "organisation_id": user["organisation_id"],
            "status": "Open",
            "sr_no": sr_no,
            "created_by": user["user_id"],
            "created_by_name": user.get("full_name") or user.get("name") or "System",
            "version": 1,
            "audit_log": [{
                "action": "CREATE",
                "timestamp": datetime.now(timezone.utc),
                "user": user.get("full_name") or user.get("name") or "System",
                "detail": f"Task created with sr_no {sr_no}",
            }],
        })
        task = await self.repo.create(task_dict)

        # Invalidate cached summary for this project
        await TaskAISummaryCache.invalidate_for_project(
            self.db,
            user["organisation_id"],
            data.project_id
        )

        return task

    async def get_task(self, user: dict, task_id: str) -> Dict[str, Any]:
        """
        Retrieve a single task with organization scoping.

        Args:
            user: Authenticated user dict (must have organisation_id)
            task_id: The task's MongoDB ObjectId as string

        Returns:
            Task document including audit_log, sr_no, status, etc.

        Raises:
            HTTPException(404): If task not found or user lacks org access
        """
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    async def update_status(self, user: dict, task_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update task status with StateMachine-enforced transitions.

        Validates transitions against the StateMachine. Closed is a terminal state.
        Logs the transition in audit_log and invalidates project's cached summary.

        Args:
            user: Authenticated user dict
            task_id: Task's MongoDB ObjectId as string
            new_status: Target status (Open, In Progress, Completed, Closed)

        Returns:
            Updated task document with incremented version and new audit_log entry

        Raises:
            HTTPException(400): If transition is invalid per StateMachine
            HTTPException(404): If task not found
        """
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Authorization check: verify org scoping
        TaskAuthorizationManager.verify_user_org_scoping(user["organisation_id"], task["organisation_id"])

        current_status = task.get("status", "Open")
        if new_status == current_status:
            return task

        # Delegate to the authoritative StateMachine (Task 3 fix)
        try:
            StateMachine.validate_transition("TASK", current_status, new_status)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        actor = user.get("full_name") or user.get("name") or "System"
        update_data = {"status": new_status, "version": task.get("version", 1) + 1}
        audit_entry = {
            "action": "STATUS_CHANGE",
            "timestamp": datetime.now(timezone.utc),
            "user": actor,
            "detail": f"Status changed from {current_status} to {new_status}",
        }
        await self.repo.update_one(
            {"_id": task["_id"]},
            {"$set": update_data, "$push": {"audit_log": audit_entry}},
        )

        # Invalidate cached summary for this project
        await TaskAISummaryCache.invalidate_for_project(
            self.db,
            user["organisation_id"],
            task["project_id"]
        )

        return await self.repo.get_by_id(task_id)

    async def update_task_details(self, user: dict, task_id: str, data: TaskUpdate) -> Dict[str, Any]:
        """
        Update task field details with immutability enforcement.

        Cannot update tasks in Closed state (terminal state). Increments version for
        optimistic locking and logs all field changes in audit_log.

        Args:
            user: Authenticated user dict
            task_id: Task's MongoDB ObjectId as string
            data: TaskUpdate DTO with fields to update (only set fields are updated)

        Returns:
            Updated task document with new audit_log entry

        Raises:
            HTTPException(400): If task is in Closed/frozen state
            HTTPException(404): If task not found
        """
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Authorization check: verify org scoping
        TaskAuthorizationManager.verify_user_org_scoping(user["organisation_id"], task["organisation_id"])

        # Task 7 fix: use StateMachine for consistent modification guard
        try:
            StateMachine.check_modification_allowed("TASK", task.get("status", "Open"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return task

        actor = user.get("full_name") or user.get("name") or "System"
        update_dict["version"] = task.get("version", 1) + 1
        audit_entry = {
            "action": "UPDATE",
            "timestamp": datetime.now(timezone.utc),
            "user": actor,
            "detail": f"Fields updated: {', '.join(update_dict.keys())}",
        }
        await self.repo.update_one(
            {"_id": task["_id"]},
            {"$set": update_dict, "$push": {"audit_log": audit_entry}},
        )

        # Invalidate cached summary for this project
        await TaskAISummaryCache.invalidate_for_project(
            self.db,
            user["organisation_id"],
            task["project_id"]
        )

        return await self.repo.get_by_id(task_id)

    async def get_tasks(self, user: dict, project_id: str) -> List[Dict[str, Any]]:
        """
        List all tasks for a project with organization scoping.

        Args:
            user: Authenticated user dict
            project_id: The project ID to filter by

        Returns:
            List of task documents for the project
        """
        return await self.repo.list({
            "organisation_id": user["organisation_id"],
            "project_id": project_id,
        })

    async def delete_task(self, user: dict, task_id: str) -> None:
        """
        Delete or close a task based on its state.
        Ensures administrative auditing for traceability (Phase 5 Hardening).

        Strategy:
        - Pristine Open tasks (CREATE log only): Hard-deleted from database
        - All other tasks: Transitioned to Closed status to preserve audit trail
        """
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Authorization check: verify org scoping
        TaskAuthorizationManager.verify_user_org_scoping(user["organisation_id"], task["organisation_id"])

        # If already Closed, nothing to do
        if task.get("status") == "Closed":
            return

        # Store project_id before deletion
        project_id = task.get("project_id")

        # Administrative Auditing: Log the deletion attempt
        if self.audit:
            await self.audit.log_action(
                organisation_id=user["organisation_id"],
                module_name="TASKS",
                entity_type="TASK",
                entity_id=task_id,
                action_type="DELETE",
                user_id=user["user_id"],
                project_id=project_id,
                old_value=task,
                metadata={"reason": "Manual deletion", "status_was": task.get("status")}
            )

        # Pristine Open tasks with only the CREATE log entry can be hard-deleted
        if task.get("status") == "Open" and len(task.get("audit_log", [])) <= 1:
            await self.repo.delete(task_id)
        else:
            # Transition to Closed — this preserves the audit trail
            await self.update_status(user, task_id, "Closed")

        # Invalidate cached summary for this project
        if project_id:
            await TaskAISummaryCache.invalidate_for_project(
                self.db,
                user["organisation_id"],
                project_id
            )

    async def get_task_summary_for_ai(self, user: dict, project_id: str) -> Dict[str, Any]:
        """
        Generate AI-powered task summary with intelligent caching.

        Workflow:
        1. Check cache (6-hour TTL) and return if valid
        2. Aggregate task metrics (status distribution, overdue count, top assignees)
        3. Call AI provider (OpenAI or mock) with 30-second timeout
        4. Store result in cache for future requests
        5. Invalidate cache when tasks change

        Args:
            user: Authenticated user dict
            project_id: Project ID to summarize

        Returns:
            Dict with summary_text (AI-generated) and metrics (aggregated data)

        Raises:
            TaskSummaryGenerationError: If AI generation fails (not timeout)
            HTTPException(500): On database errors
        """
        summary_repo = TaskAISummaryRepository(self.db)

        # 1. Check Cache (TTL configured in constants)
        try:
            existing = await summary_repo.find_one(
                {"project_id": project_id, "organisation_id": user["organisation_id"]},
                sort=[("created_at", -1)],
            )
            if existing:
                created_at = existing.get("created_at")
                if created_at and (datetime.now(timezone.utc) - created_at).total_seconds() < TASK_AI_SUMMARY_CACHE_TTL_SECONDS:
                    return existing
        except Exception as e:
            logger.error(f"Error checking cache for task summary: {str(e)}", exc_info=True)
            # Continue to regenerate on cache lookup error

        # 2. Aggregate task metrics
        try:
            tasks = await self.repo.list({
                "project_id": project_id,
                "organisation_id": user["organisation_id"],
            })
            if not tasks:
                return {"summary_text": "No tasks available to summarize.", "metrics": {}}
        except Exception as e:
            logger.error(f"Error aggregating task metrics: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to aggregate task metrics")

        total = len(tasks)
        open_tasks = [t for t in tasks if t.get("status") in ["Open", "In Progress"]]
        now = datetime.now(timezone.utc)
        overdue = sum(
            1 for t in open_tasks
            if t.get("deadline") and t["deadline"] < now
        )

        dist: Dict[str, int] = {}
        for t in tasks:
            s = t.get("status", "Unknown")
            dist[s] = dist.get(s, 0) + 1

        assignees: Dict[str, int] = {}
        for t in tasks:
            name = t.get("assigned_to_name", "Unassigned")
            assignees[name] = assignees.get(name, 0) + 1
        top_assignees = dict(
            sorted(assignees.items(), key=lambda x: x[1], reverse=True)[:MAX_TOP_ASSIGNEES_IN_SUMMARY]
        )

        report_data = {
            "total": total,
            "open": len(open_tasks),
            "overdue": overdue,
            "completed": sum(1 for t in tasks if t.get("status") in ["Completed", "Closed"]),
            "status_distribution": dist,
            "top_assignees": top_assignees,
        }

        # 3. AI Generation with graceful fallback and timeout
        try:
            from app.core.ai_summary_service import EmergentSummaryProvider, MockSummaryProvider
            from app.core.config import settings

            project_repo = ProjectRepository(self.db)
            project = await project_repo.get_by_id(project_id)
            project_name = project.get("project_name", project_id) if project else project_id

            provider = (
                EmergentSummaryProvider(settings.OPENAI_API_KEY)
                if settings.OPENAI_API_KEY
                else MockSummaryProvider()
            )

            # Add timeout for summary generation
            summary_text = await asyncio.wait_for(
                provider.generate_summary(report_data, f"Task Management for {project_name}"),
                timeout=TASK_AI_SUMMARY_GENERATION_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.warning(f"Task summary generation timed out after {TASK_AI_SUMMARY_GENERATION_TIMEOUT_SECONDS} seconds")
            summary_text = f"Summary generation timed out. Report metrics: {report_data}"
        except Exception as e:
            logger.error(f"Error generating task summary: {str(e)}", exc_info=True)
            raise TaskSummaryGenerationError(str(e))

        doc = {
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "summary_text": summary_text,
            "metrics": report_data,
            "created_at": datetime.now(timezone.utc),
        }

        try:
            return await summary_repo.create(doc)
        except Exception as e:
            logger.error(f"Error saving task summary: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to save task summary")
