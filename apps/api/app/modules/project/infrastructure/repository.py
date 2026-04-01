from typing import Any, Dict, List, Optional


from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo import ASCENDING, DESCENDING

from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.shared.infrastructure.base_repository import BaseRepository

from ..schemas.dto import Client, Project, ProjectBudget, UserProjectMap


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db):
        super().__init__(db, "projects", Project)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING)], unique=True)
        await self.collection.create_index([("project_code", ASCENDING)])
        await self.collection.create_index([("organisation_id", ASCENDING)])

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "project_id" in data:
            data["project_id"] = str(data["project_id"])

        money_fields = [
            "total_budget",
            "total_committed",
            "total_certified",
            "total_remaining",
        ]
        for field in money_fields:
            if field in data:
                data[field] = FinancialEngine.to_d128(data[field])
        return data

    async def create(self, data: Dict[str, Any], session=None) -> Dict[str, Any]:
        data = self._normalize(data)
        return await super().create(data, session=session)

    async def update(
        self, id: str, data: Dict[str, Any], session=None, **filters
    ) -> Optional[Dict[str, Any]]:
        data = self._normalize(data)
        return await super().update(id, data, session=session, **filters)

    async def get_by_project_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"project_id": str(project_id)})


class ClientRepository(BaseRepository[Client]):
    def __init__(self, db):
        super().__init__(db, "clients", Client)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("organisation_id", ASCENDING)])
        # Removed client_id unique index if not explicitly using internal client_id field


class BudgetRepository(BaseRepository[ProjectBudget]):
    def __init__(self, db):
        super().__init__(db, "project_category_budgets", ProjectBudget)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("project_id", ASCENDING), ("category_id", ASCENDING)], unique=True
        )

    async def get_by_project_and_category(
        self,
        project_id: str,
        category_id: str,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        return await self.find_one(
            {"project_id": project_id, "category_id": category_id}, session=session
        )


class UserProjectMapRepository(BaseRepository[UserProjectMap]):
    def __init__(self, db):
        super().__init__(db, "user_project_map", UserProjectMap)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("user_id", ASCENDING), ("project_id", ASCENDING)], unique=True
        )

    async def get_projects_for_user(self, user_id: str) -> List[str]:
        mappings = await self.list({"user_id": user_id})
        return [m["project_id"] for m in mappings]


# Modularized Schedule Repository (Project Context)
class ScheduleRepository(BaseRepository[Any]):
    def __init__(self, db):
        super().__init__(db, "project_schedules", Any)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING)])
        await self.collection.create_index([("organisation_id", ASCENDING)])


class TimelineRepository(BaseRepository[Any]):
    def __init__(self, db):
        super().__init__(db, "project_timeline", Any)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("project_id", ASCENDING), ("timestamp", DESCENDING)]
        )

    async def list_project_timeline(
        self, project_id: str, organisation_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return await self.list(
            {"project_id": project_id, "organisation_id": organisation_id},
            sort=[("timestamp", -1)],
            limit=limit,
        )
