from app.repositories.base_repo import BaseRepository
from app.schemas.settings_ai import AISummaryDocument

class AISummaryRepository(BaseRepository[AISummaryDocument]):
    def __init__(self, db):
        super().__init__(db, "ai_project_summaries", AISummaryDocument)
