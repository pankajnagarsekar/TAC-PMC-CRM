from app.repositories.base_repo import BaseRepository
from app.schemas.project import Project

class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db):
        super().__init__(db, "projects", Project)
