from typing import Optional, Dict, Any, List
from app.repositories.base_repo import BaseRepository
from app.schemas.site import WorkersDailyLog, SiteOverhead

class WorkerLogRepository(BaseRepository[WorkersDailyLog]):
    def __init__(self, db):
        super().__init__(db, "worker_logs", WorkersDailyLog)

class SiteOverheadRepository(BaseRepository[SiteOverhead]):
    def __init__(self, db):
        super().__init__(db, "site_overheads", SiteOverhead)

class DPRRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "dpr")

class AttendanceRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "worker_attendance")

class VoiceLogRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "voice_logs")
