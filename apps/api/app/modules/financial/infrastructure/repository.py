from datetime import datetime
from typing import Any, Dict, Optional

from pymongo import ASCENDING

from app.modules.shared.infrastructure.base_repository import BaseRepository

from ..schemas.dto import (
    Budget,
    CashTransaction,
    CodeMaster,
    DerivedFinancialState,
    FundAllocation,
    PaymentCertificate,
)


class PCRepository(BaseRepository[PaymentCertificate]):
    def __init__(self, db):
        super().__init__(db, "payment_certificates", PaymentCertificate)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("project_id", ASCENDING), ("status", ASCENDING)]
        )
        await self.collection.create_index([("pc_ref", ASCENDING)])

    async def list_by_project(
        self,
        project_id: str,
        organisation_id: str,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = {"project_id": project_id, "organisation_id": organisation_id}
        if cursor:
            query["created_at"] = {
                "$lt": datetime.fromisoformat(cursor.replace("Z", "+00:00"))
            }

        docs = await self.list(query, sort=[("created_at", -1)], limit=limit)

        next_cursor = None
        if len(docs) == limit:
            ts = docs[-1].get("created_at")
            if ts:
                next_cursor = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

        return {"items": docs, "next_cursor": next_cursor}


class CodeMasterRepository(BaseRepository[CodeMaster]):
    def __init__(self, db):
        super().__init__(db, "code_master", CodeMaster)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("code", ASCENDING)])
        await self.collection.create_index([("code_short", ASCENDING)])


class FinancialStateRepository(BaseRepository[DerivedFinancialState]):
    def __init__(self, db):
        super().__init__(db, "financial_state", DerivedFinancialState)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("project_id", ASCENDING), ("category_id", ASCENDING)], unique=True
        )

    async def get_master_state(self, project_id: str, organisation_id: str = None) -> Optional[Dict[str, Any]]:
        """Fetch the authoritative MASTER snapshot for a project."""
        from app.modules.shared.domain.financial_engine import FinancialEngine
        from bson import ObjectId

        p_id = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        query = {
            "project_id": {"$in": [project_id, p_id] if isinstance(p_id, ObjectId) else [project_id]},
            "category_id": FinancialEngine.MASTER_CATEGORY
        }
        if organisation_id:
            query["organisation_id"] = organisation_id

        return await self.find_one(query)

    async def list_categorical_states(self, project_id: str, organisation_id: str = None) -> list:
        """Fetch all financial states EXCLUDING the MASTER snapshot (BUG-005 Mitigation)."""
        from app.modules.shared.domain.financial_engine import FinancialEngine
        from bson import ObjectId

        p_id = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        query = {
            "project_id": {"$in": [project_id, p_id] if isinstance(p_id, ObjectId) else [project_id]},
            "category_id": {"$ne": FinancialEngine.MASTER_CATEGORY}
        }
        if organisation_id:
            query["organisation_id"] = organisation_id

        return await self.list(query, limit=1000)


class FundAllocationRepository(BaseRepository[FundAllocation]):
    def __init__(self, db):
        super().__init__(db, "fund_allocations", FundAllocation)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("project_id", ASCENDING), ("category_id", ASCENDING)], unique=True
        )


class CashTransactionRepository(BaseRepository[CashTransaction]):
    def __init__(self, db):
        super().__init__(db, "cash_transactions", CashTransaction)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("organisation_id", ASCENDING)])
        await self.collection.create_index([("project_id", ASCENDING)])
        await self.collection.create_index([("category_id", ASCENDING)])


class BudgetRepository(BaseRepository[Budget]):
    def __init__(self, db):
        super().__init__(db, "project_category_budgets", Budget)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index(
            [("project_id", ASCENDING), ("organisation_id", ASCENDING)]
        )
        await self.collection.create_index([("status", ASCENDING)])

    async def list_by_project(
        self, project_id: str, organisation_id: str, limit: int = 100
    ) -> list:
        query = {"project_id": project_id, "organisation_id": organisation_id}
        return await self.list(query, limit=limit, sort=[("created_at", -1)])
