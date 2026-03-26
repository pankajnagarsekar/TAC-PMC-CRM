from typing import Optional, Dict, Any
from pymongo import ASCENDING
from app.repositories.base_repo import BaseRepository
from app.schemas.vendor import Vendor

class VendorRepository(BaseRepository[Vendor]):
    def __init__(self, db):
        super().__init__(db, "vendors", Vendor)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("organisation_id", ASCENDING), ("name", ASCENDING)])
        await self.collection.create_index([("vendor_id", ASCENDING)], unique=True)

    async def get_by_name(self, name: str, organisation_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"name": name, "organisation_id": organisation_id})
