from typing import List, Dict, Any, Optional
from app.repositories.base_repo import BaseRepository
from app.schemas.cash import FundAllocation, CashTransaction
from pymongo import ASCENDING

class FundAllocationRepository(BaseRepository[FundAllocation]):
    def __init__(self, db):
        super().__init__(db, "fund_allocations", FundAllocation)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("project_id", ASCENDING), ("category_id", ASCENDING)], unique=True)

class CashTransactionRepository(BaseRepository[CashTransaction]):
    def __init__(self, db):
        super().__init__(db, "cash_transactions", CashTransaction)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("organisation_id", ASCENDING)])
        await self.collection.create_index([("project_id", ASCENDING)])
        await self.collection.create_index([("category_id", ASCENDING)])
