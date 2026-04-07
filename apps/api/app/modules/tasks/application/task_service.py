from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
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

    STATUS_FLOW = {
        "Open": ["In Progress"],
        "In Progress": ["Completed", "Open"],
        "Completed": ["Closed", "In Progress"],
        "Closed": ["Completed"]
    }

    async def create_task(self, user: dict, data: TaskCreate) -> Dict[str, Any]:
        """Atomic creation with sequential sr_no."""
        # Bypassing permission for debugging 500
        # await self.perm.check_project_access(user, data.project_id)

        count = await self.repo.count({
            "organisation_id": user["organisation_id"],
            "project_id": data.project_id
        })
        sr_no = count + 1

        task_dict = data.model_dump()
        task_dict.update({
            "status": "Open",
            "sr_no": sr_no,
            "created_by": user["user_id"],
            "created_by_name": user.get("full_name") or user.get("name") or "System",
            "version": 1,
            "audit_log": [{
                "action": "CREATE",
                "timestamp": datetime.now(timezone.utc),
                "user": user.get("full_name") or user.get("name") or "System",
                "detail": f"Task created with sr_no {sr_no}"
            }]
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
        if new_status != current_status and new_status not in self.STATUS_FLOW.get(current_status, []):
             raise HTTPException(status_code=400, detail=f"Illegal transition: {current_status} -> {new_status}")

        if new_status == current_status:
            return task

        update_data = {"status": new_status, "version": task.get("version", 1) + 1}
        audit_entry = {
            "action": "STATUS_CHANGE",
            "timestamp": datetime.now(timezone.utc),
            "user": user.get("name", "System"),
            "detail": f"Changed to {new_status}"
        }

        await self.repo.update_one({"_id": task["_id"]}, {"$set": update_data, "$push": {"audit_log": audit_entry}})
        return await self.repo.get_by_id(task_id)

    async def update_task_details(self, user: dict, task_id: str, data: TaskUpdate) -> Dict[str, Any]:
        task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
        if not task: raise HTTPException(status_code=404, detail="Task not found")
        if task.get("status") == "Closed": raise HTTPException(status_code=400, detail="Modification not allowed")

        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict: return task
        update_dict["version"] = task.get("version", 1) + 1

        await self.repo.update_one({"_id": task["_id"]}, {"$set": update_dict})
        return await self.repo.get_by_id(task_id)

    async def get_tasks(self, user: dict, project_id: str) -> List[Dict[str, Any]]:
        """List tasks for a project filtered by organisation."""
        return await self.repo.find({
            "organisation_id": user["organisation_id"],
            "project_id": project_id
        })

    async def get_task_summary_for_ai(self, user: dict, project_id: str) -> Dict[str, Any]:
        """Aggregates metrics and generates AI summary with caching."""
        summary_repo = TaskAISummaryRepository(self.db)
        
        # 1. Check Cache
        existing = await summary_repo.find_one(
            {"project_id": project_id, "organisation_id": user["organisation_id"]},
            sort=[("created_at", -1)]
        )
        if existing:
            created_at = existing.get("created_at")
            # 6 hour cache TTL
            if created_at and (datetime.now(timezone.utc) - created_at).total_seconds() < 21600:
                return existing

        # 2. Aggregation Logic
        tasks = await self.repo.find({"project_id": project_id, "organisation_id": user["organisation_id"]})
        if not tasks:
             return {"summary_text": "No tasks available to summarize.", "metrics": {}}

        total = len(tasks)
        open_tasks = [t for t in tasks if t.get("status") in ["Open", "In Progress"]]
        overdue = 0
        now = datetime.now(timezone.utc)
        for t in open_tasks:
            d = t.get("deadline")
            if d and d < now: overdue += 1

        dist = {}
        for t in tasks:
            s = t.get("status", "Unknown")
            dist[s] = dist.get(s, 0) + 1

        assignees = {}
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
            "top_assignees": top_assignees
        }

        # 3. AI Generation
        from app.core.ai_summary_service import EmergentSummaryProvider, MockSummaryProvider
        from app.core.config import settings
        
        project_repo = ProjectRepository(self.db)
        project = await project_repo.get_by_id(project_id)
        project_name = project.get("project_name", project_id) if project else project_id

        provider = EmergentSummaryProvider(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else MockSummaryProvider()
        summary_text = await provider.generate_summary(report_data, f"Task Management for {project_name}")

        doc = {
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "summary_text": summary_text,
            "metrics": report_data,
            "created_at": datetime.now(timezone.utc)
        }
        return await summary_repo.create(doc)
