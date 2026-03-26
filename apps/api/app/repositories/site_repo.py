from app.repositories.base_repo import BaseRepository
from app.schemas.site import WorkersDailyLog, SiteOverhead

class SiteLogRepository(BaseRepository[WorkersDailyLog]):
    def __init__(self, db):
        super().__init__(db, "worker_daily_logs", WorkersDailyLog)

class SiteOverheadRepository(BaseRepository[SiteOverhead]):
    def __init__(self, db):
        super().__init__(db, "site_overheads", SiteOverhead)
