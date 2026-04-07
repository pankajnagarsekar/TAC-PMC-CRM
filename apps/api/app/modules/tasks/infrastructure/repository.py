from app.modules.shared.infrastructure.base_repository import BaseRepository
from app.modules.tasks.schemas.dto import Task


class TaskRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "tasks", Task)
