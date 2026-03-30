from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo import ASCENDING, DESCENDING

from app.modules.shared.infrastructure.base_repository import BaseRepository

from ..schemas.dto import (
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
