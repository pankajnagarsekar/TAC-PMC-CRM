from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClientSession
from pydantic import BaseModel
from app.repositories.base_repo import BaseRepository
from app.schemas.financial import WorkOrder, PaymentCertificate, DerivedFinancialState, CodeMaster, VendorLedgerEntry

class SequenceModel(BaseModel):
    id: str
    seq: int

class WorkOrderRepository(BaseRepository[WorkOrder]):
    def __init__(self, db):
        super().__init__(db, "work_orders", WorkOrder)

    async def get_by_project(self, project_id: str, limit: int = 100, session: Optional[AsyncIOMotorClientSession] = None) -> List[Dict[str, Any]]:
        return await self.list({"project_id": project_id}, limit=limit, session=session)

class PCRepository(BaseRepository[PaymentCertificate]):
    def __init__(self, db):
        super().__init__(db, "payment_certificates", PaymentCertificate)

    async def list_by_project(self, project_id: str, organisation_id: str, limit: int = 100, cursor: Optional[str] = None) -> Dict[str, Any]:
        query = {"project_id": project_id, "organisation_id": organisation_id}
        if cursor:
            from datetime import datetime
            query["created_at"] = {"$lt": datetime.fromisoformat(cursor.replace('Z', '+00:00'))}
        
        docs = await self.list(query, sort=[("created_at", -1)], limit=limit)
        
        next_cursor = None
        if len(docs) == limit:
            ts = docs[-1].get("created_at")
            if ts:
                next_cursor = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)

        return {"items": docs, "next_cursor": next_cursor}

class BudgetRepository(BaseRepository[DerivedFinancialState]):
    def __init__(self, db):
        super().__init__(db, "project_category_budgets", DerivedFinancialState)

    async def get_by_project_and_category(self, project_id: str, category_id: str, session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        return await self.find_one({"project_id": project_id, "category_id": category_id}, session=session)

class CodeMasterRepository(BaseRepository[CodeMaster]):
    def __init__(self, db):
        super().__init__(db, "code_master", CodeMaster)

class LedgerRepository(BaseRepository[VendorLedgerEntry]):
    def __init__(self, db):
        super().__init__(db, "vendor_ledger", VendorLedgerEntry)

class FinancialStateRepository(BaseRepository[DerivedFinancialState]):
    def __init__(self, db):
        super().__init__(db, "financial_state", DerivedFinancialState)

class SequenceRepository(BaseRepository[SequenceModel]):
    def __init__(self, db):
        super().__init__(db, "sequences", SequenceModel)

    async def get_next_sequence(self, name: str, session: Optional[AsyncIOMotorClientSession] = None) -> int:
        doc = await self.collection.find_one_and_update(
            {"_id": name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,
            session=session
        )
        return doc["seq"]
