from typing import List, Dict, Any, Optional
from app.repositories.base_repo import BaseRepository

class FundAllocationRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "fund_allocations")

class CashTransactionRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "cash_transactions")
