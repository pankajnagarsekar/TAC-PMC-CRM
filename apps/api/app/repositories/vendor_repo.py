from typing import Optional, Dict, Any
from app.repositories.base_repo import BaseRepository
from app.schemas.vendor import Vendor

class VendorRepository(BaseRepository[Vendor]):
    def __init__(self, db):
        super().__init__(db, "vendors", Vendor)

    async def get_by_name(self, name: str, organisation_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"name": name, "organisation_id": organisation_id})
