from typing import Optional, Dict, Any, List
from pymongo import ASCENDING
from app.repositories.base_repo import BaseRepository
from app.schemas.site import WorkersDailyLog, SiteOverhead

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

class DPRRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "dpr", dict)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING), ("date", ASCENDING)], unique=True)
        await self.collection.create_index([("status", ASCENDING)])

class AttendanceRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "worker_attendance", dict)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING), ("date", ASCENDING)])

class VoiceLogRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "voice_logs", dict)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING)])
