from app.modules.shared.infrastructure.base_repository import BaseRepository

from ..schemas.dto import AISummaryDocument


class AISummaryRepository(BaseRepository[AISummaryDocument]):
    def __init__(self, db):
        super().__init__(db, "ai_project_summaries", AISummaryDocument)
