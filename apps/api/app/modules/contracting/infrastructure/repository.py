from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo import ASCENDING

from app.modules.shared.infrastructure.base_repository import BaseRepository

from ..schemas.dto import Vendor, VendorLedgerEntry, WorkOrder


class WorkOrderRepository(BaseRepository[WorkOrder]):
    def __init__(self, db):
        super().__init__(db, "work_orders", WorkOrder)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("project_id", ASCENDING), ("category_id", ASCENDING)]
        )
        await self.collection.create_index([("status", ASCENDING)])
        await self.collection.create_index([("wo_ref", ASCENDING)])

    async def get_by_project(
        self,
        project_id: str,
        limit: int = 100,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> List[Dict[str, Any]]:
        return await self.list({"project_id": project_id}, limit=limit, session=session)


class VendorRepository(BaseRepository[Vendor]):
    def __init__(self, db):
        super().__init__(db, "vendors", Vendor)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("organisation_id", ASCENDING), ("name", ASCENDING)]
        )

    async def get_by_name(
        self, name: str, organisation_id: str
    ) -> Optional[Dict[str, Any]]:
        return await self.find_one({"name": name, "organisation_id": organisation_id})


class LedgerRepository(BaseRepository[VendorLedgerEntry]):
    def __init__(self, db):
        super().__init__(db, "vendor_ledger", VendorLedgerEntry)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("vendor_id", ASCENDING), ("project_id", ASCENDING)]
        )
