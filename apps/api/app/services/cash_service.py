from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId, Decimal128
from fastapi import HTTPException

from app.repositories.cash_repo import FundAllocationRepository, CashTransactionRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.settings_repo import CodeMasterRepository
from app.repositories.user_repo import UserRepository
from app.services.audit_service import AuditService
from app.core.financial_utils import to_d128, to_decimal

class CashService:
    def __init__(self, db, permission_checker, audit_service: AuditService):
        self.db = db
        self.permission_checker = permission_checker
        self.audit_service = audit_service
        self.fund_repo = FundAllocationRepository(db)
        self.txn_repo = CashTransactionRepository(db)
        self.project_repo = ProjectRepository(db)
        self.code_repo = CodeMasterRepository(db)
        self.user_repo = UserRepository(db)

    def _get_threshold_for_category(self, category, project) -> Decimal:
        default_threshold = Decimal("1000.0")
        if not category or not project:
            return default_threshold
        cat_name = category.get("category_name", "").lower()
        if "petty" in cat_name:
            return Decimal(str(project.get("threshold_petty", default_threshold)))
        elif "ovh" in cat_name or "overhead" in cat_name:
            return Decimal(str(project.get("threshold_ovh", default_threshold)))
        return default_threshold

    async def get_cash_summary(self, user: dict, project_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        
        now = datetime.now(timezone.utc)
        project = await self.project_repo.get_by_project_id(project_id)
        
        categories = await self.code_repo.list({
            "organisation_id": user["organisation_id"],
            "budget_type": "fund_transfer"
        }, limit=100)

        if not categories:
            return {"categories": [], "summary": {"total_cash_in_hand": 0.0, "days_since_last_pc_close": 0}}

        category_ids = [str(cat["id"]) for cat in categories]
        
        # We'll use the same aggregation logic but maybe scoped via repo if we could.
        # For simplicity, since it's a complex aggregation, we can keep it here or move to repo.
        # I'll keep it here for now as it's very specific to this view.
        pipeline = [
            {"$match": {"project_id": project_id, "category_id": {"$in": category_ids}}},
            {
                "$lookup": {
                    "from": "payment_certificates",
                    "let": {"cat_id": "$category_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$project_id", project_id]},
                                        {"$eq": ["$category_id", "$$cat_id"]},
                                        {"$eq": ["$status", "Closed"]},
                                        {"$eq": ["$fund_request", True]}
                                    ]
                                }
                            }
                        },
                        {"$project": {"updated_at": 1, "_id": 0}}
                    ],
                    "as": "closed_pcs"
                }
            },
            {"$addFields": {"last_pc_close_date": {"$max": "$closed_pcs.updated_at"}}},
            {"$project": {"closed_pcs": 0}}
        ]
        
        allocation_docs = await self.db.fund_allocations.aggregate(pipeline).to_list(length=200)
        allocation_by_cat = {str(doc["category_id"]): doc for doc in allocation_docs}
        category_map = {str(cat["id"]): cat for cat in categories}

        categories_data = []
        total_cash_in_hand = Decimal("0")

        def _dec(val):
            if isinstance(val, Decimal128): return val.to_decimal()
            return Decimal(str(val)) if val is not None else Decimal("0")

        for cat_id, allocation in allocation_by_cat.items():
            cat = category_map.get(cat_id)
            if not cat: continue

            threshold = self._get_threshold_for_category(cat, project)
            allocation_received = to_decimal(allocation.get("allocation_received"))
            total_expenses = to_decimal(allocation.get("total_expenses"))
            allocation_original = to_decimal(allocation.get("allocation_original"))

            cash_in_hand = allocation_received - total_expenses
            allocation_remaining = allocation_original - allocation_received
            total_cash_in_hand += cash_in_hand

            days_since_last_pc_close = None
            last_close = allocation.get("last_pc_close_date")
            if last_close:
                if isinstance(last_close, datetime) and last_close.tzinfo is None:
                    last_close = last_close.replace(tzinfo=timezone.utc)
                days_since_last_pc_close = (now - last_close).days

            categories_data.append({
                "category_id": cat_id,
                "category_name": cat.get("category_name"),
                "cash_in_hand": float(cash_in_hand),
                "allocation_remaining": float(allocation_remaining),
                "allocation_total": float(allocation_original),
                "threshold": float(threshold),
                "days_since_last_pc_close": days_since_last_pc_close,
                "is_negative": cash_in_hand < 0,
                "threshold_breached": cash_in_hand <= threshold,
            })

        return {
            "categories": categories_data,
            "summary": {
                "total_cash_in_hand": float(total_cash_in_hand),
                "days_since_last_pc_close": min(
                    (c["days_since_last_pc_close"] for c in categories_data if c["days_since_last_pc_close"] is not None),
                    default=0
                )
            }
        }

    async def list_fund_allocations(self, user: dict, project_id: str) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        
        pipeline = [
            {"$match": {"project_id": project_id}},
            {
                "$lookup": {
                    "from": "code_master",
                    "let": {"cat_id": "$category_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$cat_id"]}}}
                    ],
                    "as": "category_info"
                }
            },
            {"$unwind": {"path": "$category_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "id": {"$toString": "$_id"},
                    "project_id": 1,
                    "category_id": 1,
                    "allocation_original": 1,
                    "allocation_received": 1,
                    "allocation_remaining": 1,
                    "last_pc_closed_date": 1,
                    "created_at": 1,
                    "category_name": "$category_info.category_name"
                }
            },
            {"$sort": {"created_at": -1}}
        ]
        
        docs = await self.db.fund_allocations.aggregate(pipeline).to_list(length=100)
        
        def to_float(val):
            if isinstance(val, Decimal128): return float(val.to_decimal())
            return float(val) if val is not None else 0.0

        for d in docs:
            d["allocation_original"] = to_float(d.get("allocation_original"))
            d["allocation_received"] = to_float(d.get("allocation_received"))
            d["allocation_remaining"] = to_float(d.get("allocation_remaining"))
            if "created_at" in d and isinstance(d["created_at"], datetime):
                d["created_at"] = d["created_at"].isoformat()

        return docs

    async def list_cash_transactions(
        self, user: dict, project_id: str, category_id: Optional[str] = None, cursor: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        
        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
        if category_id:
            query["category_id"] = category_id
            
        if cursor:
            try:
                parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
                query["created_at"] = {"$lt": parsed_cursor}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid cursor format")

        docs = await self.txn_repo.list(query, sort=[("created_at", -1)], limit=limit)
        
        next_cursor = None
        if len(docs) == limit:
            last_doc = docs[-1]
            ts = last_doc.get("created_at")
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()

        items = []
        for d in docs:
            if d.get("created_by"):
                u = await self.user_repo.get_by_user_id(d["created_by"])
                if u:
                    d["created_by_name"] = u.get("name") or u.get("full_name") or u.get("email", "").split("@")[0]
            
            if d.get("category_id"):
                cat = await self.code_repo.get(d["category_id"])
                if cat:
                    d["category_name"] = cat.get("category_name")
            
            if "amount" in d:
                if isinstance(d["amount"], Decimal128):
                    d["amount"] = float(d["amount"].to_decimal())
            
            if "created_at" in d and isinstance(d["created_at"], datetime):
                d["created_at"] = d["created_at"].isoformat()
            
            items.append(d)

        return {"items": items, "next_cursor": next_cursor}

    async def create_cash_transaction(self, user: dict, project_id: str, data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_client_readonly(user)

        amount = Decimal(str(data["amount"]))
        category_id = data["category_id"]
        txn_type = data["type"]

        async with self.db.client.start_session() as session:
            async with session.start_transaction():
                # Check idempotency handled by router for now? 
                # Actually logic should be here.
                
                allocation = await self.fund_repo.get_one({"project_id": project_id, "category_id": category_id}, session=session)
                if not allocation:
                    raise HTTPException(status_code=404, detail="No active fund allocation found for this category.")

                project = await self.project_repo.get_by_project_id(project_id)
                category = await self.code_repo.get(category_id)

                if txn_type == "DEBIT":
                    inc_ops = {
                        "cash_in_hand": to_d128(-amount),
                        "total_expenses": to_d128(amount),
                    }
                else:
                    inc_ops = {
                        "cash_in_hand": to_d128(amount),
                    }

                updated_alloc = await self.db.fund_allocations.find_one_and_update(
                    {"_id": allocation["_id"] if "_id" in allocation else ObjectId(allocation["id"])},
                    {"$inc": inc_ops},
                    return_document=True,
                    session=session
                )

                new_cash_in_hand = to_decimal(updated_alloc.get("cash_in_hand"))
                
                doc = {
                    "project_id": project_id,
                    "organisation_id": user["organisation_id"],
                    "category_id": category_id,
                    "amount": to_d128(amount),
                    "type": txn_type,
                    "description": data.get("description"),
                    "transaction_date": data.get("transaction_date"),
                    "created_by": user["user_id"],
                    "created_at": datetime.now(timezone.utc)
                }
                
                res = await self.txn_repo.create(doc, session=session)
                doc["id"] = str(res)
                
                # Audit log
                await self.audit_service.log_action(
                    organisation_id=user["organisation_id"],
                    module_name="CASH_TRANSACTIONS",
                    entity_type="CASH_TRANSACTION",
                    entity_id=str(res),
                    action_type="CREATE",
                    user_id=user["user_id"],
                    project_id=project_id,
                    new_value=data, # Simple snapshot
                    session=session
                )

        threshold = self._get_threshold_for_category(category, project)
        warnings = []
        if new_cash_in_hand < 0:
            warnings.append("negative_cash")
        elif new_cash_in_hand <= threshold:
            warnings.append("threshold_breach")

        result = {**doc, "amount": float(amount), "warnings": warnings}
        if "created_at" in result:
            result["created_at"] = result["created_at"].isoformat()
        return result

