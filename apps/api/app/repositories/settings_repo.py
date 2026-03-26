from app.repositories.base_repo import BaseRepository
from app.schemas.settings_ai import GlobalSettings, CodeMaster

class SettingsRepository(BaseRepository[GlobalSettings]):
    def __init__(self, db):
        super().__init__(db, "global_settings", GlobalSettings)

class CodeMasterRepository(BaseRepository[CodeMaster]):
    def __init__(self, db):
        super().__init__(db, "code_master", CodeMaster)
