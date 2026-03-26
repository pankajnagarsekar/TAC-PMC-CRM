from app.repositories.base_repo import BaseRepository
from app.schemas.project import Project
from typing import Dict, Any, Optional
from bson import ObjectId, Decimal128
from pymongo import ASCENDING
from app.core.financial_utils import to_d128

class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db):
        super().__init__(db, "projects", Project)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        # Fixed CR-22: Added critical indexes for project identification and tenant scoping
        await self.collection.create_index([("project_id", ASCENDING)], unique=True)
        await self.collection.create_index([("project_code", ASCENDING)])
        await self.collection.create_index([("organisation_id", ASCENDING)])

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hard Normalization: Fix data shape drift (Point 41)."""
        if "project_id" in data:
            data["project_id"] = str(data["project_id"])
        
        # Financial fields (Standard names)
        money_fields = ["total_budget", "total_committed", "total_certified", "total_remaining"]
        for field in money_fields:
            if field in data:
                data[field] = to_d128(data[field])
        
        return data

    async def create(self, data: Dict[str, Any], session=None) -> Dict[str, Any]:
        data = self._normalize(data)
        return await super().create(data, session=session)

    async def update(self, id: str, data: Dict[str, Any], session=None) -> Optional[Dict[str, Any]]:
        data = self._normalize(data)
        return await super().update(id, data, session=session)

    async def get_by_project_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Authoritative project lookup."""
        return await self.find_one({"project_id": str(project_id)})
