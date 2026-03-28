from typing import Optional, Dict, Any, List
from pymongo import ASCENDING
from app.repositories.base_repo import BaseRepository
from ..schemas.dto import WorkersDailyLog, SiteOverhead, DPR, VoiceLog

class WorkerLogRepository(BaseRepository[WorkersDailyLog]):
    def __init__(self, db):
        super().__init__(db, "worker_logs", WorkersDailyLog)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING)])

class SiteOverheadRepository(BaseRepository[SiteOverhead]):
    def __init__(self, db):
        super().__init__(db, "site_overheads", SiteOverhead)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING), ("category_id", ASCENDING)])

class DPRRepository(BaseRepository[DPR]):
    def __init__(self, db):
        super().__init__(db, "dpr", DPR)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        # Ensure project+date uniqueness for DPRs
        await self.collection.create_index([("project_id", ASCENDING), ("dpr_date", ASCENDING)], unique=True)
        await self.collection.create_index([("status", ASCENDING)])

class AttendanceRepository(BaseRepository[Any]):
    def __init__(self, db):
        super().__init__(db, "worker_attendance", Any)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING), ("date", ASCENDING)])

class VoiceLogRepository(BaseRepository[VoiceLog]):
    def __init__(self, db):
        super().__init__(db, "voice_logs", VoiceLog)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING)])
