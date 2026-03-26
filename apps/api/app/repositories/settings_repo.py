from pymongo import ASCENDING
from app.repositories.base_repo import BaseRepository
from app.schemas.settings_ai import GlobalSettings

class SettingsRepository(BaseRepository[GlobalSettings]):
    def __init__(self, db):
        super().__init__(db, "global_settings", GlobalSettings)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("organisation_id", ASCENDING)], unique=True)

# Fixed CR-08: Removed duplicate CodeMasterRepository from settings_repo.
# It is now exclusively defined in financial_repo.py.
