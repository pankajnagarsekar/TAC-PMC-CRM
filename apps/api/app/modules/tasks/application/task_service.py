from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.shared.domain.state_machine import StateMachine
from app.modules.tasks.infrastructure.repository import TaskRepository, TaskAISummaryRepository
from app.modules.tasks.schemas.dto import TaskCreate, TaskUpdate
from app.modules.project.infrastructure.repository import ProjectRepository


class TaskService:
    def __init__(self, db: AsyncIOMotorDatabase, audit=None, perm=None, snap=None):
        self.db = db
        self.repo = TaskRepository(db)
        self.audit = audit
        self.perm = perm
        self.snap = snap

    async def create_task(self, user: dict, data: TaskCreate) -> Dict[str, Any]:
        """Atomic creation with sequential sr_no."""
        count = await self.repo.count({
            "organisation_id": user["organisation_id"],
            "project_id": data.project_id,
        })
        sr_no = count + 1

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
        return await self.repo.create(task_dict)

    async def get_task(self, user: dict, task_id: str) -> Dict[str, Any]:
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    async def update_status(self, user: dict, task_id: str, new_status: str) -> Dict[str, Any]:
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

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
        return await self.repo.get_by_id(task_id)

    async def update_task_details(self, user: dict, task_id: str, data: TaskUpdate) -> Dict[str, Any]:
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

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
        return await self.repo.get_by_id(task_id)

    async def get_tasks(self, user: dict, project_id: str) -> List[Dict[str, Any]]:
        """List all tasks for a project scoped to the user's organisation."""
        return await self.repo.find({
            "organisation_id": user["organisation_id"],
            "project_id": project_id,
        })

    async def delete_task(self, user: dict, task_id: str) -> None:
        """
        Hard-delete pristine Open tasks.
        Tasks with work history are transitioned to Closed instead (preserves audit trail).
        """
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # If already Closed, nothing to do
        if task.get("status") == "Closed":
            return

        # Pristine Open tasks with only the CREATE log entry can be hard-deleted
        if task.get("status") == "Open" and len(task.get("audit_log", [])) <= 1:
            await self.repo.delete(task_id)
        else:
            # Transition to Closed — this preserves the audit trail
            await self.update_status(user, task_id, "Closed")

    async def get_task_summary_for_ai(self, user: dict, project_id: str) -> Dict[str, Any]:
        """Aggregates metrics and generates AI summary with caching."""
        summary_repo = TaskAISummaryRepository(self.db)

        # 1. Check Cache (6-hour TTL)
        existing = await summary_repo.find_one(
            {"project_id": project_id, "organisation_id": user["organisation_id"]},
            sort=[("created_at", -1)],
        )
        if existing:
            created_at = existing.get("created_at")
            if created_at and (datetime.now(timezone.utc) - created_at).total_seconds() < 21600:
                return existing

        # 2. Aggregate task metrics
        tasks = await self.repo.find({
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
        })
        if not tasks:
            return {"summary_text": "No tasks available to summarize.", "metrics": {}}

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
        top_assignees = dict(sorted(assignees.items(), key=lambda x: x[1], reverse=True)[:3])

        report_data = {
            "total": total,
            "open": len(open_tasks),
            "overdue": overdue,
            "completed": sum(1 for t in tasks if t.get("status") in ["Completed", "Closed"]),
            "status_distribution": dist,
            "top_assignees": top_assignees,
        }

        # 3. AI Generation with graceful fallback
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
        summary_text = await provider.generate_summary(report_data, f"Task Management for {project_name}")

        doc = {
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "summary_text": summary_text,
            "metrics": report_data,
            "created_at": datetime.now(timezone.utc),
        }
        return await summary_repo.create(doc)
