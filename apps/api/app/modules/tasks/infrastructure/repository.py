from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.shared.infrastructure.base_repository import BaseRepository
from app.modules.tasks.schemas.dto import Task
from app.modules.tasks.infrastructure.counter import AtomicCounter


class TaskRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "tasks", Task)
        self._db = db

    async def get_next_sr_no(self, org_id: str, project_id: str) -> int:
        """
        Get the next sequential sr_no for a task in the project.

        Args:
            org_id: Organization ID for scoping
            project_id: Project ID for scoping

        Returns:
            The next sequential sr_no (starting from 1)
        """
        return await AtomicCounter.get_next_value(self._db, org_id, project_id)


class TaskAISummaryRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "task_ai_summaries", dict)
